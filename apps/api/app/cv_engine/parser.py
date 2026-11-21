"""CV parsing: section segmentation, regex, spaCy NER, experience years. CV-03."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from calendar import monthrange
from datetime import date
from typing import Any

from app.cv_engine.skills import find_skills_in_text
from app.cv_engine.types import (
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    ExtractResult,
    ParsedCV,
)

logger = logging.getLogger(__name__)

PARSER_VERSION = "rule-1.0"

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s\-.]?)?(?:\(?\d{2,4}\)?[\s\-.]?)?\d{3,4}[\s\-.]?\d{3,4}")
URL_RE = re.compile(r"https?://[^\s)>\]]+|www\.[^\s)>\]]+|linkedin\.com/[^\s)>\]]+", re.I)
DATE_TOKEN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|"
    r"\d{1,2})[/\-\s.]*(?:\d{2,4})|Present|Current|Now"  # noqa: S105
)
DATE_RANGE_RE = re.compile(
    rf"(?P<start>{DATE_TOKEN})\s*[–\-|to]+\s*(?P<end>{DATE_TOKEN})",
    re.IGNORECASE,
)
MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "profile", "about", "objective"),
    "experience": (
        "experience",
        "work experience",
        "employment",
        "professional experience",
        "work history",
    ),
    "education": ("education", "academic", "academics"),
    "skills": ("skills", "technical skills", "core competencies", "technologies"),
    "certifications": ("certifications", "certificates", "licenses"),
}


class CVParser(ABC):
    @abstractmethod
    def parse(self, text: str, *, file_meta: ExtractResult | None = None) -> ParsedCV:
        raise NotImplementedError


def _parse_month_year(token: str) -> date | None:
    raw = token.strip()
    if re.match(r"(?i)present|current|now", raw):
        return date.today()
    m = re.match(r"(?i)([A-Za-z]+)\s*[/\-.]?\s*(\d{2,4})", raw)
    if m:
        month = MONTH_MAP.get(m.group(1).lower())
        year = int(m.group(2))
        if year < 100:
            year += 2000 if year < 50 else 1900
        if month:
            return date(year, month, 1)
    m2 = re.match(r"(\d{1,2})[/\-.](\d{2,4})", raw)
    if m2:
        month = int(m2.group(1))
        year = int(m2.group(2))
        if year < 100:
            year += 2000 if year < 50 else 1900
        if 1 <= month <= 12:
            return date(year, month, 1)
    m3 = re.match(r"(\d{4})", raw)
    if m3:
        return date(int(m3.group(1)), 1, 1)
    return None


def merge_experience_years(ranges: list[tuple[date, date]]) -> float:
    """Merge overlapping date ranges and return total years (1 decimal)."""
    if not ranges:
        return 0.0
    normalized = sorted((min(a, b), max(a, b)) for a, b in ranges)
    merged: list[list[date]] = [[normalized[0][0], normalized[0][1]]]
    for start, end in normalized[1:]:
        last = merged[-1]
        if start <= last[1]:
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    total_days = 0
    for start, end in merged:
        # Inclusive-ish month span
        days = (end - start).days + monthrange(end.year, end.month)[1] // 4
        total_days += max(days, 0)
    return round(total_days / 365.25, 1)


def _heading_key(line: str) -> str | None:
    cleaned = re.sub(r"[^a-zA-Z\s]", "", line).strip().lower()
    if not cleaned or len(cleaned) > 40:
        return None
    for key, aliases in SECTION_ALIASES.items():
        if cleaned in aliases:
            return key
    return None


def segment_sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    sections: dict[str, list[str]] = {"_preamble": []}
    current = "_preamble"
    for line in lines:
        key = _heading_key(line.strip())
        if key:
            current = key
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {key: "\n".join(vals).strip() for key, vals in sections.items() if vals}


def _load_nlp() -> Any | None:
    try:
        import spacy

        try:
            return spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spacy_model_missing_en_core_web_sm")
            return None
    except ImportError:
        logger.warning("spacy_not_installed")
        return None


def _first_person_name(nlp: Any, text: str) -> str | None:
    doc = nlp(text[:2000])
    for ent in doc.ents:
        if ent.label_ == "PERSON" and 1 <= len(ent.text.split()) <= 4:
            name = str(ent.text).strip()
            return name or None
    return None


def _orgs_and_locations(nlp: Any, text: str) -> tuple[list[str], list[str]]:
    doc = nlp(text[:8000])
    orgs = [e.text.strip() for e in doc.ents if e.label_ == "ORG"]
    locs = [e.text.strip() for e in doc.ents if e.label_ in {"GPE", "LOC"}]
    return orgs, locs


def _parse_experience_block(block: str, orgs: list[str]) -> list[ExperienceEntry]:
    entries: list[ExperienceEntry] = []
    if not block:
        return entries
    chunks = re.split(r"\n{2,}", block)
    for chunk in chunks:
        lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
        if not lines:
            continue
        date_match = DATE_RANGE_RE.search(chunk)
        start = end = None
        if date_match:
            start = date_match.group("start").strip()
            end = date_match.group("end").strip()
        title = lines[0][:120]
        company = None
        for org in orgs:
            if org.lower() in chunk.lower():
                company = org
                break
        if company is None and len(lines) > 1:
            company = lines[1][:120]
        entries.append(
            ExperienceEntry(
                title=title,
                company=company,
                start_date=start,
                end_date=end,
                description=chunk[:1000],
            )
        )
    return entries[:20]


def _parse_education_block(block: str) -> list[EducationEntry]:
    entries: list[EducationEntry] = []
    if not block:
        return entries
    degree_re = re.compile(
        r"(Bachelor|Master|B\.?Tech|M\.?Tech|B\.?E\.?|M\.?S\.?|MBA|Ph\.?D|BSc|MSc|BA|MA)[^,\n]{0,60}",
        re.I,
    )
    for chunk in re.split(r"\n{2,}", block):
        degree_m = degree_re.search(chunk)
        date_m = DATE_RANGE_RE.search(chunk) or re.search(r"(20\d{2}|19\d{2})", chunk)
        lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
        if not lines and not degree_m:
            continue
        entries.append(
            EducationEntry(
                degree=degree_m.group(0).strip() if degree_m else (lines[0] if lines else None),
                institution=lines[1] if len(lines) > 1 else (lines[0] if lines else None),
                start_date=date_m.group("start")
                if date_m and hasattr(date_m, "groupdict") and date_m.groupdict().get("start")
                else None,
                end_date=(
                    date_m.group("end")
                    if date_m and hasattr(date_m, "groupdict") and date_m.groupdict().get("end")
                    else (date_m.group(0) if date_m else None)
                ),
            )
        )
    return entries[:15]


def _parse_certs(block: str) -> list[CertificationEntry]:
    if not block:
        return []
    certs: list[CertificationEntry] = []
    for line in block.splitlines():
        line = line.strip(" -•\t")
        if len(line) < 3:
            continue
        certs.append(CertificationEntry(name=line[:200]))
    return certs[:30]


class RuleBasedParser(CVParser):
    def parse(self, text: str, *, file_meta: ExtractResult | None = None) -> ParsedCV:
        sections = segment_sections(text)
        email_m = EMAIL_RE.search(text)
        phone_m = PHONE_RE.search(text)
        links = list(dict.fromkeys(URL_RE.findall(text)))[:20]

        nlp = _load_nlp()
        full_name = None
        orgs: list[str] = []
        locs: list[str] = []
        if nlp is not None:
            full_name = _first_person_name(nlp, sections.get("_preamble", text[:500]))
            orgs, locs = _orgs_and_locations(nlp, text)

        skills_text = sections.get("skills", "") or text
        skills = find_skills_in_text(skills_text)
        if len(skills) < 3:
            skills = list(dict.fromkeys(skills + find_skills_in_text(text)))

        experience = _parse_experience_block(sections.get("experience", ""), orgs)
        education = _parse_education_block(sections.get("education", ""))
        certifications = _parse_certs(sections.get("certifications", ""))

        ranges: list[tuple[date, date]] = []
        for exp in experience:
            if exp.start_date and exp.end_date:
                start = _parse_month_year(exp.start_date)
                end = _parse_month_year(exp.end_date)
                if start and end:
                    ranges.append((start, end))
        # Also scan whole text for date ranges if experience block was thin
        if not ranges:
            for match in DATE_RANGE_RE.finditer(text):
                start = _parse_month_year(match.group("start"))
                end = _parse_month_year(match.group("end"))
                if start and end:
                    ranges.append((start, end))
        years = merge_experience_years(ranges) if ranges else None

        found_sections = [k for k in SECTION_ALIASES if sections.get(k)]
        confidence: dict[str, float] = {
            "email": 0.95 if email_m else 0.0,
            "phone": 0.85 if phone_m else 0.0,
            "name": 0.7 if full_name else 0.2,
            "skills": min(1.0, len(skills) / 10),
            "experience": min(1.0, len(experience) / 3),
        }

        return ParsedCV(
            full_name=full_name,
            email=email_m.group(0) if email_m else None,
            phone=phone_m.group(0).strip() if phone_m else None,
            location=locs[0] if locs else None,
            links=links,
            summary=(sections.get("summary") or "")[:1500] or None,
            skills=skills,
            experience=experience,
            education=education,
            certifications=certifications,
            total_experience_years=years,
            sections_found=found_sections,
            confidence=confidence,
            parser_version=PARSER_VERSION,
            ocr_used=bool(file_meta and file_meta.ocr_used),
        )
