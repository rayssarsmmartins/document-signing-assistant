"""Ponto de entrada `cs`. Saída para máquina em JSON; mensagens de erro em pt-BR no stderr.

Exit codes: 0 ok · 1 aviso (doctor) / problema bloqueante (review check) · 2 erro de uso/estado.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import dispatch, doc, doctor, glossary, payload, state as st, storage
from .config import load_settings


def _out(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _read_json_arg(raw: str):
    text = sys.stdin.read() if raw == "-" else raw
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise st.StateError(f"JSON inválido: {e}") from None


def cmd_doctor(a, s):
    checks = doctor.run(s)
    if a.json:
        _out({"checks": checks})
    else:
        icon = {"ok": "✅", "warn": "⚠️ ", "error": "❌"}
        for c in checks:
            line = f"{icon[c['status']]} {c['id']}: {c['detail']}"
            if c["fix"]:
                line += f"  → {c['fix']}"
            print(line)
    return doctor.exit_code(checks, a.strict)


def cmd_doc_inspect(a, s):
    info, _ = doc.inspect(Path(a.file).expanduser())
    _out(info.to_dict())
    return 0


def cmd_run_new(a, s):
    _out(st.new_run(s, Path(a.file)))
    return 0


def cmd_run_get(a, s):
    state = st.load(s, a.run)
    if a.text:
        tp = state["document"].get("text_path")
        if not tp or not Path(tp).exists():
            raise st.StateError("não há texto extraído deste documento")
        print(Path(tp).read_text(encoding="utf-8"))
        return 0
    if not a.events:
        state = {k: v for k, v in state.items() if k != "events"}
    _out(state)
    return 0


def cmd_run_patch(a, s):
    _out(st.patch(s, a.run, _read_json_arg(a.json)))
    return 0


def cmd_run_metric(a, s):
    st.bump(s, a.run, a.kind, a.detail)
    return 0


def cmd_run_list(a, s):
    _out(st.list_runs(s, only_open=a.open, max_age_days=a.max_age_days))
    return 0


def cmd_run_abandon(a, s):
    _out({"run_id": st.abandon(s, a.run)["run_id"], "node": "abandoned"})
    return 0


def cmd_run_replace_doc(a, s):
    _out(st.replace_document(s, a.run, Path(a.file), keep_signers=not a.reset_signers))
    return 0


def cmd_run_scrub(a, s):
    _out({"removed": st.scrub(s, a.run)})
    return 0


def cmd_run_prune(a, s):
    _out({"removed": st.prune(s, a.days or s.retention_days)})
    return 0


def cmd_review_check(a, s):
    state = st.load(s, a.run)
    probs = payload.check(state, s)
    _out({"problems": probs, "blocking": len(payload.blocking(probs))})
    return 1 if payload.blocking(probs) else 0


def cmd_review_show(a, s):
    state = st.load(s, a.run)
    text, h, probs = payload.render_summary(state, s)
    blocks = payload.blocking(probs)
    if not blocks:
        state["summary"] = {"hash": h, "shown_at": st.now_iso()}
        state["node"] = "review"
        state["metrics"]["summaries_shown"] += 1
        st.add_event(state, "summary_shown", {"hash": h})
        st.save(s, state)
    if a.json:
        _out({"text": text, "hash": h if not blocks else None, "problems": probs})
    else:
        print(text)
        print("---")
        print(f"hash={h if not blocks else '-'} bloqueios={len(blocks)}")
    return 1 if blocks else 0


def cmd_dispatch_prepare(a, s):
    _out(dispatch.prepare(s, a.run, a.hash))
    return 0


def cmd_dispatch_record(a, s):
    r = dispatch.record(s, a.run, a.envelope_id, a.status, a.deadline, a.keep_upload)
    _out({"run_id": r["run_id"], "dispatch": r["dispatch"]})
    return 0


def cmd_dispatch_fail(a, s):
    r = dispatch.fail(s, a.run, a.error, a.ambiguous)
    _out({"run_id": r["run_id"], "dispatch": r["dispatch"], "node": r["node"]})
    return 0


def cmd_dispatch_resolve(a, s):
    r = dispatch.resolve_not_created(s, a.run)
    _out({"run_id": r["run_id"], "dispatch": r["dispatch"], "node": r["node"]})
    return 0


def cmd_upload_put(a, s):
    up = storage.put(s, Path(a.file).expanduser())
    _out({"ref": up.ref, "url": up.url, "expires_at": up.expires_at})
    return 0


def cmd_upload_delete(a, s):
    storage.delete(s, a.ref)
    _out({"deleted": a.ref})
    return 0


def cmd_upload_selftest(a, s):
    r = storage.selftest(s, Path(a.file).expanduser())
    _out(r)
    return 0 if r["content_matches"] and r["url_dead_after_delete"] else 1


def cmd_glossary_role(a, s):
    role = glossary.role_from_pt(a.term)
    _out({"term": a.term, "role": role, "label": glossary.role_label(role) if role else None})
    return 0 if role else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cs", description="Ferramentas locais do workspace Envio Pontual")
    sub = p.add_subparsers(dest="domain", required=True)

    d = sub.add_parser("doctor", help="diagnóstico read-only (exit 0/1/2)")
    d.add_argument("--json", action="store_true")
    d.add_argument("--strict", action="store_true")
    d.set_defaults(fn=cmd_doctor)

    dc = sub.add_parser("doc", help="inspeção de arquivo").add_subparsers(dest="verb", required=True)
    x = dc.add_parser("inspect")
    x.add_argument("file")
    x.set_defaults(fn=cmd_doc_inspect)

    r = sub.add_parser("run", help="estado da jornada").add_subparsers(dest="verb", required=True)
    x = r.add_parser("new", help="inicia jornada a partir de um arquivo (nó 1)")
    x.add_argument("file")
    x.set_defaults(fn=cmd_run_new)
    x = r.add_parser("get")
    x.add_argument("run")
    x.add_argument("--text", action="store_true", help="imprime o texto extraído do documento")
    x.add_argument("--events", action="store_true")
    x.set_defaults(fn=cmd_run_get)
    x = r.add_parser("patch", help="merge de campos editáveis (JSON ou - para stdin)")
    x.add_argument("run")
    x.add_argument("json")
    x.set_defaults(fn=cmd_run_patch)
    x = r.add_parser("metric")
    x.add_argument("run")
    x.add_argument("kind", choices=["question", "edit", "user_turn"])
    x.add_argument("--detail")
    x.set_defaults(fn=cmd_run_metric)
    x = r.add_parser("list")
    x.add_argument("--open", action="store_true")
    x.add_argument("--max-age-days", type=int)
    x.set_defaults(fn=cmd_run_list)
    x = r.add_parser("abandon")
    x.add_argument("run")
    x.set_defaults(fn=cmd_run_abandon)
    x = r.add_parser("replace-doc", help="E8: troca o arquivo da jornada")
    x.add_argument("run")
    x.add_argument("file")
    x.add_argument("--reset-signers", action="store_true")
    x.set_defaults(fn=cmd_run_replace_doc)
    x = r.add_parser("scrub", help="apaga texto e cópia do documento")
    x.add_argument("run")
    x.set_defaults(fn=cmd_run_scrub)
    x = r.add_parser("prune")
    x.add_argument("--days", type=int)
    x.set_defaults(fn=cmd_run_prune)

    rv = sub.add_parser("review", help="resumo (nó 5)").add_subparsers(dest="verb", required=True)
    x = rv.add_parser("check")
    x.add_argument("run")
    x.set_defaults(fn=cmd_review_check)
    x = rv.add_parser("show")
    x.add_argument("run")
    x.add_argument("--json", action="store_true")
    x.set_defaults(fn=cmd_review_show)

    dp = sub.add_parser("dispatch", help="envio (nó 6)").add_subparsers(dest="verb", required=True)
    x = dp.add_parser("prepare")
    x.add_argument("run")
    x.add_argument("--hash", required=True)
    x.set_defaults(fn=cmd_dispatch_prepare)
    x = dp.add_parser("record")
    x.add_argument("run")
    x.add_argument("--envelope-id", required=True)
    x.add_argument("--status")
    x.add_argument("--deadline")
    x.add_argument("--keep-upload", action="store_true")
    x.set_defaults(fn=cmd_dispatch_record)
    x = dp.add_parser("fail")
    x.add_argument("run")
    x.add_argument("--error", required=True)
    x.add_argument("--ambiguous", action="store_true")
    x.set_defaults(fn=cmd_dispatch_fail)
    x = dp.add_parser("resolve")
    x.add_argument("run")
    x.add_argument("--not-created", action="store_true", required=True)
    x.set_defaults(fn=cmd_dispatch_resolve)

    up = sub.add_parser("upload", help="ponte de upload").add_subparsers(dest="verb", required=True)
    x = up.add_parser("put")
    x.add_argument("file")
    x.set_defaults(fn=cmd_upload_put)
    x = up.add_parser("delete")
    x.add_argument("ref")
    x.set_defaults(fn=cmd_upload_delete)
    x = up.add_parser("selftest", help="sobe, baixa pela URL pública, compara e apaga")
    x.add_argument("file")
    x.set_defaults(fn=cmd_upload_selftest)

    g = sub.add_parser("glossary").add_subparsers(dest="verb", required=True)
    x = g.add_parser("role", help="termo pt-BR -> papel canônico")
    x.add_argument("term")
    x.set_defaults(fn=cmd_glossary_role)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    try:
        return args.fn(args, settings)
    except (st.StateError, storage.StorageError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
