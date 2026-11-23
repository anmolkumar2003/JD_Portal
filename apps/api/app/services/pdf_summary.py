"""Generate a one-to-two page A4 candidate summary PDF with ReportLab (BSD-3-Clause)."""

from __future__ import annotations

import base64
import io
import re
from datetime import UTC, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Portal indigo primary ≈ hsl(243 75% 59%) → #4F46E5
_PRIMARY = colors.HexColor("#4F46E5")
_FG = colors.HexColor("#0F172A")
_MUTED = colors.HexColor("#64748B")
_BORDER = colors.HexColor("#E2E8F0")
_BG = colors.HexColor("#F8FAFC")
_ADVISORY = (
    "Match, ATS and interview scores are advisory only. A recruiter makes the hiring decision."
)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "org": ParagraphStyle(
            "OrgName",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=_PRIMARY,
            spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "CandTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=_FG,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "CandSub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=_MUTED,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "SectionH",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=_PRIMARY,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=_FG,
            leading=12,
            alignment=TA_LEFT,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=_MUTED,
            alignment=TA_CENTER,
            spaceBefore=12,
        ),
        "note": ParagraphStyle(
            "Note",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            textColor=_MUTED,
            leading=10,
        ),
    }


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_escape(text).replace("\n", "<br/>"), style)


def _logo_image(
    data_url: str | None, max_w: float = 36 * mm, max_h: float = 14 * mm
) -> Image | None:
    if not data_url or not data_url.startswith("data:"):
        return None
    match = re.match(r"data:image/[^;]+;base64,(.+)", data_url, re.DOTALL)
    if not match:
        return None
    try:
        raw = base64.b64decode(match.group(1))
    except Exception:
        return None
    img = Image(io.BytesIO(raw))
    img.hAlign = "LEFT"
    iw, ih = float(img.imageWidth), float(img.imageHeight)
    if iw <= 0 or ih <= 0:
        return None
    scale = min(max_w / iw, max_h / ih, 1.0)
    img.drawWidth = iw * scale
    img.drawHeight = ih * scale
    return img


def _kv_table(rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [
            Paragraph(f"<b>{_escape(k)}</b>", styles["body"]),
            Paragraph(_escape(v) if v else "—", styles["body"]),
        ]
        for k, v in rows
        if v is not None
    ]
    table = Table(data, colWidths=[42 * mm, 130 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("BACKGROUND", (0, 0), (-1, -1), _BG),
                ("BOX", (0, 0), (-1, -1), 0.4, _BORDER),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, _BORDER),
            ]
        )
    )
    return table


def build_pdf_summary(payload: dict[str, Any]) -> bytes:
    """Build a candidate summary PDF from a pre-assembled payload dict."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Candidate summary — {payload.get('candidate_name', '')}",
    )
    styles = _styles()
    story: list[Any] = []

    header_bits: list[Any] = []
    logo = _logo_image(payload.get("org_logo_data_url"))
    if logo is not None:
        header_bits.append(logo)
        header_bits.append(Spacer(1, 4))
    header_bits.append(_p(payload.get("org_name") or "Organization", styles["org"]))
    story.append(KeepTogether(header_bits))

    story.append(_p(payload.get("candidate_name") or "Candidate", styles["title"]))
    subtitle_parts = [
        p
        for p in (
            payload.get("current_title"),
            payload.get("current_company"),
        )
        if p
    ]
    if subtitle_parts:
        story.append(_p(" · ".join(subtitle_parts), styles["subtitle"]))

    overview: list[tuple[str, str]] = [
        ("Job", payload.get("job_title") or ""),
        ("Department", payload.get("department") or ""),
        ("Stage", payload.get("stage") or ""),
        ("Shortlist", "Yes" if payload.get("is_shortlisted") else "No"),
    ]
    if payload.get("include_contact"):
        overview.extend(
            [
                ("Email", payload.get("email") or ""),
                ("Phone", payload.get("phone") or ""),
                ("Location", payload.get("location") or ""),
            ]
        )
    if payload.get("include_salary"):
        overview.extend(
            [
                ("Current CTC", payload.get("current_ctc") or ""),
                ("Expected CTC", payload.get("expected_ctc") or ""),
                ("Offered CTC", payload.get("offered_ctc") or ""),
            ]
        )
    story.append(_kv_table([(k, v) for k, v in overview if v or k in {"Job", "Stage"}], styles))

    story.append(_p("Experience", styles["h2"]))
    exp = payload.get("experience_lines") or []
    if exp:
        for line in exp:
            story.append(_p(f"• {line}", styles["body"]))
    else:
        years = payload.get("total_experience_years")
        story.append(
            _p(
                f"Total experience: {years} years"
                if years is not None
                else "No experience listed.",
                styles["body"],
            )
        )

    story.append(_p("Education", styles["h2"]))
    edu = payload.get("education_lines") or []
    if edu:
        for line in edu:
            story.append(_p(f"• {line}", styles["body"]))
    else:
        story.append(_p("No education listed.", styles["body"]))

    story.append(_p("Top skills", styles["h2"]))
    skills = payload.get("top_skills") or []
    story.append(_p(", ".join(skills) if skills else "—", styles["body"]))

    story.append(_p("Scores (advisory)", styles["h2"]))
    match_score = payload.get("match_score")
    matched = payload.get("matched_skills") or []
    missing = payload.get("missing_skills") or []
    score_rows = [
        ("CV match", f"{match_score}%" if match_score is not None else "—"),
        ("Matched skills", ", ".join(matched) if matched else "—"),
        ("Missing skills", ", ".join(missing) if missing else "—"),
        (
            "ATS score",
            f"{payload['ats_score']}%" if payload.get("ats_score") is not None else "—",
        ),
    ]
    story.append(_kv_table(score_rows, styles))

    story.append(_p("Interview ratings", styles["h2"]))
    ratings = payload.get("interview_ratings") or []
    if not ratings:
        story.append(_p("No interview ratings yet.", styles["body"]))
    else:
        for rating in ratings:
            header = (
                f"{rating.get('round_name') or 'Round'} — "
                f"{rating.get('overall_rating')}/5 — "
                f"{rating.get('recommendation') or '—'}"
            )
            story.append(_p(header, styles["body"]))
            skill_bits = []
            for sr in rating.get("skill_ratings") or []:
                if isinstance(sr, dict) and sr.get("skill"):
                    skill_bits.append(f"{sr['skill']}: {sr.get('rating', '—')}")
            if skill_bits:
                story.append(_p("Skills: " + "; ".join(skill_bits), styles["body"]))
            if rating.get("strengths"):
                story.append(_p(f"Strengths: {rating['strengths']}", styles["body"]))
            if rating.get("concerns"):
                story.append(_p(f"Concerns: {rating['concerns']}", styles["body"]))
            story.append(Spacer(1, 4))

    if payload.get("include_hr_notes"):
        story.append(_p("HR notes", styles["h2"]))
        notes = payload.get("hr_notes") or []
        if notes:
            for note in notes[:20]:
                story.append(_p(f"• {note}", styles["body"]))
        else:
            story.append(_p("No notes.", styles["body"]))

    generated = payload.get("generated_at") or datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    story.append(_p(f"Generated {generated}", styles["meta"]))
    story.append(_p(_ADVISORY, styles["note"]))

    doc.build(story)
    return buffer.getvalue()
