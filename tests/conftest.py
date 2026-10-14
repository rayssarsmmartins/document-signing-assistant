from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from cs.config import Settings

CONTRACT_TEXT = [
    "CONTRATO DE PRESTACAO DE SERVICOS",
    "CONTRATANTE: Maria Souza Andrade, e-mail maria.souza@example.com.",
    "CONTRATADO: Joao Pedro Lima, e-mail joao.lima@example.com.",
    "As partes acima identificadas tem entre si justo e contratado o presente instrumento.",
    "Clausula primeira - Do objeto: prestacao de servicos de consultoria de marketing.",
]


def make_pdf(path: Path, lines: list[str]) -> Path:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in lines:
        pdf.multi_cell(0, 8, line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))
    return path


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(runs_dir=tmp_path / "runs", account_key="acc", dry_run=True)


@pytest.fixture
def contract_pdf(tmp_path) -> Path:
    return make_pdf(tmp_path / "contrato-servicos.pdf", CONTRACT_TEXT)


@pytest.fixture
def blank_pdf(tmp_path) -> Path:
    return make_pdf(tmp_path / "scan.pdf", [""])


@pytest.fixture
def encrypted_pdf(tmp_path, contract_pdf) -> Path:
    from pypdf import PdfReader, PdfWriter

    w = PdfWriter()
    for p in PdfReader(str(contract_pdf)).pages:
        w.add_page(p)
    w.encrypt(user_password="segredo", owner_password="dono")
    out = tmp_path / "protegido.pdf"
    with out.open("wb") as f:
        w.write(f)
    return out


@pytest.fixture
def signers_ok() -> list[dict]:
    return [
        {"name": "Maria Souza Andrade", "email": "maria.souza@example.com", "role": "contractor", "auth": "email",
         "source": "extracted", "confidence": "high", "evidence": "CONTRATANTE: Maria Souza Andrade",
         "email_evidence": "e-mail maria.souza@example.com", "group": 1},
        {"name": "Joao Pedro Lima", "email": "joao.lima@example.com", "role": "contractee", "auth": "email",
         "source": "extracted", "confidence": "high", "evidence": "CONTRATADO: Joao Pedro Lima",
         "email_evidence": "e-mail joao.lima@example.com", "group": 1},
    ]


def with_settings(s: Settings, **kw) -> Settings:
    return replace(s, **kw)
