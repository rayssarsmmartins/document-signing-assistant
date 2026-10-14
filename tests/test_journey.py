import json

import pytest

from cs import dispatch, glossary, payload, state as st
from tests.conftest import with_settings


def test_new_run_reads_document(settings, contract_pdf):
    s = st.new_run(settings, contract_pdf)
    assert s["node"] == "read"
    assert s["envelope_name"] == "Contrato servicos"
    assert s["dispatch"]["status"] == "none"
    text = (settings.runs_dir / s["run_id"] / "document.txt").read_text()
    assert "Joao Pedro Lima" in text


def test_encrypted_run_node(settings, encrypted_pdf):
    s = st.new_run(settings, encrypted_pdf)
    assert s["node"] == "ask_new_file"


def test_patch_rejects_protected_fields(settings, contract_pdf):
    s = st.new_run(settings, contract_pdf)
    with pytest.raises(st.StateError):
        st.patch(settings, s["run_id"], {"dispatch": {"status": "sent"}})
    with pytest.raises(st.StateError):
        st.patch(settings, s["run_id"], {"node": "dispatched"})


def test_patch_validates_schema(settings, contract_pdf):
    s = st.new_run(settings, contract_pdf)
    with pytest.raises(st.StateError):
        st.patch(settings, s["run_id"], {"signers": [{"name": "Sem Papel"}]})


def test_missing_email_blocks_and_names_signer(settings, contract_pdf, signers_ok):
    s = st.new_run(settings, contract_pdf)
    signers_ok[1]["email"] = None
    signers_ok[1]["email_evidence"] = None
    st.patch(settings, s["run_id"], {"signers": signers_ok})
    probs = payload.check(st.load(settings, s["run_id"]), settings)
    codes = {(p["code"], p.get("signer")) for p in payload.blocking(probs)}
    assert codes == {("missing_email", 1)}


def test_extracted_email_without_evidence_blocks(settings, contract_pdf, signers_ok):
    s = st.new_run(settings, contract_pdf)
    signers_ok[0]["email_evidence"] = None
    st.patch(settings, s["run_id"], {"signers": signers_ok})
    codes = {p["code"] for p in payload.blocking(payload.check(st.load(settings, s["run_id"]), settings))}
    assert "email_without_evidence" in codes


def test_user_provided_email_needs_no_evidence(settings, contract_pdf, signers_ok):
    s = st.new_run(settings, contract_pdf)
    signers_ok[0].update(source="user", email_evidence=None)
    st.patch(settings, s["run_id"], {"signers": signers_ok})
    assert not payload.blocking(payload.check(st.load(settings, s["run_id"]), settings))


def test_name_needs_surname_and_phone_auth_needs_phone(settings, contract_pdf, signers_ok):
    s = st.new_run(settings, contract_pdf)
    signers_ok[0]["name"] = "Maria"
    signers_ok[1].update(auth="whatsapp", phone=None)
    st.patch(settings, s["run_id"], {"signers": signers_ok})
    codes = {p["code"] for p in payload.blocking(payload.check(st.load(settings, s["run_id"]), settings))}
    assert {"name_incomplete", "missing_phone"} <= codes


def test_auth_outside_mvp_blocks(settings, contract_pdf, signers_ok):
    s = st.new_run(settings, contract_pdf)
    signers_ok[0]["auth"] = "selfie"
    st.patch(settings, s["run_id"], {"signers": signers_ok})
    codes = {p["code"] for p in payload.blocking(payload.check(st.load(settings, s["run_id"]), settings))}
    assert "auth_not_allowed" in codes


def test_summary_uses_persona_vocabulary(settings, contract_pdf, signers_ok):
    s = st.new_run(settings, contract_pdf)
    st.patch(settings, s["run_id"], {"signers": signers_ok, "message": "Olá! Segue o contrato."})
    text, h, probs = payload.render_summary(st.load(settings, s["run_id"]), settings)
    assert "contratante" in text and "contratado(a)" in text
    assert "código por e-mail" in text
    assert "Posso enviar?" in text
    for forbidden in ["envelope", "requirement", "auth", "role", "signer", "provide_evidence", "{"]:
        assert forbidden not in text.lower()
    assert not payload.blocking(probs)


def test_group_warning_when_order_not_supported(settings, contract_pdf, signers_ok):
    s = st.new_run(settings, contract_pdf)
    signers_ok[1]["group"] = 2
    st.patch(settings, s["run_id"], {"signers": signers_ok})
    text, _, _ = payload.render_summary(st.load(settings, s["run_id"]), settings)
    assert "ao mesmo tempo" in text


def _ready_run(settings, contract_pdf, signers_ok):
    s = st.new_run(settings, contract_pdf)
    st.patch(settings, s["run_id"], {"signers": signers_ok, "message": "Olá! Segue o contrato."})
    state = st.load(settings, s["run_id"])
    _, h, _ = payload.render_summary(state, settings)
    state["summary"] = {"hash": h, "shown_at": st.now_iso()}
    st.save(settings, state)
    return s["run_id"], h


def test_dispatch_requires_matching_hash(settings, contract_pdf, signers_ok):
    run, h = _ready_run(settings, contract_pdf, signers_ok)
    with pytest.raises(dispatch.DispatchError):
        dispatch.prepare(settings, run, "000000000000")


def test_edit_after_summary_invalidates_confirmation(settings, contract_pdf, signers_ok):
    run, h = _ready_run(settings, contract_pdf, signers_ok)
    signers_ok[1]["email"] = "outro@example.com"
    signers_ok[1]["source"] = "user"
    st.patch(settings, run, {"signers": signers_ok})
    s = st.load(settings, run)
    assert s["summary"] is None and s["metrics"]["edits"] == 1
    with pytest.raises(dispatch.DispatchError):
        dispatch.prepare(settings, run, h)


def test_dry_run_dispatch_flow_and_args(settings, contract_pdf, signers_ok):
    run, h = _ready_run(settings, contract_pdf, signers_ok)
    out = dispatch.prepare(settings, run, h)
    assert out["dry_run"] is True
    args = out["args"]
    assert args["document"]["filename"] == "contrato-servicos.pdf"
    assert args["document"]["file_url"].startswith("https://")
    assert args["signers"][0]["requirements"] == [
        {"action": "agree", "role": "contractor"},
        {"action": "provide_evidence", "auth": "email"},
    ]
    assert "group" not in args["signers"][0]
    assert args["notifications"]["message"] == "Olá! Segue o contrato."
    saved = json.loads((settings.runs_dir / run / "dispatch-args.json").read_text())
    assert saved == args
    # segunda tentativa sem registrar resultado é recusada (E13)
    with pytest.raises(dispatch.DispatchError):
        dispatch.prepare(settings, run, h)
    # edição também é recusada enquanto o envio não é resolvido
    with pytest.raises(st.StateError):
        st.patch(settings, run, {"message": "outra"})
    s = dispatch.record(settings, run, "dry-run")
    assert s["node"] == "dispatched" and s["dispatch"]["status"] == "sent"
    with pytest.raises(dispatch.DispatchError):
        dispatch.prepare(settings, run, h)


def test_group_sent_when_enabled(settings, contract_pdf, signers_ok):
    settings = with_settings(settings, send_group=True)
    signers_ok[0]["group"] = 2
    run, h = _ready_run(settings, contract_pdf, signers_ok)
    args = dispatch.prepare(settings, run, h)["args"]
    assert [x["name"] for x in args["signers"]] == ["Joao Pedro Lima", "Maria Souza Andrade"]
    assert [x["group"] for x in args["signers"]] == [1, 2]


def test_ambiguous_failure_then_resolve(settings, contract_pdf, signers_ok):
    run, h = _ready_run(settings, contract_pdf, signers_ok)
    dispatch.prepare(settings, run, h)
    dispatch.fail(settings, run, "timeout", ambiguous=True)
    with pytest.raises(dispatch.DispatchError):
        dispatch.prepare(settings, run, h)
    s = dispatch.resolve_not_created(settings, run)
    assert s["node"] == "review" and s["summary"] is None


def test_definitive_failure_allows_fix_and_retry(settings, contract_pdf, signers_ok):
    run, h = _ready_run(settings, contract_pdf, signers_ok)
    dispatch.prepare(settings, run, h)
    s = dispatch.fail(settings, run, "400 nome inválido", ambiguous=False)
    assert s["dispatch"]["status"] == "failed" and s["node"] == "review"
    state = st.load(settings, run)
    _, h2, _ = payload.render_summary(state, settings)
    state["summary"] = {"hash": h2, "shown_at": st.now_iso()}
    st.save(settings, state)
    assert dispatch.prepare(settings, run, h2)["args"]


def test_replace_document_keeps_signers(settings, contract_pdf, blank_pdf, signers_ok):
    s = st.new_run(settings, contract_pdf)
    st.patch(settings, s["run_id"], {"signers": signers_ok})
    s2 = st.replace_document(settings, s["run_id"], blank_pdf)
    assert len(s2["signers"]) == 2
    assert s2["document"]["replaced_sha256"] == [s["document"]["sha256"]]
    assert s2["node"] == "ask_signers"


def test_open_runs_and_scrub(settings, contract_pdf):
    s = st.new_run(settings, contract_pdf)
    assert [r["run_id"] for r in st.list_runs(settings, only_open=True)] == [s["run_id"]]
    st.abandon(settings, s["run_id"])
    assert st.list_runs(settings, only_open=True) == []
    removed = st.scrub(settings, s["run_id"])
    assert any(r.endswith("document.txt") for r in removed)


def test_glossary_roles():
    assert glossary.role_from_pt("Locatária") == "lessee"
    assert glossary.role_from_pt("testemunha") == "witness"
    assert glossary.role_from_pt("parte") is None  # ambíguo: perguntar


def test_summary_shows_representation_and_notes(settings, contract_pdf, signers_ok):
    s = st.new_run(settings, contract_pdf)
    signers_ok[0]["represents"] = "ACME Comercio Ltda"
    st.patch(settings, s["run_id"], {
        "signers": signers_ok,
        "envelope_name": "Contrato de consultoria — ACME",
        "summary_notes": ["O documento tem espaço para 2 testemunhas — se quiser incluir alguém, é só me dizer."],
    })
    text, _, probs = payload.render_summary(st.load(settings, s["run_id"]), settings)
    assert text.splitlines()[0] == "📄 Contrato de consultoria — ACME (contrato-servicos.pdf, 1 página)"
    assert "contratante, pela ACME Comercio Ltda" in text
    assert "ℹ️ O documento tem espaço para 2 testemunhas" in text
    assert not payload.blocking(probs)


def test_silent_send_suppresses_notifications(settings, contract_pdf, signers_ok):
    settings = with_settings(settings, silent_send=True)
    run, h = _ready_run(settings, contract_pdf, signers_ok)
    args = dispatch.prepare(settings, run, h)["args"]
    assert all(x["communicate_events"] == {"signature_request": "none"} for x in args["signers"])


def test_normal_send_has_no_communicate_override(settings, contract_pdf, signers_ok):
    run, h = _ready_run(settings, contract_pdf, signers_ok)
    args = dispatch.prepare(settings, run, h)["args"]
    assert all("communicate_events" not in x for x in args["signers"])
