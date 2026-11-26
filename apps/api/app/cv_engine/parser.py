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
    ProjectEntry,
)

logger = logging.getLogger(__name__)

PARSER_VERSION = "rule-1.3"

# Autofill only when the parser is at least this sure (else leave the field blank).
AUTOFILL_MIN_CONFIDENCE = 0.6

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# Broad candidate; digit-count validated in _extract_phone (10–15 digits).
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s\-.]*)?(?:\(?\d{1,5}\)?[\s\-.]*){1,5}\d{2,}")
URL_RE = re.compile(r"https?://[^\s)>\]]+|www\.[^\s)>\]]+|linkedin\.com/[^\s)>\]]+", re.I)
_MONTH_NAME = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)
# Jan'19, Jan 2019, 01/15/2019, 01/2019, 2019, Present/Current/Now
DATE_TOKEN = (
    rf"(?:Present|Current|Now|"
    rf"(?:{_MONTH_NAME})[\s/\-.'’]*\d{{2,4}}|"
    rf"\d{{1,2}}[/\-.]\d{{1,2}}[/\-.]\d{{2,4}}|"
    rf"\d{{1,2}}[/\-.]\d{{2,4}}|"
    rf"\d{{4}})"
)
# Include en/em dashes, ASCII hyphen, middle dot (common in PDF extract), and "to".
DATE_RANGE_RE = re.compile(
    rf"(?P<start>{DATE_TOKEN})\s*[–—\-·•|to]+\s*(?P<end>{DATE_TOKEN})",
    re.IGNORECASE,
)
YEARS_MENTION_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+experience|\s+building|\s+in)?",
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
    "summary": (
        "summary",
        "professional summary",
        "career summary",
        "executive summary",
        "profile",
        "professional profile",
        "about",
        "about me",
        "objective",
        "career objective",
        "professional objective",
    ),
    "experience": (
        "experience",
        "work experience",
        "employment",
        "employment history",
        "professional experience",
        "work history",
        "career history",
        "relevant experience",
    ),
    "projects": (
        "projects",
        "project",
        "personal projects",
        "key projects",
        "selected projects",
        "academic projects",
        "side projects",
        "notable projects",
    ),
    "education": (
        "education",
        "academic",
        "academics",
        "academic background",
        "education and training",
    ),
    "skills": (
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
        "technologies",
        "tech stack",
        "key skills",
    ),
    "certifications": (
        "certifications",
        "certificates",
        "licenses",
        "licenses and certifications",
    ),
}

# Tokens that mark CV section headings — never accept these as a person name.
_HEADING_NAME_TOKENS = frozenset(
    {
        "summary",
        "professional",
        "profile",
        "objective",
        "about",
        "experience",
        "employment",
        "education",
        "academic",
        "academics",
        "skills",
        "skill",
        "projects",
        "project",
        "certifications",
        "certificates",
        "certification",
        "licenses",
        "competencies",
        "technologies",
        "history",
        "references",
        "interests",
        "hobbies",
        "achievements",
        "awards",
        "publications",
        "languages",
        "declaration",
        "curriculum",
        "vitae",
        "resume",
        "contact",
        "details",
        "personal",
        "information",
        "career",
        "work",
        "training",
    }
)

# Words that may decorate a section title ("Technical Skills") without being the section itself.
_HEADING_MODIFIERS = frozenset(
    {
        "professional",
        "career",
        "executive",
        "personal",
        "key",
        "selected",
        "notable",
        "relevant",
        "academic",
        "side",
        "technical",
        "core",
        "work",
        "employment",
        "additional",
        "other",
        "my",
        "and",
        "the",
        "of",
    }
)

# Common job-title heads — never accept these as a person name.
_TITLE_NAME_TOKENS = frozenset(
    {
        "engineer",
        "developer",
        "manager",
        "analyst",
        "consultant",
        "architect",
        "designer",
        "specialist",
        "lead",
        "director",
        "intern",
        "officer",
        "executive",
        "associate",
        "scientist",
        "administrator",
        "coordinator",
        "programmer",
        "technician",
    }
)


class CVParser(ABC):
    @abstractmethod
    def parse(self, text: str, *, file_meta: ExtractResult | None = None) -> ParsedCV:
        raise NotImplementedError


def _normalize_year(year: int) -> int:
    if year < 100:
        return year + 2000 if year < 50 else year + 1900
    return year


def _parse_month_year(token: str) -> date | None:  # noqa: C901, PLR0911
    raw = token.strip().strip(".,;")
    if re.match(r"(?i)^(?:present|current|now)$", raw):
        return date.today()
    # Jan'19 / Jan 2019 / January-19
    m = re.match(rf"(?i)^({_MONTH_NAME})[\s/\-.'’]*(\d{{2,4}})$", raw)
    if m:
        key = m.group(1).lower()
        month = MONTH_MAP.get(key) or MONTH_MAP.get(key[:3])
        year = _normalize_year(int(m.group(2)))
        if month:
            return date(year, month, 1)
    # 01/15/2019 or 15/01/2019 (day/month/year vs month/day/year)
    m_full = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", raw)
    if m_full:
        a, b, year = (
            int(m_full.group(1)),
            int(m_full.group(2)),
            _normalize_year(int(m_full.group(3))),
        )
        if a > 12 and 1 <= b <= 12:
            month = b
        elif b > 12 and 1 <= a <= 12:
            month = a
        elif 1 <= a <= 12:
            # Prefer month-first (US) when ambiguous — matches 01/15/2019.
            month = a
        else:
            return None
        return date(year, month, 1)
    # 01/2019
    m2 = re.match(r"^(\d{1,2})[/\-.](\d{2,4})$", raw)
    if m2:
        month = int(m2.group(1))
        year = _normalize_year(int(m2.group(2)))
        if 1 <= month <= 12:
            return date(year, month, 1)
    m3 = re.match(r"^(\d{4})$", raw)
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


def _extract_phone(text: str) -> str | None:
    """Return the best phone-like match with 10–15 digits (keeps original formatting)."""
    best: str | None = None
    best_len = 0
    for match in PHONE_RE.finditer(text):
        raw = match.group(0).strip(" -.")
        digits = re.sub(r"\D", "", raw)
        if 10 <= len(digits) <= 15 and len(digits) > best_len:
            best = raw
            best_len = len(digits)
    return best


def _heading_tokens(line: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z\s]", "", line).strip().lower()
    return cleaned.split() if cleaned else []


def _heading_key(line: str) -> str | None:
    """Map a line to a section key by identity (aliases), not by position in the file."""
    cleaned = re.sub(r"[^a-zA-Z\s]", "", line).strip().lower()
    if not cleaned or len(cleaned) > 60:
        return None
    words = cleaned.split()
    # Headings are short labels; long sentences are content even if they contain the word.
    if len(words) > 6:
        return None
    for key, aliases in SECTION_ALIASES.items():
        if cleaned in aliases:
            return key
    # "Professional Summary" / "KEY PROJECTS": alias as whole phrase, or token + modifiers only.
    # Never treat job titles like "Project Manager" as a Projects heading.
    for key, aliases in SECTION_ALIASES.items():
        for alias in sorted(aliases, key=len, reverse=True):
            if cleaned == alias:
                return key
            if " " in alias and (cleaned.endswith(" " + alias) or cleaned.startswith(alias + " ")):
                return key
            if " " not in alias and alias in words and len(words) <= 4:
                if all(w == alias or w in _HEADING_MODIFIERS for w in words):
                    return key
    return None


def _looks_like_section_heading(line: str) -> bool:
    """True when a short line is a CV section title, not a person or job title."""
    words = _heading_tokens(line)
    if not words or len(words) > 6:
        return False
    if _heading_key(line):
        return True
    # Unknown short lines that are mostly heading vocabulary.
    heading_hits = sum(1 for w in words if w in _HEADING_NAME_TOKENS)
    return heading_hits >= 1 and heading_hits >= (len(words) + 1) // 2


_HONORIFICS = frozenset({"mr", "mrs", "ms", "miss", "mx", "dr", "prof", "sir", "madam", "shri", "smt"})
_CREDENTIALS = frozenset(
    {
        "phd",
        "ph",
        "mba",
        "mtech",
        "btech",
        "msc",
        "bsc",
        "ba",
        "ma",
        "md",
        "esq",
        "cpa",
        "cfa",
        "pmp",
        "pe",
    }
)
# Split contact header cells: "Jane Doe | email | phone" or multi-column PDF extract.
_NAME_CELL_SPLIT = re.compile(r"\s*[|•·/]\s*|\s+[—–-]\s+|\t+|\s{2,}")


def _contains_place(parts: list[str]) -> bool:
    """True when any word (or the whole phrase) is a known city / state / country."""
    from app.cv_engine.quick_fill.data import get_gazetteer, get_rules, norm_key

    places = get_gazetteer().places
    first_names = get_rules().first_names
    if norm_key(" ".join(parts)) in places:
        return True
    for part in parts:
        word = part.strip(".'’-")
        if not word:
            continue
        if norm_key(word) in places and word.casefold() not in first_names:
            return True
    return False


def _find_location(blob: str) -> str | None:
    """Most specific known place in the contact header, as 'City, State' when both appear.

    Identity comes from the gazetteer (a place is a place by name), not from line order.
    """
    from app.cv_engine.quick_fill.data import get_gazetteer, norm_key

    gaz = get_gazetteer()
    cities: list[Any] = []
    states: list[Any] = []
    countries: list[Any] = []
    for match in gaz.place_re.finditer(blob):
        place = gaz.places.get(norm_key(match.group(0)))
        if place is None or norm_key(match.group(0)) in gaz.weak_aliases:
            continue
        bucket = {"city": cities, "state": states, "country": countries}.get(place.kind)
        if bucket is not None and place not in bucket:
            bucket.append(place)
    if len({c.name for c in cities}) > 1:
        return None  # several cities in the header: ambiguous, leave empty
    if cities:
        city = cities[0]
        state = city.state
        if state and any(s.name == state for s in states):
            return f"{city.name}, {state}"
        return city.name
    if len({s.name for s in states}) == 1:
        return states[0].name
    return None


def _title_case_token(token: str) -> str:
    if not token:
        return token
    if "-" in token:
        return "-".join(_title_case_token(p) for p in token.split("-"))
    if "'" in token or "’" in token:
        sep = "'" if "'" in token else "’"
        return sep.join(_title_case_token(b) for b in token.split(sep))
    if len(token) <= 2 and token.isupper():
        return token.upper()
    return token[:1].upper() + token[1:].lower()


def _title_case_name(parts: list[str]) -> str:
    """Normalise ALL-CAPS / odd casing for form display without inventing a new name."""
    return " ".join(_title_case_token(p) for p in parts)


def _normalize_name_candidate(raw: str) -> str | None:
    """Validate and normalise one name candidate (no contact separators)."""
    line = raw.strip(" .,;:|-")
    if not line or "@" in line or EMAIL_RE.search(line) or _extract_phone(line):
        return None
    if _looks_like_section_heading(line) or _heading_key(line):
        return None
    # "Doe, Jane" / "Jane Doe, PhD" / "Doe, Jane, PhD"
    if "," in line:
        bits = [b.strip() for b in line.split(",") if b.strip()]
        if not bits:
            return None
        trailing = re.sub(r"[^a-zA-Z]", "", bits[-1]).lower()
        if trailing in _CREDENTIALS or bits[-1].lower().rstrip(".") in _CREDENTIALS:
            bits = bits[:-1]
        if not bits:
            return None
        if len(bits) == 1:
            line = bits[0]  # "Jane Doe, PhD" → "Jane Doe"
        elif len(bits) == 2 and " " not in bits[0] and len(bits[1].split()) <= 2:
            line = f"{bits[1]} {bits[0]}"  # "Doe, Jane" → "Jane Doe"
        else:
            # Three+ comma parts are addresses / skill lists, never a person name.
            return None
    parts = [p for p in re.split(r"\s+", line) if p]
    # Drop leading honorifics: "Mr. Jane Doe" → "Jane Doe"
    while parts and re.sub(r"[^a-zA-Z]", "", parts[0]).lower() in _HONORIFICS:
        parts = parts[1:]
    # Drop trailing credentials stuck without comma: "Jane Doe PhD"
    while parts and re.sub(r"[^a-zA-Z]", "", parts[-1]).lower() in _CREDENTIALS:
        parts = parts[:-1]
    if not (1 <= len(parts) <= 4):
        return None
    if not all(re.match(r"^[A-Za-z][A-Za-z'.’-]*$", p) for p in parts):
        return None
    alpha_parts = [re.sub(r"[^a-zA-Z]", "", p).lower() for p in parts]
    if any(p in _HEADING_NAME_TOKENS for p in alpha_parts if p):
        return None
    from app.cv_engine.skills import is_known_skill

    if any(is_known_skill(p) for p in alpha_parts if p):
        return None
    if any(p in _TITLE_NAME_TOKENS for p in alpha_parts if p):
        return None
    # Never accept place text (Punjab, India, Ludhiana) as a person name.
    if _contains_place(parts):
        return None
    return _title_case_name(parts)[:120]


def _clean_name(value: str | None) -> str | None:
    """Return a display-ready person name from a line or contact cell, or None."""
    if not value:
        return None
    line = value.splitlines()[0].strip()
    if not line:
        return None
    # Prefer the first cell that looks like a name on pipe/column contact rows.
    cells = [c.strip() for c in _NAME_CELL_SPLIT.split(line) if c.strip()]
    if not cells:
        cells = [line]
    for cell in cells:
        cleaned = _normalize_name_candidate(cell)
        if cleaned and len(cleaned.split()) >= 1:
            return cleaned
    return None


def _best_name_from_text(blob: str) -> str | None:
    """First reliable multi-token name in a contact/preamble blob."""
    best: str | None = None
    for line in blob.splitlines():
        cleaned = _clean_name(line)
        if cleaned and len(cleaned.split()) >= 2:
            return cleaned
        if cleaned and best is None:
            best = cleaned
    return best


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
    """Prefer multi-token PERSON entities so 'Jane Unusual' is not truncated to 'Jane'."""
    doc = nlp(text[:2000])
    best: str | None = None
    best_tokens = 0
    for ent in doc.ents:
        if ent.label_ != "PERSON":
            continue
        parts = [p for p in ent.text.split() if p]
        if not (1 <= len(parts) <= 4):
            continue
        name = str(ent.text).strip()
        if not name:
            continue
        if len(parts) > best_tokens:
            best = name
            best_tokens = len(parts)
            if best_tokens >= 2:
                break
    return best


def _orgs_and_locations(nlp: Any, text: str) -> tuple[list[str], list[str]]:
    doc = nlp(text[:8000])
    orgs = [e.text.strip() for e in doc.ents if e.label_ == "ORG"]
    locs = [e.text.strip() for e in doc.ents if e.label_ in {"GPE", "LOC"}]
    return orgs, locs


def _contact_blob(text: str, sections: dict[str, str]) -> str:
    """Text most likely to hold identity/contact facts (not projects or job bullets)."""
    preamble = (sections.get("_preamble") or "").strip()
    if preamble:
        return preamble
    # When a heading opens the CV, the name/contact lines often sit under summary.
    summary = (sections.get("summary") or "").strip()
    if summary:
        # Keep only leading contact-like lines; skip long prose paragraphs.
        lines: list[str] = []
        for line in summary.splitlines():
            stripped = line.strip()
            if not stripped:
                if lines:
                    break
                continue
            if len(stripped.split()) > 12 and not EMAIL_RE.search(stripped):
                # Prose summary sentence — stop before treating it as identity.
                if lines:
                    break
                continue
            lines.append(stripped)
            if len(lines) >= 8:
                break
        if lines:
            return "\n".join(lines)
    # Lines before the first recognised section heading only (never Experience/Projects).
    before: list[str] = []
    for line in text.splitlines():
        if _heading_key(line.strip()):
            break
        before.append(line)
    return "\n".join(before).strip()


def _pick_location(
    nlp: Any | None, text: str, sections: dict[str, str]
) -> tuple[str | None, float]:
    """Prefer places near the contact header; never take the first GPE from Projects."""
    # Contact header only (never Experience / Projects); gazetteer decides what is a place.
    contact = _contact_blob(text, sections)
    found = _find_location(contact) if contact.strip() else None
    if found:
        return found, 0.85
    # Labelled location line near the top of the document.
    for line in text.splitlines()[:20]:
        low = line.strip().lower()
        if low.startswith(("location", "based in", "city", "address", "residing")):
            labelled = _find_location(line)
            if labelled:
                return labelled, 0.8
    # Uncertain or only in body sections: leave unmapped.
    return None, 0.0


def _is_plausible_job_entry(entry: ExperienceEntry) -> bool:
    """Reject section headings / project blocks that leaked into Experience."""
    title = (entry.title or "").strip()
    if not title:
        return False
    if _looks_like_section_heading(title) or _heading_key(title):
        return False
    company = (entry.company or "").strip()
    if company and (_looks_like_section_heading(company) or _heading_key(company)):
        return False
    return True


def _name_near_email(text: str, email: str | None) -> str | None:
    """Prefer a multi-token name sitting just above / beside the email (contact identity)."""
    if not email:
        return None
    idx = text.find(email)
    if idx < 0:
        return None
    window = text[max(0, idx - 240) : idx]
    # Same-line contact: "Jane Doe | jane@x.com" → cell before the address.
    same_line = window.splitlines()[-1] if window else ""
    for cell in reversed([c.strip() for c in _NAME_CELL_SPLIT.split(same_line) if c.strip()]):
        cleaned = _normalize_name_candidate(cell)
        if cleaned and len(cleaned.split()) >= 2:
            return cleaned
    for line in reversed(window.splitlines()):
        cleaned = _clean_name(line)
        if cleaned and len(cleaned.split()) >= 2:
            return cleaned
    return None


def _parse_experience_block(block: str, orgs: list[str]) -> list[ExperienceEntry]:
    entries: list[ExperienceEntry] = []
    if not block:
        return entries
    chunks = re.split(r"\n{2,}", block)
    for chunk in chunks:
        lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
        if not lines:
            continue
        # Drop a leading section heading that was not segmented out.
        if _heading_key(lines[0]) or _looks_like_section_heading(lines[0]):
            lines = lines[1:]
            if not lines:
                continue
            chunk = "\n".join(lines)
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
        if company is None and len(lines) > 1 and not _looks_like_section_heading(lines[1]):
            company = lines[1][:120]
        entry = ExperienceEntry(
            title=title,
            company=company,
            start_date=start,
            end_date=end,
            description=chunk[:1000],
        )
        if _is_plausible_job_entry(entry):
            entries.append(entry)
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


def _parse_projects_block(block: str) -> list[ProjectEntry]:
    """Projects keep their own section: never merged into Experience or contact fields."""
    entries: list[ProjectEntry] = []
    for chunk in re.split(r"\n{2,}", block or ""):
        lines = [ln.strip(" -•\t") for ln in chunk.splitlines() if ln.strip(" -•\t")]
        if not lines:
            continue
        entries.append(
            ProjectEntry(
                name=lines[0][:200],
                description="\n".join(lines[1:])[:1000] or None,
            )
        )
    return entries[:20]


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
    def parse(  # noqa: C901, PLR0912
        self, text: str, *, file_meta: ExtractResult | None = None
    ) -> ParsedCV:
        sections = segment_sections(text)
        email_m = EMAIL_RE.search(text)
        email = email_m.group(0) if email_m else None
        phone = _extract_phone(text)
        links = list(dict.fromkeys(URL_RE.findall(text)))[:20]

        nlp = _load_nlp()
        full_name = None
        name_confidence = 0.0
        orgs: list[str] = []
        contact = _contact_blob(text, sections)
        if nlp is not None:
            full_name = _clean_name(_first_person_name(nlp, contact))
            if full_name:
                name_confidence = 0.85 if len(full_name.split()) >= 2 else 0.55
            orgs, _ = _orgs_and_locations(nlp, text)

        location, location_confidence = _pick_location(nlp, text, sections)

        skills_text = sections.get("skills", "") or text
        skills = find_skills_in_text(skills_text)
        if len(skills) < 3:
            skills = list(dict.fromkeys(skills + find_skills_in_text(text)))

        experience = _parse_experience_block(sections.get("experience", ""), orgs)
        education = _parse_education_block(sections.get("education", ""))
        certifications = _parse_certs(sections.get("certifications", ""))
        projects = _parse_projects_block(sections.get("projects", ""))

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
        mention_blob = "\n".join(
            filter(None, [sections.get("summary"), sections.get("_preamble"), text[:800]])
        )
        mention = YEARS_MENTION_RE.search(mention_blob)
        if mention:
            mentioned = float(mention.group(1))
            # Prefer the larger of timeline merge vs explicit "N years" claim.
            years = mentioned if years is None else max(years, mentioned)

        # Identity: prefer name next to email, then contact-block lines, never headings.
        near_email = _name_near_email(text, email)
        contact_name = _best_name_from_text(contact)
        if near_email:
            full_name = near_email
            name_confidence = 0.9
        elif contact_name and len(contact_name.split()) >= 2:
            if not full_name or len(full_name.split()) < 2:
                full_name = contact_name
                name_confidence = max(name_confidence, 0.85)
            elif full_name and len(full_name.split()) < 2:
                full_name = contact_name
                name_confidence = max(name_confidence, 0.85)
        # No whole-document name scan: job titles / skill rows must not become the name.
        # If the contact block has no reliable name, leave it unmapped for manual review.

        # Re-normalise NER hits (honorifics, ALL CAPS, "Last, First").
        if full_name:
            normalised = _clean_name(full_name)
            if not normalised:
                full_name = None
                name_confidence = 0.0
            else:
                full_name = normalised
                if len(full_name.split()) >= 2:
                    name_confidence = max(name_confidence, 0.75)

        current = experience[0] if experience else None
        title_confidence = 0.0
        company_confidence = 0.0
        if current and _is_plausible_job_entry(current):
            if current.start_date or current.end_date:
                title_confidence = 0.8 if current.title else 0.0
                company_confidence = 0.75 if current.company else 0.0
            else:
                title_confidence = 0.55 if current.title else 0.0
                company_confidence = 0.5 if current.company else 0.0

        found_sections = [k for k in SECTION_ALIASES if sections.get(k)]
        confidence: dict[str, float] = {
            "email": 0.95 if email else 0.0,
            "phone": 0.85 if phone else 0.0,
            "name": name_confidence if full_name else 0.0,
            "location": location_confidence if location else 0.0,
            "title": title_confidence,
            "company": company_confidence,
            # Lexicon-matched skill tokens are identified by name, not position.
            "skills": 0.75 if skills else 0.0,
            "experience": min(1.0, len(experience) / 3) if experience else 0.0,
        }

        return ParsedCV(
            full_name=full_name,
            email=email,
            phone=phone,
            location=location,
            links=links,
            summary=(sections.get("summary") or "")[:1500] or None,
            skills=skills,
            experience=experience,
            education=education,
            certifications=certifications,
            projects=projects,
            total_experience_years=years,
            sections_found=found_sections,
            confidence=confidence,
            parser_version=PARSER_VERSION,
            ocr_used=bool(file_meta and file_meta.ocr_used),
        )
