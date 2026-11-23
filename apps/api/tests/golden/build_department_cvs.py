#!/usr/bin/env python3
"""Build synthetic golden CVs (PDF/DOCX) for 9 departments, OCR, and two-column fixtures."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "departments"
OUT.mkdir(parents=True, exist_ok=True)

DEPARTMENTS: dict[str, dict[str, object]] = {
    "content_writing": {
        "name": "Aisha Khan",
        "email": "aisha.khan@example.com",
        "phone": "+91 98100 11101",
        "title": "Senior Content Writer",
        "skills": ["Content Writing", "Copywriting", "SEO", "SEO Writing", "WordPress"],
        "body_skill": "SEO blogs and product copy",
    },
    "shopify": {
        "name": "Rohan Mehta",
        "email": "rohan.mehta@example.com",
        "phone": "+91 98100 11102",
        "title": "Shopify Developer",
        "skills": ["Shopify", "Shopify Themes", "Liquid", "JavaScript", "CSS"],
        "body_skill": "Shopify Plus themes and checkout extensions",
    },
    "ppc": {
        "name": "Neha Kapoor",
        "email": "neha.kapoor@example.com",
        "phone": "+91 98100 11103",
        "title": "PPC Specialist",
        "skills": ["PPC", "Google Ads", "SEO", "Google Analytics", "SEM"],
        "body_skill": "Google Ads and paid search campaigns",
    },
    "android": {
        "name": "Arjun Patel",
        "email": "arjun.patel@example.com",
        "phone": "+91 98100 11104",
        "title": "Android Engineer",
        "skills": ["Kotlin", "Jetpack Compose", "Android SDK", "Java", "Firebase"],
        "body_skill": "Kotlin apps with Jetpack Compose",
    },
    "ios": {
        "name": "Meera Iyer",
        "email": "meera.iyer@example.com",
        "phone": "+91 98100 11105",
        "title": "iOS Engineer",
        "skills": ["Swift", "SwiftUI", "UIKit", "iOS", "Xcode"],
        "body_skill": "Swift and SwiftUI product features",
    },
    "flutter": {
        "name": "Kabir Singh",
        "email": "kabir.singh@example.com",
        "phone": "+91 98100 11106",
        "title": "Flutter Developer",
        "skills": ["Flutter", "Dart", "Firebase", "REST", "Git"],
        "body_skill": "Flutter mobile apps in Dart",
    },
    "quality_analyst": {
        "name": "Sana Rahman",
        "email": "sana.rahman@example.com",
        "phone": "+91 98100 11107",
        "title": "Quality Analyst",
        "skills": ["QA", "Selenium", "Cypress", "Appium", "Jira"],
        "body_skill": "Selenium and Cypress test automation",
    },
    "ux_design": {
        "name": "Diya Nair",
        "email": "diya.nair@example.com",
        "phone": "+91 98100 11108",
        "title": "UX Designer",
        "skills": ["UX Design", "Figma", "Adobe XD", "Wireframing", "Prototyping"],
        "body_skill": "Figma prototypes and UX research",
    },
    "project_manager": {
        "name": "Vikram Desai",
        "email": "vikram.desai@example.com",
        "phone": "+91 98100 11109",
        "title": "Project Manager",
        "skills": ["Project Management", "Agile", "Scrum", "Jira", "Stakeholder Management"],
        "body_skill": "Agile delivery and stakeholder management",
    },
}


def cv_text(slug: str, meta: dict[str, object]) -> str:
    skills = ", ".join(meta["skills"])  # type: ignore[arg-type]
    return f"""{meta["name"]}
{meta["email"]} | {meta["phone"]}
Bengaluru, India

Summary
{meta["title"]} with 6 years of experience in {meta["body_skill"]}.

Experience
{meta["title"]}
Pixel Works
Jan 2020 - Present
Delivered {meta["body_skill"]} for production teams.

Associate {meta["title"]}
Bright Labs
Jun 2017 - Dec 2019
Supported launches and documentation.

Education
B.A. / B.Tech
Example University
2013 - 2017

Skills
{skills}
"""


def to_docx(text: str, path: Path) -> None:
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    doc.save(str(path))


def to_pdf(text: str, path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    lines = pdf.beginText(50, A4[1] - 50)
    lines.setFont("Helvetica", 10)
    for line in text.splitlines():
        lines.textLine(line[:110])
    pdf.drawText(lines)
    pdf.save()


def to_two_column_pdf(text: str, path: Path) -> None:
    """Two-column layout: identity/experience left; education/skills right."""
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    lines = text.splitlines()
    # Keep skills intact by rendering them as individual right-column lines.
    skills_idx = next((i for i, line in enumerate(lines) if line.strip().lower() == "skills"), None)
    if skills_idx is None:
        mid = len(lines) // 2
        col1, col2 = lines[:mid], lines[mid:]
    else:
        col1 = lines[:skills_idx]
        skill_names = [s.strip() for s in lines[skills_idx + 1].split(",") if s.strip()]
        col2 = ["Education", "B.Tech", "Example University", "2013 - 2017", "Skills", *skill_names]
        drop = {"education", "b.a. / b.tech", "example university", "2013 - 2017"}
        col1 = [ln for ln in col1 if ln.strip().lower() not in drop]
    y1, y2 = height - 50, height - 50
    pdf.setFont("Helvetica", 9)
    for line in col1:
        pdf.drawString(40, y1, line[:48])
        y1 -= 12
    for line in col2:
        pdf.drawString(width / 2 + 10, y2, line[:48])
        y2 -= 12
    pdf.save()


def to_scanned_pdf(text: str, path: Path) -> None:
    """Image-only PDF (no text layer) so extract falls back to OCR."""
    from io import BytesIO

    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.utils import ImageReader

    img = Image.new("RGB", (2480, 3508), "white")
    draw = ImageDraw.Draw(img)
    font_paths = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    )
    font: object = ImageFont.load_default()
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 48)
            break
        except OSError:
            continue
    y = 80
    for line in text.splitlines():
        draw.text((80, y), line[:90], fill=(0, 0, 0), font=font)
        y += 64
    buf = BytesIO()
    img.save(buf, format="PNG", dpi=(300, 300))
    buf.seek(0)
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.drawImage(ImageReader(buf), 0, 0, width=A4[0], height=A4[1])
    pdf.save()


def main() -> None:
    for slug, meta in DEPARTMENTS.items():
        text = cv_text(slug, meta)
        (OUT / f"{slug}.txt").write_text(text, encoding="utf-8")
        to_docx(text, OUT / f"{slug}.docx")
        to_pdf(text, OUT / f"{slug}.pdf")
        print(f"wrote {slug}.txt/.docx/.pdf")

    shopify = cv_text("shopify", DEPARTMENTS["shopify"])
    to_two_column_pdf(shopify, OUT / "two_column_shopify.pdf")
    print("wrote two_column_shopify.pdf")

    unusual = """Jane Unusual
jane.unusual@example.com | +91 99999 88877
Bengaluru, India

Summary
Engineer with hands-on Shopify and Python experience across product teams.

Experience
Engineer
Shopify Labs
01/15/2019 - current
Python tooling and Shopify apps for merchants.

Junior Engineer
Beta Inc
Jan'19 - Dec 2020
Supporting Kotlin mobile experiments.

Skills
Python, Shopify, Kotlin
"""
    (OUT / "unusual_dates.txt").write_text(unusual, encoding="utf-8")
    to_pdf(unusual, OUT / "unusual_dates.pdf")
    to_docx(unusual, OUT / "unusual_dates.docx")
    to_scanned_pdf(unusual, OUT / "scanned_unusual.pdf")
    print("wrote unusual_dates + scanned_unusual.pdf")


if __name__ == "__main__":
    main()
