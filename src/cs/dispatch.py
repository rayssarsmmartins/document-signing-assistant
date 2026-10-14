"""Travas do envio irreversível (nó 6, E13).

Sequência obrigatória:
  cs review show RUN          -> mostra o resumo e grava summary.hash
  (usuário diz "enviar")
  cs dispatch prepare RUN --hash H   -> confere hash, sobe o arquivo, grava status=ready, imprime args
  (agente chama clicksign_create_envelope_with_file_url com os args)
  cs dispatch record RUN --envelope-id X   |   cs dispatch fail RUN --error "..." [--ambiguous]

`ready` persistido ANTES da chamada ao MCP é o que torna o retry seguro: se a sessão cair
no meio, o próximo `prepare` recusa e exige verificação na Clicksign.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import payload, state as st, storage
from .config import Settings


class DispatchError(st.StateError):
    pass


def prepare(settings: Settings, run_id: str, confirmed_hash: str) -> dict:
    s = st.load(settings, run_id)
    d = s["dispatch"]
    if d["status"] == "sent":
        raise DispatchError(f"já enviado (id {d.get('envelope_id')}); não vou enviar de novo")
    if d["status"] in {"ready", "ambiguous"}:
        raise DispatchError(
            f"há uma tentativa de envio de {d.get('prepared_at')} sem resultado registrado. "
            "Verifique na Clicksign se o documento foi criado antes de tentar de novo; depois rode "
            "`cs dispatch record RUN --envelope-id ID` (se foi criado) ou "
            "`cs dispatch resolve RUN --not-created` (se não foi)"
        )
    summary = s.get("summary")
    if not summary or not summary.get("hash"):
        raise DispatchError("nenhum resumo foi mostrado para este estado; rode `cs review show` e peça confirmação")
    current = payload.content_hash(s, settings)
    if confirmed_hash != summary["hash"] or confirmed_hash != current:
        raise DispatchError(
            "a confirmação não corresponde ao resumo atual (algo mudou depois do resumo); "
            "mostre o resumo de novo e peça nova confirmação"
        )
    blocks = payload.blocking(payload.check(s, settings))
    if blocks:
        raise DispatchError("ainda há pendências: " + "; ".join(p["text"] for p in blocks))

    if settings.dry_run:
        up = storage.Upload(
            ref=f"dry-run://local/{s['document']['filename']}",
            url=f"https://dry-run.invalid/{s['document']['filename']}",
            expires_at=st.now_iso(),
        )
    else:
        up = storage.put(settings, Path(s["document"]["stored_path"]))
    args = payload.build_args(s, settings, up.url)

    run_path = st.run_dir(settings, run_id)
    (run_path / "dispatch-args.json").write_text(json.dumps(args, ensure_ascii=False, indent=2), encoding="utf-8")
    s["dispatch"].update({
        "status": "ready",
        "payload_hash": current,
        "prepared_at": st.now_iso(),
        "upload_ref": up.ref,
        "file_url_expires_at": up.expires_at,
        "upload_deleted": False,
        "error": None,
        "dry_run": settings.dry_run,
    })
    s["node"] = "dispatching"
    st.add_event(s, "dispatch_prepared", {"payload_hash": current, "dry_run": settings.dry_run})
    st.save(settings, s)
    return {
        "dry_run": settings.dry_run,
        "tool": "clicksign_create_envelope_with_file_url",
        "args": args,
        "url_expires_at": up.expires_at,
        "next": (
            "DRY_RUN: NÃO chame o MCP; rode `cs dispatch record RUN --envelope-id dry-run`"
            if settings.dry_run
            else "chame o MCP com `args` agora e registre o resultado com `cs dispatch record` ou `cs dispatch fail`"
        ),
    }


def _cleanup_upload(settings: Settings, s: dict) -> str | None:
    ref = s["dispatch"].get("upload_ref")
    if not ref or s["dispatch"].get("upload_deleted"):
        return None
    try:
        storage.delete(settings, ref)
        s["dispatch"]["upload_deleted"] = True
        return None
    except storage.StorageError as e:
        return str(e)


def record(settings: Settings, run_id: str, envelope_id: str, envelope_status: str | None = None,
           deadline_at: str | None = None, keep_upload: bool = False) -> dict:
    s = st.load(settings, run_id)
    if s["dispatch"]["status"] == "sent":
        if envelope_status or deadline_at:  # permite completar dados depois de get_envelope_details
            s["dispatch"]["envelope_status"] = envelope_status or s["dispatch"].get("envelope_status")
            s["dispatch"]["deadline_at"] = deadline_at or s["dispatch"].get("deadline_at")
            st.save(settings, s)
            return s
        raise DispatchError("envio já registrado")
    if s["dispatch"]["status"] not in {"ready", "ambiguous"}:
        raise DispatchError("não há envio preparado para registrar")
    s["dispatch"].update({
        "status": "sent",
        "envelope_id": envelope_id,
        "envelope_status": envelope_status,
        "deadline_at": deadline_at,
        "sent_at": st.now_iso(),
        "error": None,
    })
    s["node"] = "dispatched"
    warn = None if keep_upload else _cleanup_upload(settings, s)
    st.add_event(s, "dispatched", {"envelope_id": envelope_id, "cleanup_error": warn})
    st.save(settings, s)
    return s


def fail(settings: Settings, run_id: str, error: str, ambiguous: bool) -> dict:
    """ambiguous=True: não sabemos se o envelope foi criado (timeout, 5xx, sessão caiu).
    ambiguous=False: erro definitivo de validação (nada foi criado) — pode corrigir e tentar de novo."""
    s = st.load(settings, run_id)
    if s["dispatch"]["status"] != "ready":
        raise DispatchError("não há envio em andamento para marcar como falho")
    s["dispatch"]["error"] = error
    if ambiguous:
        s["dispatch"]["status"] = "ambiguous"
    else:
        s["dispatch"]["status"] = "failed"
        s["node"] = "review"
        s["summary"] = None
        _cleanup_upload(settings, s)
    st.add_event(s, "dispatch_failed", {"ambiguous": ambiguous, "error": error})
    st.save(settings, s)
    return s


def resolve_not_created(settings: Settings, run_id: str) -> dict:
    s = st.load(settings, run_id)
    if s["dispatch"]["status"] not in {"ready", "ambiguous"}:
        raise DispatchError("nada a resolver")
    s["dispatch"]["status"] = "failed"
    s["dispatch"]["error"] = (s["dispatch"].get("error") or "") + " | verificado: não criado"
    s["node"] = "review"
    s["summary"] = None
    _cleanup_upload(settings, s)
    st.add_event(s, "dispatch_resolved_not_created")
    st.save(settings, s)
    return s
