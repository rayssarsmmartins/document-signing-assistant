import shutil

from cs import state as st
from tests.conftest import with_settings


def _tg(settings, tmp_path):
    tg = tmp_path / "tg"
    tg.mkdir()
    return with_settings(settings, telegram_tmp=tg), tg


def test_telegram_prefix_stripped_and_origin(settings, tmp_path, contract_pdf):
    settings, tg = _tg(settings, tmp_path)
    src = tg / "1759950000000-contrato-servicos.pdf"
    shutil.copy(contract_pdf, src)
    s = st.new_run(settings, src)
    assert s["document"]["origin"] == "telegram"
    assert s["document"]["filename"] == "contrato-servicos.pdf"
    assert s["envelope_name"] == "Contrato servicos"
    assert s["document"]["compressed_photo"] is False


def test_telegram_photo_flagged(settings, tmp_path):
    settings, tg = _tg(settings, tmp_path)
    src = tg / "1759950000000-photo-4242.jpg"
    src.write_bytes(b"\xff\xd8\xff")
    s = st.new_run(settings, src)
    assert s["document"]["compressed_photo"] is True
    assert s["node"] == "ask_signers"


def test_scrub_removes_telegram_original_only(settings, tmp_path, contract_pdf):
    settings, tg = _tg(settings, tmp_path)
    src = tg / "1759950000000-contrato.pdf"
    shutil.copy(contract_pdf, src)
    s = st.new_run(settings, src)
    st.scrub(settings, s["run_id"])
    assert not src.exists()
    # arquivo local do usuário nunca é apagado
    s2 = st.new_run(settings, contract_pdf)
    st.scrub(settings, s2["run_id"])
    assert contract_pdf.exists()
    assert s2["document"]["origin"] == "local"


def test_replace_from_telegram_deletes_previous_tmp(settings, tmp_path, contract_pdf):
    settings, tg = _tg(settings, tmp_path)
    a = tg / "1759950000000-v1.pdf"
    b = tg / "1759950000001-v2.pdf"
    shutil.copy(contract_pdf, a)
    shutil.copy(contract_pdf, b)
    s = st.new_run(settings, a)
    s = st.replace_document(settings, s["run_id"], b)
    assert not a.exists() and b.exists()
    assert s["document"]["filename"] == "v2.pdf"
