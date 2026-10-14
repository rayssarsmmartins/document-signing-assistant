"""Resolução do root do workspace e da configuração (.env + ambiente)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _find_root() -> Path:
    env = os.environ.get("CS_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # src/cs/config.py -> parents[2] é o root do repo (instalação editable via uv).
    here = Path(__file__).resolve().parents[2]
    if (here / "AGENTS.md").exists():
        return here
    cur = Path.cwd().resolve()
    for p in (cur, *cur.parents):
        if (p / "AGENTS.md").exists() and (p / "pyproject.toml").exists():
            return p
    raise SystemExit("cs: não encontrei o root do workspace (AGENTS.md). Defina CS_ROOT.")


ROOT = _find_root()
SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _bool(v: str | None, default: bool = False) -> bool:
    if v is None or v == "":
        return default
    return v.strip().lower() in {"1", "true", "yes", "sim", "on"}


@dataclass(frozen=True)
class Settings:
    account_key: str = ""
    account_name: str = ""
    upload_backend: str = ""  # s3 | gcs
    upload_bucket: str = ""
    upload_prefix: str = "envio-pontual/"
    upload_ttl_seconds: int = 600
    upload_max_downloads: int = 3
    s3_endpoint_url: str = ""
    s3_region: str = ""
    runs_dir: Path = field(default_factory=lambda: ROOT / "runs")
    retention_days: int = 7
    send_group: bool = False
    allowed_auths: tuple[str, ...] = ("email", "sms", "whatsapp")
    dry_run: bool = False
    silent_send: bool = False
    env_file_present: bool = False
    telegram_tmp: Path = field(default_factory=lambda: Path.home() / ".pi" / "agent" / "tmp" / "telegram")


def load_settings() -> Settings:
    file_values = parse_env_file(ROOT / ".env")
    merged = {**file_values, **{k: v for k, v in os.environ.items()}}

    def g(key: str, default: str = "") -> str:
        return merged.get(key, default) or default

    runs_dir = Path(g("CS_RUNS_DIR", str(ROOT / "runs"))).expanduser()
    if not runs_dir.is_absolute():
        runs_dir = ROOT / runs_dir
    auths = tuple(a.strip() for a in g("CS_ALLOWED_AUTHS", "email,sms,whatsapp").split(",") if a.strip())
    return Settings(
        account_key=g("CLICKSIGN_ACCOUNT_KEY"),
        account_name=g("CLICKSIGN_ACCOUNT_NAME"),
        upload_backend=g("UPLOAD_BACKEND").lower(),
        upload_bucket=g("UPLOAD_BUCKET"),
        upload_prefix=g("UPLOAD_PREFIX", "envio-pontual/"),
        upload_ttl_seconds=int(g("UPLOAD_TTL_SECONDS", "600")),
        upload_max_downloads=int(g("UPLOAD_MAX_DOWNLOADS", "3")),
        s3_endpoint_url=g("S3_ENDPOINT_URL"),
        s3_region=g("S3_REGION", g("AWS_REGION")),
        runs_dir=runs_dir,
        retention_days=int(g("CS_RETENTION_DAYS", "7")),
        send_group=_bool(g("CLICKSIGN_SEND_GROUP"), False),
        allowed_auths=auths,
        dry_run=_bool(g("CS_DRY_RUN"), False),
        silent_send=_bool(g("CS_SILENT_SEND"), False),
        env_file_present=(ROOT / ".env").exists(),
        telegram_tmp=Path(g("CS_TELEGRAM_TMP", str(Path.home() / ".pi" / "agent" / "tmp" / "telegram"))).expanduser(),
    )
