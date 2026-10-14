"""`cs doctor` — diagnóstico read-only. Exit: 0 tudo ok, 1 há warn, 2 há error (`--strict`: warn vira error)."""

from __future__ import annotations

import importlib
import os

from . import state as st, storage
from .config import ROOT, Settings


def _c(cid: str, status: str, detail: str, fix: str = "") -> dict:
    return {"id": cid, "status": status, "detail": detail, "fix": fix}


def run(settings: Settings) -> list[dict]:
    checks: list[dict] = []

    missing = []
    for mod in ("pypdf", "docx", "jsonschema", "boto3"):
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(mod)
    checks.append(_c("python-deps", "error" if missing else "ok",
                     f"faltando: {', '.join(missing)}" if missing else "pypdf, python-docx, jsonschema, boto3",
                     "uv sync" if missing else ""))

    checks.append(_c("env-file", "ok" if settings.env_file_present else "warn",
                     ".env presente" if settings.env_file_present else ".env ausente (usando só o ambiente)",
                     "" if settings.env_file_present else "cp .env.example .env"))

    if settings.account_key:
        name = f" ({settings.account_name})" if settings.account_name else ""
        checks.append(_c("clicksign-account", "ok", f"conta {settings.account_key}{name}"))
    else:
        checks.append(_c("clicksign-account", "error", "CLICKSIGN_ACCOUNT_KEY não definido",
                         "rode o onboarding (/setup) e grave a conta no .env"))

    ok, detail = storage.probe(settings)
    if ok:
        checks.append(_c("upload-bridge", "ok", detail))
    elif settings.dry_run:
        checks.append(_c("upload-bridge", "warn", detail + " — CS_DRY_RUN=true, envio real desabilitado",
                         "UPLOAD_BACKEND=tunnel (com cloudflared) ou s3/gcs no .env"))
    else:
        checks.append(_c("upload-bridge", "error", detail,
                         "UPLOAD_BACKEND=tunnel (com cloudflared) ou s3/gcs com bucket e credenciais"))

    try:
        settings.runs_dir.mkdir(parents=True, exist_ok=True)
        writable = os.access(settings.runs_dir, os.W_OK)
    except OSError:
        writable = False
    checks.append(_c("runs-dir", "ok" if writable else "error", str(settings.runs_dir),
                     "" if writable else "ajuste CS_RUNS_DIR"))

    gi = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
    leaks = [p for p in ("runs/", ".env") if p not in gi]
    checks.append(_c("gitignore", "error" if leaks else "ok",
                     f"não ignorados: {', '.join(leaks)}" if leaks else "runs/ e .env fora do git",
                     "adicione ao .gitignore" if leaks else ""))

    pending = [r for r in st.list_runs(settings) if r["dispatch"] in {"ready", "ambiguous"}]
    checks.append(_c("pending-dispatch", "warn" if pending else "ok",
                     f"envios sem resultado registrado: {', '.join(r['run_id'] for r in pending)}" if pending
                     else "nenhum envio pendente de verificação",
                     "verifique na Clicksign e rode cs dispatch record/resolve" if pending else ""))

    if settings.dry_run:
        checks.append(_c("mode", "warn", "CS_DRY_RUN=true (nada é enviado de verdade)"))
    elif settings.silent_send:
        checks.append(_c("mode", "warn", "CS_SILENT_SEND=true: envelopes reais, mas signatários NÃO são notificados",
                         "desligue para uso real"))
    else:
        checks.append(_c("mode", "ok", "envio real habilitado (signatários são notificados)"))
    return checks


def exit_code(checks: list[dict], strict: bool = False) -> int:
    statuses = {c["status"] for c in checks}
    if "error" in statuses or (strict and "warn" in statuses):
        return 2
    return 1 if "warn" in statuses else 0
