"""Backend `tunnel` da ponte de upload — sem bucket.

Serve **um único arquivo**, num caminho aleatório (128 bits), por tempo e número de
downloads limitados, através de um *quick tunnel* do Cloudflare
(`https://<aleatório>.trycloudflare.com`). Não exige conta nem guarda o arquivo fora
da máquina.

Processo: `cs upload put` dispara este módulo como processo **destacado** (nova
sessão), porque o túnel precisa sobreviver ao comando — o agente ainda vai chamar o
MCP depois. O processo escreve o status em `<work_dir>/status.json` e se encerra
sozinho no TTL, após `max_downloads` GETs completos, ou ao receber SIGTERM
(`cs upload delete` / `cs dispatch record`).

Uso interno:  python -m cs.tunnel --file F --work-dir D --ttl 600 --max-downloads 3
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def cloudflared_bin() -> str | None:
    env = os.environ.get("CLOUDFLARED_BIN")
    if env and Path(env).exists():
        return env
    found = shutil.which("cloudflared")
    if found:
        return found
    local = Path.home() / ".local" / "bin" / "cloudflared"
    return str(local) if local.exists() else None


def cloudflared_conflict() -> str | None:
    """Quick tunnels não funcionam se existir config.yml do cloudflared no diretório padrão."""
    for p in (Path.home() / ".cloudflared" / "config.yml", Path.home() / ".cloudflared" / "config.yaml",
              Path("/etc/cloudflared/config.yml")):
        if p.exists():
            return str(p)
    return None


def _write_status(work_dir: Path, **fields) -> None:
    path = work_dir / "status.json"
    cur = {}
    if path.exists():
        try:
            cur = json.loads(path.read_text())
        except json.JSONDecodeError:
            cur = {}
    cur.update(fields)
    tmp = work_dir / ".status.tmp"
    tmp.write_text(json.dumps(cur, ensure_ascii=False, indent=2))
    os.replace(tmp, path)


def serve(file: Path, work_dir: Path, ttl: int, max_downloads: int) -> int:
    work_dir.mkdir(parents=True, exist_ok=True)
    binary = cloudflared_bin()
    if not binary:
        _write_status(work_dir, state="error", error="cloudflared não encontrado")
        return 2

    token = secrets.token_urlsafe(16)
    url_path = f"/{token}/{quote(file.name, safe='._-')}"
    data = file.read_bytes()
    ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    stop = threading.Event()
    downloads = {"n": 0}
    lock = threading.Lock()
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    class Handler(BaseHTTPRequestHandler):
        server_version = "cs"
        sys_version = ""

        def log_message(self, fmt, *args):  # log mínimo, sem query/headers
            with (work_dir / "access.log").open("a") as f:
                f.write(f"{datetime.now().isoformat(timespec='seconds')} {self.command} "
                        f"{'match' if self.path.split('?')[0] == url_path else 'other'} {args[1] if len(args) > 1 else ''}\n")

        def _headers(self):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(file.name)}")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def _deny(self):
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_HEAD(self):
            if self.path.split("?")[0] != url_path or stop.is_set():
                return self._deny()
            self._headers()

        def do_GET(self):
            if self.path.split("?")[0] != url_path or stop.is_set():
                return self._deny()
            with lock:
                if downloads["n"] >= max_downloads:
                    return self._deny()
            self._headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                return
            with lock:
                downloads["n"] += 1
                n = downloads["n"]
            _write_status(work_dir, downloads=n)
            if n >= max_downloads:
                stop.set()

        def _method_not_allowed(self):
            self.send_response(405)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _method_not_allowed

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    log = (work_dir / "cloudflared.log").open("w")
    proc = subprocess.Popen(
        [binary, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    _write_status(work_dir, state="starting", pid=os.getpid(), port=port,
                  expires_at=expires.isoformat(timespec="seconds"), downloads=0, max_downloads=max_downloads)

    def read_stderr():
        found = False
        for line in proc.stderr:  # type: ignore[union-attr]
            log.write(line)
            log.flush()
            if not found:
                m = URL_RE.search(line)
                if m:
                    found = True
                    _write_status(work_dir, state="ready", url=m.group(0) + url_path)

    threading.Thread(target=read_stderr, daemon=True).start()

    def on_term(signum, frame):
        stop.set()

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)

    while not stop.is_set():
        if datetime.now(timezone.utc) >= expires:
            break
        if proc.poll() is not None:
            _write_status(work_dir, state="error", error=f"cloudflared saiu com código {proc.returncode}")
            httpd.shutdown()
            return 2
        stop.wait(0.5)

    # pequena folga para a resposta em curso terminar
    time.sleep(0.5)
    httpd.shutdown()
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    _write_status(work_dir, state="closed", closed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  downloads=downloads["n"])
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cs.tunnel")
    p.add_argument("--file", required=True)
    p.add_argument("--work-dir", required=True)
    p.add_argument("--ttl", type=int, default=600)
    p.add_argument("--max-downloads", type=int, default=3)
    a = p.parse_args(argv)
    return serve(Path(a.file), Path(a.work_dir), a.ttl, a.max_downloads)


if __name__ == "__main__":
    sys.exit(main())
