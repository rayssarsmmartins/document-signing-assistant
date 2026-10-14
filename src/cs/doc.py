"""Leitura do documento (nó 1) e classificação de ilegibilidade (E9).

Decisão de produto codificada aqui:
- Formato que a Clicksign **não aceita**, arquivo com senha, corrompido ou > 20 MB
  → `next = "ask_new_file"` (não há como enviar; pedir outro arquivo).
- Formato que a Clicksign aceita mas que não conseguimos ler (scan, imagem, .doc)
  → `next = "ask_signers"` (envia normalmente; só não dá para sugerir quem assina — vai para 3B).
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

SENDABLE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".txt", ".doc", ".docx"}
MAX_BYTES = 20 * 1024 * 1024
MIN_CHARS_PER_PAGE = 40  # abaixo disso o PDF é tratado como scan


@dataclass
class DocInfo:
    filename: str
    extension: str
    size_bytes: int
    sha256: str
    status: str  # ok | no_text | unreadable_format | encrypted | corrupt | unsupported_format | too_large
    can_send: bool
    can_read: bool
    next: str  # read | ask_signers | ask_new_file
    pages: int | None = None
    chars: int = 0
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _pdf_text(path: Path) -> tuple[str, int, str]:
    """Retorna (texto, páginas, status)."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(path))
    except PdfReadError:
        return "", 0, "corrupt"
    except Exception:  # noqa: BLE001 - qualquer falha de parsing é "corrompido" para a persona
        return "", 0, "corrupt"
    if reader.is_encrypted:
        try:
            ok = reader.decrypt("")
        except Exception:  # noqa: BLE001
            ok = 0
        if not ok:
            return "", 0, "encrypted"
    try:
        pages = len(reader.pages)
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
    except Exception:  # noqa: BLE001
        return "", 0, "corrupt"
    text = "\n\n".join(parts).strip()
    if len(text) < MIN_CHARS_PER_PAGE * max(pages, 1) * 0.5:
        return text, pages, "no_text"
    return text, pages, "ok"


def _docx_text(path: Path) -> tuple[str, str]:
    import docx  # python-docx

    try:
        d = docx.Document(str(path))
    except Exception:  # noqa: BLE001
        return "", "corrupt"
    parts = [p.text for p in d.paragraphs]
    for table in d.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    text = "\n".join(p for p in parts if p is not None).strip()
    return text, ("ok" if text else "no_text")


def inspect(path: Path) -> tuple[DocInfo, str]:
    """Inspeciona o arquivo. Retorna (info, texto extraído)."""
    path = Path(path)
    ext = path.suffix.lower()
    size = path.stat().st_size
    digest = sha256_file(path)

    def info(status: str, can_send: bool, can_read: bool, nxt: str, reason: str, pages=None, chars=0):
        return DocInfo(
            filename=path.name, extension=ext, size_bytes=size, sha256=digest, status=status,
            can_send=can_send, can_read=can_read, next=nxt, pages=pages, chars=chars, reason=reason,
        )

    if ext not in SENDABLE_EXTENSIONS:
        return info("unsupported_format", False, False, "ask_new_file",
                    f"formato {ext or '(sem extensão)'} não é aceito para assinatura; aceitos: PDF, Word, imagem ou texto"), ""
    if size > MAX_BYTES:
        return info("too_large", False, False, "ask_new_file", "arquivo maior que 20 MB"), ""

    if ext == ".pdf":
        text, pages, status = _pdf_text(path)
        if status == "encrypted":
            return info(status, False, False, "ask_new_file", "PDF protegido por senha"), ""
        if status == "corrupt":
            return info(status, False, False, "ask_new_file", "não consegui abrir o PDF (arquivo corrompido?)"), ""
        if status == "no_text":
            return info(status, True, False, "ask_signers",
                        "PDF parece digitalizado (sem texto selecionável)", pages, len(text)), text
        return info("ok", True, True, "read", "", pages, len(text)), text

    if ext == ".docx":
        text, status = _docx_text(path)
        if status == "corrupt":
            return info(status, False, False, "ask_new_file", "não consegui abrir o arquivo Word"), ""
        if status == "no_text":
            return info(status, True, False, "ask_signers", "documento Word sem texto", None, 0), ""
        return info("ok", True, True, "read", "", None, len(text)), text

    if ext == ".txt":
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")
        text = text.strip()
        if not text:
            return info("no_text", True, False, "ask_signers", "arquivo de texto vazio"), ""
        return info("ok", True, True, "read", "", None, len(text)), text

    if ext == ".doc":
        return info("unreadable_format", True, False, "ask_signers",
                    "formato Word antigo (.doc): envio funciona, mas não consigo ler para sugerir quem assina"), ""

    # imagens
    return info("no_text", True, False, "ask_signers", "imagem: sem leitura de texto (OCR não habilitado)"), ""
