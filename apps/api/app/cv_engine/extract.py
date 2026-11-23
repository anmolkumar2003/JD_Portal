"""Text extraction from PDF/DOCX with OCR fallback. CV-02."""

from __future__ import annotations

import io
import logging
from typing import Literal

from app.cv_engine.types import ExtractResult

logger = logging.getLogger(__name__)

OCR_THRESHOLD = 200
MimeHint = Literal[
    "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
]


def _guess_kind(file_bytes: bytes, mime_or_ext: str | None) -> str:
    hint = (mime_or_ext or "").lower().strip()
    if hint in {"pdf", "application/pdf"} or file_bytes[:4] == b"%PDF":
        return "pdf"
    if (
        hint in {"docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        or file_bytes[:2] == b"PK"
    ):
        return "docx"
    if hint.endswith(".pdf"):
        return "pdf"
    if hint.endswith(".docx"):
        return "docx"
    return "pdf" if file_bytes[:4] == b"%PDF" else "docx"


def _extract_pdf_pdfplumber(file_bytes: bytes) -> tuple[str, int]:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip(), page_count


def _extract_pdf_pypdf(file_bytes: bytes) -> tuple[str, int]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(parts).strip(), len(reader.pages)


def _extract_docx(file_bytes: bytes) -> tuple[str, int]:
    from docx import Document

    document = Document(io.BytesIO(file_bytes))
    parts = [p.text for p in document.paragraphs if p.text]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    # DOCX has no reliable page count without layout; approximate by chars.
    text = "\n".join(parts).strip()
    page_count = max(1, (len(text) // 3000) + 1) if text else 1
    return text, page_count


def _ocr_pdf(file_bytes: bytes) -> str:
    """Render PDF pages and OCR with Tesseract. Best-effort; returns empty on failure."""
    try:
        import pypdfium2 as pdfium
        import pytesseract
    except ImportError:
        logger.warning("ocr_dependencies_missing")
        return ""

    parts: list[str] = []
    try:
        doc = pdfium.PdfDocument(file_bytes)
    except Exception:
        logger.exception("ocr_failed")
        return ""
    try:
        for page in doc:
            image = page.render(scale=2).to_pil()
            parts.append(pytesseract.image_to_string(image) or "")
    except Exception:
        logger.exception("ocr_failed")
        return ""
    finally:
        doc.close()
    return "\n".join(parts).strip()


def extract_text(file_bytes: bytes, mime_or_ext: str | None = None) -> ExtractResult:
    """Extract plain text from a CV file. Uses OCR if extracted text is under 200 chars."""
    kind = _guess_kind(file_bytes, mime_or_ext)
    method = kind
    page_count: int | None = None
    text = ""
    ocr_used = False

    if kind == "pdf":
        try:
            text, page_count = _extract_pdf_pdfplumber(file_bytes)
            method = "pdfplumber"
        except Exception:
            logger.warning("pdfplumber_failed_falling_back_to_pypdf")
            text, page_count = _extract_pdf_pypdf(file_bytes)
            method = "pypdf"
        if len(text) < OCR_THRESHOLD:
            ocr_text = _ocr_pdf(file_bytes)
            if len(ocr_text) > len(text):
                text = ocr_text
                ocr_used = True
                method = "tesseract"
    else:
        text, page_count = _extract_docx(file_bytes)
        method = "python-docx"

    return ExtractResult(
        text=text,
        ocr_used=ocr_used,
        page_count=page_count,
        method=method,
        file_size=len(file_bytes),
    )
