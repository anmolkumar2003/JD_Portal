import io
import zipfile
from dataclasses import dataclass

from fastapi import status

from app.core.errors import AppError

MAX_CV_BYTES = 5 * 1024 * 1024

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@dataclass(frozen=True)
class ValidatedFile:
    mime_type: str
    extension: str


def _invalid(message: str) -> AppError:
    return AppError(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_file", message)


def _is_docx(data: bytes) -> bool:
    if not data.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return "word/document.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False


def validate_cv(data: bytes) -> ValidatedFile:
    """Identify the file by its content (magic bytes), never by name or declared type."""
    if not data:
        raise _invalid("The CV file is empty.")
    if len(data) > MAX_CV_BYTES:
        raise _invalid("The CV must be 5 MB or smaller.")
    if data.startswith(b"%PDF-"):
        return ValidatedFile(PDF_MIME, "pdf")
    if _is_docx(data):
        return ValidatedFile(DOCX_MIME, "docx")
    raise _invalid("The CV must be a PDF or Word (.docx) document.")
