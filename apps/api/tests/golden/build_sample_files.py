#!/usr/bin/env python3
"""Convert golden .txt CVs into PDF and DOCX samples."""

from __future__ import annotations

from pathlib import Path

CVS = Path(__file__).parent / "cvs"


def to_docx(text: str, path: Path) -> None:
    from docx import Document

    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    doc.save(str(path))


def to_pdf(text: str, path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(path), pagesize=A4)
    lines = pdf.beginText(50, A4[1] - 50)
    lines.setFont("Helvetica", 10)
    for line in text[:5000].splitlines():
        lines.textLine(line)
    pdf.drawText(lines)
    pdf.save()


def main() -> None:
    for txt in sorted(CVS.glob("*.txt")):
        content = txt.read_text(encoding="utf-8")
        to_docx(content, txt.with_suffix(".docx"))
        to_pdf(content, txt.with_suffix(".pdf"))
        print(f"wrote {txt.stem}.docx/.pdf")


if __name__ == "__main__":
    main()
