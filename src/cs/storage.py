"""Ponte de upload (A1): o MCP da Clicksign só aceita URL HTTPS pública.

Sobe o arquivo para um bucket próprio, devolve URL assinada de TTL curto e apaga
depois do envio. Backends:
- `tunnel` (padrão, sem bucket): serve o arquivo local por um quick tunnel do Cloudflare,
  com caminho aleatório, TTL e limite de downloads (ver `cs.tunnel`);
- `s3` (AWS S3 ou compatível — Cloudflare R2, MinIO, Backblaze B2, via S3_ENDPOINT_URL);
- `gcs` (Google Cloud Storage; exige credencial de service account para assinar URL).
"""

from __future__ import annotations

import json
import mimetypes
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from .config import Settings


class StorageError(Exception):
    pass


@dataclass
class Upload:
    ref: str  # "<backend>://<bucket>/<key>"
    url: str
    expires_at: str


def _key(settings: Settings, filename: str) -> str:
    prefix = settings.upload_prefix
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    # Chave aleatória por envio; o basename preserva o nome do arquivo (o MCP também recebe filename explícito).
    return f"{prefix}{secrets.token_urlsafe(18)}/{quote(filename, safe='._-')}"


def _parse_ref(ref: str) -> tuple[str, str, str]:
    backend, _, rest = ref.partition("://")
    bucket, _, key = rest.partition("/")
    if not backend or not bucket or not key:
        raise StorageError(f"referência de upload inválida: {ref}")
    return backend, bucket, key


def _s3(settings: Settings):
    import boto3
    from botocore.config import Config

    kwargs = {"config": Config(signature_version="s3v4")}
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.s3_region:
        kwargs["region_name"] = settings.s3_region
    return boto3.client("s3", **kwargs)


def _gcs_bucket(settings: Settings, bucket: str):
    try:
        from google.cloud import storage as gcs
    except ImportError as e:  # pragma: no cover
        raise StorageError("backend gcs requer `uv sync --extra gcs`") from e
    return gcs.Client().bucket(bucket)


def _require(settings: Settings) -> None:
    if settings.upload_backend not in {"tunnel", "s3", "gcs"}:
        raise StorageError("UPLOAD_BACKEND não configurado (use tunnel, s3 ou gcs no .env)")
    if settings.upload_backend != "tunnel" and not settings.upload_bucket:
        raise StorageError("UPLOAD_BUCKET não configurado no .env")


# --- tunnel -----------------------------------------------------------------

TUNNEL_READY_TIMEOUT = 45  # s até o cloudflared publicar a URL
TUNNEL_VERIFY_TIMEOUT = 60  # s até a URL pública responder (propagação de DNS)


def _tunnel_status(work_dir: Path) -> dict:
    try:
        return json.loads((work_dir / "status.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _doh_resolve(host: str) -> str | None:
    """Resolve via DNS público (DoH Cloudflare). Redes corporativas podem não resolver
    *.trycloudflare.com; a Clicksign usa DNS público, então é isso que importa verificar."""
    req = urllib.request.Request(
        f"https://1.1.1.1/dns-query?name={host}&type=A", headers={"accept": "application/dns-json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    for ans in data.get("Answer") or []:
        if ans.get("type") == 1:
            return ans.get("data")
    return None


def _fetch(url: str, method: str = "GET", timeout: int = 15) -> tuple[int, dict, bytes]:
    """Requisição HTTPS que resolve o host pelo DNS do sistema e, se falhar, por DoH."""
    import http.client
    import socket
    import ssl
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    host = parts.hostname or ""
    path = parts.path + (f"?{parts.query}" if parts.query else "")
    try:
        ip = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)[0][4][0]
    except socket.gaierror:
        ip = _doh_resolve(host)
        if not ip:
            raise OSError(f"não resolvi {host}")
    ctx = ssl.create_default_context()

    class _Conn(http.client.HTTPSConnection):
        def connect(self):
            sock = socket.create_connection((ip, 443), timeout=timeout)
            self.sock = ctx.wrap_socket(sock, server_hostname=host)

    conn = _Conn(host, 443, timeout=timeout, context=ctx)
    try:
        conn.request(method, path, headers={"User-Agent": "cs-selfcheck", "Host": host})
        r = conn.getresponse()
        body = r.read() if method != "HEAD" else b""
        return r.status, {k.lower(): v for k, v in r.getheaders()}, body
    finally:
        conn.close()


def _head_ok(url: str) -> bool:
    try:
        return _fetch(url, "HEAD", timeout=10)[0] == 200
    except OSError:
        return False


def _tunnel_put(settings: Settings, path: Path) -> Upload:
    from . import tunnel

    if not tunnel.cloudflared_bin():
        raise StorageError("cloudflared não está instalado (veja README → Ponte de upload)")
    conflict = tunnel.cloudflared_conflict()
    if conflict:
        raise StorageError(f"quick tunnel não funciona com {conflict} presente")
    work_dir = settings.runs_dir / ".tunnels" / secrets.token_hex(8)
    work_dir.mkdir(parents=True)
    ttl = settings.upload_ttl_seconds
    subprocess.Popen(
        [sys.executable, "-m", "cs.tunnel", "--file", str(path.resolve()), "--work-dir", str(work_dir),
         "--ttl", str(ttl), "--max-downloads", str(settings.upload_max_downloads)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True, cwd=str(work_dir),
    )
    ref = f"tunnel://local{work_dir}"
    deadline = time.monotonic() + TUNNEL_READY_TIMEOUT
    status: dict = {}
    while time.monotonic() < deadline:
        status = _tunnel_status(work_dir)
        if status.get("state") in {"ready", "error"}:
            break
        time.sleep(0.5)
    if status.get("state") != "ready":
        _safe_delete(settings, ref)
        raise StorageError(f"túnel não ficou pronto: {status.get('error') or 'tempo esgotado'}")
    url = status["url"]
    deadline = time.monotonic() + TUNNEL_VERIFY_TIMEOUT
    while time.monotonic() < deadline:
        if _head_ok(url):
            return Upload(ref=ref, url=url, expires_at=status["expires_at"])
        time.sleep(2)
    _safe_delete(settings, ref)
    raise StorageError("túnel criado, mas a URL pública não respondeu a tempo")


def _tunnel_delete(work_dir: Path) -> None:
    status = _tunnel_status(work_dir)
    pid = status.get("pid")
    if pid and status.get("state") not in {"closed", "error"}:
        try:
            os.killpg(pid, signal.SIGTERM)  # processo é líder da sessão: derruba o cloudflared junto
        except (ProcessLookupError, PermissionError):
            pass
        for _ in range(20):
            if _tunnel_status(work_dir).get("state") in {"closed", "error"}:
                break
            time.sleep(0.25)
        else:
            try:
                os.killpg(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    shutil.rmtree(work_dir, ignore_errors=True)


def _safe_delete(settings: Settings, ref: str) -> None:
    try:
        delete(settings, ref)
    except StorageError:
        pass


def put(settings: Settings, path: Path) -> Upload:
    _require(settings)
    path = Path(path)
    key = _key(settings, path.name)
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    ttl = settings.upload_ttl_seconds
    expires = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat(timespec="seconds")
    if settings.upload_backend == "tunnel":
        return _tunnel_put(settings, path)
    try:
        if settings.upload_backend == "s3":
            c = _s3(settings)
            c.upload_file(str(path), settings.upload_bucket, key, ExtraArgs={"ContentType": ctype})
            url = c.generate_presigned_url(
                "get_object", Params={"Bucket": settings.upload_bucket, "Key": key}, ExpiresIn=ttl
            )
        else:
            blob = _gcs_bucket(settings, settings.upload_bucket).blob(key)
            blob.upload_from_filename(str(path), content_type=ctype)
            url = blob.generate_signed_url(version="v4", expiration=timedelta(seconds=ttl), method="GET")
    except StorageError:
        raise
    except Exception as e:  # noqa: BLE001
        raise StorageError(f"falha no upload ({settings.upload_backend}): {e}") from e
    if not url.startswith("https://"):
        raise StorageError("o backend devolveu URL sem HTTPS; a Clicksign exige HTTPS")
    return Upload(ref=f"{settings.upload_backend}://{settings.upload_bucket}/{key}", url=url, expires_at=expires)


def delete(settings: Settings, ref: str) -> None:
    backend, bucket, key = _parse_ref(ref)
    if backend == "tunnel":
        work_dir = Path("/" + key.lstrip("/"))
        if settings.runs_dir.resolve() not in work_dir.resolve().parents:
            raise StorageError(f"referência de túnel fora de {settings.runs_dir}: {ref}")
        _tunnel_delete(work_dir)
        return
    try:
        if backend == "s3":
            _s3(settings).delete_object(Bucket=bucket, Key=key)
        elif backend == "gcs":
            _gcs_bucket(settings, bucket).blob(key).delete()
        elif backend == "dry-run":
            return
        else:
            raise StorageError(f"backend desconhecido: {backend}")
    except StorageError:
        raise
    except Exception as e:  # noqa: BLE001
        raise StorageError(f"falha ao apagar {ref}: {e}") from e


def probe(settings: Settings) -> tuple[bool, str]:
    """Checagem read-only de acesso ao bucket (para o doctor)."""
    try:
        _require(settings)
    except StorageError as e:
        return False, str(e)
    if settings.upload_backend == "tunnel":
        from . import tunnel

        binary = tunnel.cloudflared_bin()
        if not binary:
            return False, "cloudflared não instalado"
        conflict = tunnel.cloudflared_conflict()
        if conflict:
            return False, f"quick tunnel incompatível com {conflict}"
        try:
            ver = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, f"cloudflared não executa: {e}"
        return True, (f"túnel temporário via {ver.split(' (')[0]} "
                      f"(TTL {settings.upload_ttl_seconds}s, até {settings.upload_max_downloads} downloads)")
    try:
        if settings.upload_backend == "s3":
            _s3(settings).head_bucket(Bucket=settings.upload_bucket)
        else:
            _gcs_bucket(settings, settings.upload_bucket).reload()
    except Exception as e:  # noqa: BLE001
        return False, f"sem acesso ao bucket {settings.upload_bucket}: {e}"
    return True, f"{settings.upload_backend}://{settings.upload_bucket} acessível (TTL {settings.upload_ttl_seconds}s)"


def selftest(settings: Settings, path: Path) -> dict:
    """Sobe o arquivo, baixa pela URL pública como a Clicksign faria, compara o conteúdo e apaga."""
    import hashlib

    path = Path(path)
    t0 = time.monotonic()
    up = put(settings, path)
    t_ready = time.monotonic() - t0
    try:
        status, headers, body = _fetch(up.url, "GET", timeout=30)
        ctype = headers.get("content-type")
        same = status == 200 and hashlib.sha256(body).hexdigest() == hashlib.sha256(path.read_bytes()).hexdigest()
    finally:
        delete(settings, up.ref)
    gone = not _head_ok(up.url)
    return {
        "backend": settings.upload_backend,
        "url_host": up.url.split("/")[2],
        "seconds_to_ready": round(t_ready, 1),
        "content_type": ctype,
        "content_matches": same,
        "url_dead_after_delete": gone,
    }
