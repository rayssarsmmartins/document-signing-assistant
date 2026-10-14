"""Servidor do túnel com um cloudflared falso: valida caminho secreto, limites e encerramento."""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

FAKE_CLOUDFLARED = """#!/usr/bin/env bash
echo "INF |  https://fake-test-tunnel.trycloudflare.com  |" >&2
exec sleep 300
"""


@pytest.fixture
def tunnel(tmp_path, contract_pdf):
    fake = tmp_path / "cloudflared"
    fake.write_text(FAKE_CLOUDFLARED)
    fake.chmod(0o755)
    work = tmp_path / "work"
    env = {**os.environ, "CLOUDFLARED_BIN": str(fake)}
    proc = subprocess.Popen(
        [sys.executable, "-m", "cs.tunnel", "--file", str(contract_pdf), "--work-dir", str(work),
         "--ttl", "30", "--max-downloads", "2"],
        env=env, start_new_session=True,
    )
    status = {}
    for _ in range(60):
        try:
            status = json.loads((work / "status.json").read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            status = {}
        if status.get("state") == "ready":
            break
        time.sleep(0.1)
    assert status.get("state") == "ready", status
    yield proc, work, status
    if proc.poll() is None:
        proc.terminate()
        proc.wait(5)


def _local(status, path=None):
    secret_path = "/" + status["url"].split("/", 3)[3]
    return f"http://127.0.0.1:{status['port']}{path or secret_path}"


def _code(url, method="GET"):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method=method), timeout=5) as r:
            return r.status, r.read(), r.headers.get("Content-Type")
    except urllib.error.HTTPError as e:
        return e.code, b"", None


def test_public_url_shape(tunnel):
    _, _, status = tunnel
    assert status["url"].startswith("https://fake-test-tunnel.trycloudflare.com/")
    assert status["url"].endswith("/contrato-servicos.pdf")


def test_only_secret_path_served_and_download_limit(tunnel, contract_pdf):
    proc, work, status = tunnel
    assert _code(_local(status, "/"))[0] == 404
    assert _code(_local(status, "/contrato-servicos.pdf"))[0] == 404
    assert _code(_local(status), "POST")[0] == 405
    assert _code(_local(status), "HEAD")[0] == 200  # HEAD não consome download
    code, body, ctype = _code(_local(status))
    assert code == 200 and body == contract_pdf.read_bytes() and ctype == "application/pdf"
    assert _code(_local(status))[0] == 200
    proc.wait(10)  # limite de 2 downloads atingido -> encerra sozinho
    final = json.loads((work / "status.json").read_text())
    assert final["state"] == "closed" and final["downloads"] == 2


def test_sigterm_closes(tunnel):
    proc, work, _ = tunnel
    proc.terminate()
    proc.wait(10)
    assert json.loads((work / "status.json").read_text())["state"] == "closed"
