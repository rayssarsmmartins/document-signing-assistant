"""Estado da jornada em runs/<run_id>/journey-state.json.

O estado é a memória da conversa: permite editar sem bifurcar (volta ao nó), retomar
uma jornada abandonada (E14) e impedir envio duplicado (E13).
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema

from . import doc as docmod
from .config import SCHEMAS_DIR, Settings

STATE_FILE = "journey-state.json"
EDITABLE_KEYS = {"node", "envelope_name", "signers", "mentioned_non_signers", "message", "summary_notes"}
CONTENT_KEYS = {"envelope_name", "signers", "message"}  # mudam o que vai ser enviado
AGENT_SETTABLE_NODES = {"intake", "read", "signers", "ask_signers", "auth", "review", "abandoned", "ask_new_file"}
OPEN_NODES = {"intake", "read", "signers", "ask_signers", "auth", "review", "dispatching", "ask_new_file"}


class StateError(Exception):
    """Erro de uso do estado — mensagem em pt-BR, pronta para o agente."""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _schema() -> dict:
    return json.loads((SCHEMAS_DIR / "journey-state.schema.json").read_text(encoding="utf-8"))


def validate(state: dict) -> None:
    try:
        jsonschema.validate(state, _schema())
    except jsonschema.ValidationError as e:
        path = "/".join(str(p) for p in e.absolute_path) or "(raiz)"
        raise StateError(f"estado inválido em {path}: {e.message}") from None


def run_dir(settings: Settings, run_id: str) -> Path:
    d = settings.runs_dir / run_id
    if not (d / STATE_FILE).exists():
        raise StateError(f"jornada {run_id} não encontrada em {settings.runs_dir}")
    return d


def load(settings: Settings, run_id: str) -> dict:
    return json.loads((run_dir(settings, run_id) / STATE_FILE).read_text(encoding="utf-8"))


def save(settings: Settings, state: dict) -> None:
    state["updated_at"] = now_iso()
    validate(state)
    d = settings.runs_dir / state["run_id"]
    d.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".state-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, d / STATE_FILE)


def add_event(state: dict, kind: str, detail=None) -> None:
    ev = {"ts": now_iso(), "kind": kind, "node": state.get("node", "")}
    if detail is not None:
        ev["detail"] = detail
    state["events"].append(ev)


TELEGRAM_PHOTO_RE = re.compile(r"^(\d+-)?photo-\d+\.jpg$")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def _store_document(d: Path, src: Path, settings: Settings) -> tuple[Path, dict, str]:
    origin = "telegram" if _is_within(src, settings.telegram_tmp) else "local"
    name = src.name
    if origin == "telegram":
        # a ponte salva como "<epoch_ms>-<nome original>"; o prefixo não pode chegar ao signatário
        name = re.sub(r"^\d{10,}-", "", name) or src.name
    orig_dir = d / "original"
    if orig_dir.exists():
        shutil.rmtree(orig_dir)
    orig_dir.mkdir(parents=True)
    stored = orig_dir / name
    shutil.copy2(src, stored)
    info, text = docmod.inspect(stored)
    text_path = None
    if text:
        text_path = d / "document.txt"
        text_path.write_text(text, encoding="utf-8")
    document = {
        "filename": info.filename,
        "original_path": str(src.resolve()),
        "stored_path": str(stored),
        "text_path": str(text_path) if text_path else None,
        "extension": info.extension,
        "size_bytes": info.size_bytes,
        "sha256": info.sha256,
        "status": info.status,
        "can_send": info.can_send,
        "can_read": info.can_read,
        "pages": info.pages,
        "chars": info.chars,
        "reason": info.reason,
        "origin": origin,
        "compressed_photo": origin == "telegram" and bool(TELEGRAM_PHOTO_RE.match(src.name)),
    }
    return stored, document, info.next


def _node_for(next_step: str) -> str:
    return {"read": "read", "ask_signers": "ask_signers", "ask_new_file": "ask_new_file"}[next_step]


def default_envelope_name(filename: str) -> str:
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    stem = " ".join(stem.split())
    return stem[:1].upper() + stem[1:] if stem else "Documento para assinatura"


def new_run(settings: Settings, file: Path) -> dict:
    file = Path(file).expanduser()
    if not file.is_file():
        raise StateError(f"arquivo não encontrado: {file}")
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
    d = settings.runs_dir / run_id
    d.mkdir(parents=True, exist_ok=False)
    _, document, nxt = _store_document(d, file, settings)
    state = {
        "run_id": run_id,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "node": _node_for(nxt),
        "document": document,
        "envelope_name": default_envelope_name(document["filename"]),
        "signers": [],
        "mentioned_non_signers": [],
        "summary_notes": [],
        "message": None,
        "summary": None,
        "dispatch": {"status": "none", "upload_deleted": False, "dry_run": settings.dry_run},
        "metrics": {"questions_asked": 0, "edits": 0, "summaries_shown": 0, "user_turns": 0},
        "events": [],
    }
    add_event(state, "document_attached", {"status": document["status"], "next": nxt})
    save(settings, state)
    return state


def replace_document(settings: Settings, run_id: str, file: Path, keep_signers: bool = True) -> dict:
    """E8 — troca de documento. Por padrão preserva signatários (decisão a validar)."""
    state = load(settings, run_id)
    _ensure_not_sent(state)
    d = run_dir(settings, run_id)
    old_sha = state["document"]["sha256"]
    old_orig = state["document"].get("original_path")
    if old_orig and Path(old_orig).is_file() and _is_within(Path(old_orig), settings.telegram_tmp) \
            and Path(old_orig).resolve() != Path(file).expanduser().resolve():
        Path(old_orig).unlink()  # versão anterior vinda do Telegram: não deixar cópia órfã
    old_text = d / "document.txt"
    if old_text.exists():
        old_text.unlink()
    _, document, nxt = _store_document(d, Path(file).expanduser(), settings)
    document["replaced_sha256"] = [*state["document"].get("replaced_sha256", []), old_sha]
    state["document"] = document
    if not keep_signers:
        state["signers"] = []
        state["mentioned_non_signers"] = []
    state["summary"] = None
    state["node"] = _node_for(nxt)
    state["envelope_name"] = default_envelope_name(document["filename"])
    add_event(state, "document_replaced", {"keep_signers": keep_signers, "status": document["status"]})
    save(settings, state)
    return state


def _ensure_not_sent(state: dict) -> None:
    if state["dispatch"]["status"] == "sent":
        raise StateError("este documento já foi enviado; alterações agora exigem um novo envio")
    if state["dispatch"]["status"] in {"ready", "ambiguous"}:
        raise StateError(
            "há uma tentativa de envio sem resultado registrado; resolva com `cs dispatch record` "
            "ou `cs dispatch resolve --not-created` antes de editar"
        )


def patch(settings: Settings, run_id: str, changes: dict) -> dict:
    state = load(settings, run_id)
    unknown = set(changes) - EDITABLE_KEYS
    if unknown:
        raise StateError(f"campos não editáveis via patch: {sorted(unknown)} (editáveis: {sorted(EDITABLE_KEYS)})")
    _ensure_not_sent(state)
    if "node" in changes and changes["node"] not in AGENT_SETTABLE_NODES:
        raise StateError(f"o nó '{changes['node']}' só é definido pelos comandos de envio")
    content_changed = any(k in changes and changes[k] != state.get(k) for k in CONTENT_KEYS)
    for k, v in changes.items():
        state[k] = v
    if content_changed:
        if state.get("summary"):
            state["metrics"]["edits"] += 1
            add_event(state, "edit_after_summary", sorted(k for k in CONTENT_KEYS if k in changes))
        state["summary"] = None  # qualquer mudança invalida a confirmação anterior
    add_event(state, "patch", sorted(changes))
    save(settings, state)
    return state


def bump(settings: Settings, run_id: str, metric: str, detail=None) -> dict:
    state = load(settings, run_id)
    key = {"question": "questions_asked", "edit": "edits", "user_turn": "user_turns"}.get(metric)
    if not key:
        raise StateError("métrica deve ser question | edit | user_turn")
    state["metrics"][key] += 1
    add_event(state, metric, detail)
    save(settings, state)
    return state


def list_runs(settings: Settings, only_open: bool = False, max_age_days: int | None = None) -> list[dict]:
    out = []
    if not settings.runs_dir.exists():
        return out
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days) if max_age_days else None
    for d in sorted(settings.runs_dir.iterdir(), reverse=True):
        f = d / STATE_FILE
        if not f.exists():
            continue
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if only_open and s["node"] not in OPEN_NODES:
            continue
        if cutoff and datetime.fromisoformat(s["updated_at"]) < cutoff:
            continue
        out.append({
            "run_id": s["run_id"],
            "node": s["node"],
            "document": s["document"]["filename"],
            "envelope_name": s.get("envelope_name"),
            "signers": len(s["signers"]),
            "dispatch": s["dispatch"]["status"],
            "updated_at": s["updated_at"],
        })
    return out


def abandon(settings: Settings, run_id: str) -> dict:
    state = load(settings, run_id)
    _ensure_not_sent(state)
    state["node"] = "abandoned"
    add_event(state, "abandoned")
    save(settings, state)
    return state


def scrub(settings: Settings, run_id: str) -> list[str]:
    """Remove conteúdo sensível da jornada (texto extraído e cópia do arquivo). Mantém o estado.

    Também apaga o arquivo original quando ele veio do diretório temporário da ponte do
    Telegram (que não limpa sozinha). Arquivos do usuário fora desse diretório nunca são tocados.
    """
    d = run_dir(settings, run_id)
    removed = []
    s = load(settings, run_id)
    originals = [s["document"].get("original_path")]
    for p in originals:
        if p and Path(p).is_file() and _is_within(Path(p), settings.telegram_tmp):
            Path(p).unlink()
            removed.append(p)
    for p in [d / "document.txt", d / "dispatch-args.json"]:
        if p.exists():
            p.unlink()
            removed.append(str(p))
    orig = d / "original"
    if orig.exists():
        shutil.rmtree(orig)
        removed.append(str(orig))
    return removed


def prune(settings: Settings, days: int) -> list[str]:
    """Apaga jornadas encerradas (enviadas/abandonadas) mais antigas que `days` e abertas há mais de 4x isso."""
    removed = []
    if not settings.runs_dir.exists():
        return removed
    now = datetime.now(timezone.utc)
    for d in settings.runs_dir.iterdir():
        f = d / STATE_FILE
        if not f.exists():
            continue
        s = json.loads(f.read_text(encoding="utf-8"))
        age = now - datetime.fromisoformat(s["updated_at"])
        closed = s["node"] in {"dispatched", "abandoned"}
        if (closed and age > timedelta(days=days)) or age > timedelta(days=days * 4):
            if s["dispatch"]["status"] in {"ready", "ambiguous"}:
                continue  # nunca apagar evidência de envio não resolvido
            shutil.rmtree(d)
            removed.append(s["run_id"])
    return removed
