"""Skills, tags, source and the department / job hints."""

from __future__ import annotations

import re
from typing import Literal

from app.cv_engine.quick_fill.common import ambiguous, found, smart_title, tidy_words
from app.cv_engine.quick_fill.data import get_rules, norm_key
from app.cv_engine.quick_fill.text import Doc
from app.cv_engine.quick_fill.types import Alternative, FieldResult, Json
from app.cv_engine.skills import canonicalize, find_skills_in_text, get_taxonomy

MAX_ITEMS = 30
_ITEM_SPLIT = re.compile(r"\s*(?:[,;/|]|\band\b|&)\s*", re.IGNORECASE)
_SKILL_ITEM = re.compile(r"^[A-Za-z][A-Za-z0-9 .+#&'-]{0,38}$")
_TAG_ITEM = re.compile(r"^[^\W_][\w .+#&'-]{0,38}$")

# --- Skills -----------------------------------------------------------------------------------


def _list_items(value: str) -> list[str]:
    return [i.strip(" .-") for i in _ITEM_SPLIT.split(value) if i.strip(" .-")]


def extract_skills(doc: Doc) -> list[FieldResult]:
    ordered: dict[str, Literal["keyed", "item", "text"]] = {}
    unknown: set[str] = set()
    rules = get_rules()
    for chunk in doc.chunks:
        if chunk.key == "skills":
            for item in _list_items(chunk.value):
                known = get_taxonomy().lookup(item)
                if known is not None:
                    ordered.setdefault(known.name, "keyed")
                elif _SKILL_ITEM.match(item) and item.casefold() not in rules.non_name_words:
                    name = canonicalize(item)
                    ordered.setdefault(name, "keyed")
                    unknown.add(name)
            doc.claim(chunk.start, chunk.end)
            continue
        if chunk.key is not None:
            continue
        free = doc.free_text(chunk)
        body = free.strip(" .")
        if not body:
            continue
        known = get_taxonomy().lookup(body) if len(body) <= 30 else None
        if known is not None and not any(doc.claimed[chunk.start : chunk.end]):
            ordered.setdefault(known.name, "item")
            doc.claim(chunk.start, chunk.end)
            continue
        for name in find_skills_in_text(free):
            ordered.setdefault(name, "text")
    if not ordered:
        return []
    names = list(ordered)[:MAX_ITEMS]
    kinds = {ordered[n] for n in names}
    confidence: Literal["high", "medium", "low"] = (
        "medium" if "text" in kinds or unknown else "high"
    )
    parts: list[str] = []
    if "keyed" in kinds:
        parts.append("Listed under Skills / Tech stack.")
    if "item" in kinds:
        parts.append("Standalone items that are known skills.")
    if "text" in kinds:
        parts.append("Skills mentioned inside other text (for example a job title).")
    if unknown:
        parts.append(f"Not in the skills list: {', '.join(sorted(unknown))}.")
    warning = (
        f"More than {MAX_ITEMS} skills: only the first {MAX_ITEMS} are listed."
        if len(ordered) > MAX_ITEMS
        else None
    )
    return [
        found(
            "skills",
            list[Json](names),
            ", ".join(names),
            confidence,
            " ".join(parts),
            warning=warning,
        )
    ]


# --- Tags -------------------------------------------------------------------------------------

_HASHTAG = re.compile(r"(?<![\w&])#([A-Za-z][\w-]{1,30})")


def extract_tags(doc: Doc) -> list[FieldResult]:
    tags: dict[str, None] = {}
    for chunk in doc.chunks:
        if chunk.key == "tags":
            for item in _list_items(chunk.value):
                if _TAG_ITEM.match(item):
                    tags.setdefault(tidy_words(item).lower(), None)
            doc.claim(chunk.start, chunk.end)
    for m in _HASHTAG.finditer(doc.masked()):
        tags.setdefault(m.group(1).lower().replace("-", " "), None)
        doc.claim(m.start(), m.end())
    if not tags:
        return []
    names = list(tags)[:12]
    return [
        found(
            "tags",
            list[Json](names),
            ", ".join(names),
            "high",
            "Listed under Tags or written as #hashtags.",
        )
    ]


# --- Source -----------------------------------------------------------------------------------

_SOURCE_CUE = re.compile(
    r"(?:\bvia\b|\bthrough\b|\bsourced\s+(?:from|via|through)\b|\bfound\s+(?:on|via|through)\b|"
    r"\bapplied\s+(?:via|through|on)\b|\bsource\b|\bfrom\b)\s*[:=]?\s*(?:the\s+|our\s+)?$",
    re.IGNORECASE,
)
_REFERRAL_WORDS = re.compile(r"\b(?:referral|referred|walk-?\s?in)\b", re.IGNORECASE)


def _source_for(value: str) -> str | None:
    low = norm_key(value)
    for source, words in get_rules().sources.items():
        if any(low == w or low.startswith(w) or w in low.split() for w in words):
            return source
    return None


_SOURCE_LABEL = {
    "career_site": "Career site",
    "referral": "Referral",
    "linkedin": "LinkedIn",
    "agency": "Agency",
    "manual": "Manual",
}


def extract_source(doc: Doc) -> list[FieldResult]:
    for chunk in doc.chunks:
        if chunk.key == "source":
            doc.claim(chunk.start, chunk.end)
            source = _source_for(chunk.value)
            if source is None:
                return [
                    FieldResult(
                        field="source",
                        value=None,
                        confidence="low",
                        reason=f"'{chunk.value}' is not one of the portal sources.",
                        candidates=[
                            Alternative(k, v, "Portal source") for k, v in _SOURCE_LABEL.items()
                        ],
                        warning="Source not recognised: pick one by hand.",
                    )
                ]
            return [found("source", source, _SOURCE_LABEL[source], "high", "Labelled as source.")]
    found_sources: dict[str, tuple[int, int, bool]] = {}
    masked = doc.masked()
    for source, words in get_rules().sources.items():
        pattern = re.compile(
            r"(?<![\w])(?:"
            + "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in words)
            + r")(?![\w])",
            re.IGNORECASE,
        )
        for m in pattern.finditer(masked):
            owner = doc.chunk_at(m.start())
            if owner is not None and owner.key not in (None, "source"):
                continue
            cued = bool(_SOURCE_CUE.search(masked[max(0, m.start() - 25) : m.start()]))
            strong_word = source in ("referral", "manual") and bool(
                _REFERRAL_WORDS.fullmatch(m.group(0))
            )
            if cued or strong_word:
                found_sources.setdefault(source, (m.start(), m.end(), cued))
    if not found_sources:
        return []
    if len(found_sources) > 1:
        options = [Alternative(k, _SOURCE_LABEL[k], "Mentioned in the text") for k in found_sources]
        return [ambiguous("source", options, "More than one possible source: choose one.")]
    ((source, (start, end, cued)),) = found_sources.items()
    doc.claim(start, end)
    return [
        found(
            "source",
            source,
            _SOURCE_LABEL[source],
            "medium",
            "Written after 'via' / 'from' / 'through'."
            if cued
            else "The word matches this source.",
        )
    ]


# --- Department and job hints -----------------------------------------------------------------


def _dept_pattern() -> re.Pattern[str]:
    depts = sorted(get_rules().departments, key=len, reverse=True)
    alt = "|".join(re.escape(d).replace(r"\ ", r"\s+") for d in depts)
    return re.compile(
        rf"(?<![\w])(?:(?:in|for|from|under)\s+(?:the\s+)?)?(?P<d>{alt})\s+(?:department|dept\.?|team|function)(?![\w])",
        re.IGNORECASE,
    )


def extract_department(doc: Doc) -> list[FieldResult]:
    for chunk in doc.chunks:
        if chunk.key == "department" and chunk.value:
            doc.claim(chunk.start, chunk.end)
            return [
                found(
                    "department_hint",
                    smart_title(chunk.value),
                    smart_title(chunk.value),
                    "high",
                    "Labelled as department.",
                )
            ]
    m = _dept_pattern().search(doc.masked())
    if m is None:
        return []
    doc.claim(m.start(), m.end())
    value = smart_title(m.group("d"))
    return [
        found("department_hint", value, value, "medium", "Written as '<name> department / team'.")
    ]


_JOB_PHRASE = re.compile(
    r"(?<![\w])(?:applied\s+for|applying\s+for|applying\s+to|interested\s+in|for\s+the)\s+"
    r"(?:the\s+)?(?P<j>[A-Za-z][\w.+#&/' -]{2,60}?)\s*"
    r"(?:(?:role|position|opening|job|post|vacancy|profile)\b|(?=[,;]|$))",
    re.IGNORECASE | re.MULTILINE,
)


# "applied for Java Developer in Engineering": the job ends before "in / at / with ..."
_JOB_TAIL = re.compile(r"\s+(?:in|at|with|from|since|under|through|via)\s+", re.IGNORECASE)
# "the post of Accountant": the noun in front is not part of the title
_JOB_NOUN_LEAD = re.compile(
    r"^(?:the\s+)?(?:post|position|role|job|opening|vacancy)\s+(?:of|for|as)\s+(?:an?\s+|the\s+)?",
    re.IGNORECASE,
)


def extract_job(doc: Doc) -> list[FieldResult]:
    for chunk in doc.chunks:
        if chunk.key == "job" and chunk.value:
            doc.claim(chunk.start, chunk.end)
            value = smart_title(chunk.value)
            return [found("job_hint", value, value, "high", "Labelled as the job applied for.")]
    masked = doc.masked()
    for m in _JOB_PHRASE.finditer(masked):
        raw = _JOB_TAIL.split(m.group("j").strip(), maxsplit=1)[0].strip()
        raw = _JOB_NOUN_LEAD.sub("", raw).strip()
        if not raw:
            continue
        if len(raw.split()) > 7 or re.search(r"\d|@", raw):
            continue
        if raw.casefold().split()[0] in ("a", "an", "my", "our", "your", "it", "this", "that"):
            continue
        is_for_the = m.group(0).casefold().lstrip().startswith("for the")
        if is_for_the and not re.search(
            r"(?:role|position|opening|job|post|vacancy)\s*$", m.group(0), re.IGNORECASE
        ):
            continue
        doc.claim(m.start(), m.end())
        value = smart_title(raw)
        return [
            found(
                "job_hint", value, value, "medium", "Written after 'applied for' / 'applying for'."
            )
        ]
    return []
