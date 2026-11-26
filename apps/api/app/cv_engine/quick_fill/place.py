"""Current location, current company and current job title."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.cv_engine.quick_fill.common import ambiguous, found, smart_title, tidy_words
from app.cv_engine.quick_fill.data import Place, get_gazetteer, get_rules, norm_key
from app.cv_engine.quick_fill.text import Chunk, Doc
from app.cv_engine.quick_fill.types import Alternative, FieldResult
from app.cv_engine.skills import is_known_skill

_NON_PLACE_KEYS = frozenset(
    {
        "ignore",
        "alt_phone",
        "phone",
        "email",
        "linkedin",
        "portfolio",
        "skills",
        "tags",
        "source",
        "department",
        "name",
        "first_name",
        "last_name",
        "experience",
        "notice",
        "current_ctc",
        "expected_ctc",
        "offered_ctc",
        "negotiable",
        "title",
        "job",
        "company",
    }
)

# --- Location ---------------------------------------------------------------------------------

_STRONG_PREP = re.compile(
    r"(?:(?<![\w])from|based\s+(?:in|at|out\s+of)|located\s+(?:in|at)|residing\s+(?:in|at)|"
    r"lives?\s+in|living\s+in|resides?\s+in|staying\s+in|stays\s+in|currently\s+(?:in|at)|"
    r"presently\s+(?:in|at)|location\s+(?:is|:)|currently\s+located\s+(?:in|at))\s+$",
    re.IGNORECASE,
)
_WEAK_PREP = re.compile(r"(?<![\w])(?:in|at|near)\s+$", re.IGNORECASE)
_OTHER_PLACE = re.compile(
    r"(?:relocat\w*|prefer\w*|native|hometown|home\s+town|moving|move|shift(?:ing)?|transfer\w*|"
    r"open\s+to|willing\s+to|ready\s+to|interested\s+in|travel\w*)(?:\s+\w+){0,3}\s*(?:to|in|at|for)?\s*$",
    re.IGNORECASE,
)


@dataclass(slots=True)
class _PlaceHit:
    place: Place
    typed: str
    start: int
    end: int
    chunk: Chunk
    tier: Literal["key", "strong", "weak_prep", "standalone", "other", "loose"]
    is_weak_alias: bool
    state_text: str | None = None  # state/country written right after a city


def _place_hits(doc: Doc) -> list[_PlaceHit]:
    gazetteer = get_gazetteer()
    hits: list[_PlaceHit] = []
    for chunk in doc.chunks:
        if chunk.key in _NON_PLACE_KEYS:
            continue
        free = doc.free_text(chunk)
        body = free.strip()
        for m in gazetteer.place_re.finditer(free):
            typed = m.group(0)
            place = gazetteer.places[norm_key(typed)]
            before = free[: m.start()]
            tier: Literal["key", "strong", "weak_prep", "standalone", "other", "loose"]
            if chunk.key == "location":
                tier = "key"
            elif _OTHER_PLACE.search(before):
                tier = "other"
            elif _STRONG_PREP.search(before):
                tier = "strong"
            elif _WEAK_PREP.search(before):
                tier = "weak_prep"
            elif len(body) > 0 and len(typed) >= len(body.strip(" .,")) - 1:
                tier = "standalone"
            else:
                tier = "loose"
            hits.append(
                _PlaceHit(
                    place,
                    typed,
                    chunk.start + m.start(),
                    chunk.start + m.end(),
                    chunk,
                    tier,
                    norm_key(typed) in gazetteer.weak_aliases,
                )
            )
    return _merge_state(doc, hits)


def _merge_state(doc: Doc, hits: list[_PlaceHit]) -> list[_PlaceHit]:
    """ "Pune, Maharashtra, India" / "Dubai, UAE": the following states or country complete a city."""
    out: list[_PlaceHit] = []
    skip: set[int] = set()
    for i, hit in enumerate(hits):
        if i in skip:
            continue
        if hit.place.kind == "city":
            j = i + 1
            last_chunk = hit.chunk
            while j < len(hits):
                nxt = hits[j]
                gap = doc.text[hit.end : nxt.start]
                adjacent = re.fullmatch(r"[\s,]{0,3}", gap) is not None and (
                    nxt.chunk is last_chunk or nxt.chunk.index <= last_chunk.index + 1
                )
                if not adjacent or nxt.place.kind not in ("state", "country"):
                    break
                belongs = nxt.place.name in (hit.place.state, hit.place.country) or (
                    nxt.place.kind == "country"
                    and nxt.place.name == "India"
                    and not hit.place.international
                )
                if not belongs:
                    break
                if nxt.place.kind == "state":
                    hit.state_text = nxt.place.name
                hit.end = nxt.end
                last_chunk = nxt.chunk
                skip.add(j)
                doc.claim(nxt.start, nxt.end)
                if nxt.tier == "standalone" and hit.tier == "loose":
                    hit.tier = "standalone"
                j += 1
        out.append(hit)
    return out


def _place_value(hit: _PlaceHit) -> str:
    return f"{hit.place.name}, {hit.state_text}" if hit.state_text else hit.place.name


def extract_location(doc: Doc) -> list[FieldResult]:
    hits = _place_hits(doc)
    if not hits:
        return []
    for hit in hits:
        if hit.tier in ("key", "strong", "weak_prep", "standalone", "other"):
            doc.claim(hit.start, hit.end)
    tiers: list[tuple[tuple[str, ...], str]] = [
        (("key", "strong"), "high"),
        (("weak_prep",), "medium"),
        (("standalone",), "high"),
    ]
    for tier_names, base in tiers:
        pool = [h for h in hits if h.tier in tier_names]
        if tier_names == ("standalone",):
            pool = [h for h in pool if not h.is_weak_alias or h.state_text]
        if not pool:
            continue
        return [_location_result(pool, tier_names, base)]
    return []


def _location_result(pool: list[_PlaceHit], tier_names: tuple[str, ...], base: str) -> FieldResult:
    distinct: dict[str, _PlaceHit] = {}
    for hit in pool:
        distinct.setdefault(_place_value(hit), hit)
    if len(distinct) > 1:
        keyed = [h for h in pool if h.tier == "key"]
        if len({_place_value(h) for h in keyed}) == 1:
            chosen = keyed[0]
            result = _one_location(chosen, "high")
            result.warning = f"{len(distinct)} places found; the labelled one was used."
            return result
        options = [Alternative(v, v, "A place in the text") for v in distinct]
        return ambiguous(
            "current_location",
            options,
            f"{len(distinct)} places found: which is the current location?",
        )
    (chosen,) = distinct.values()
    confidence = "high" if base == "high" else "medium"
    if chosen.place.kind != "city":
        confidence = "medium"  # a state or country alone is a vague location
    if chosen.is_weak_alias:
        confidence = "medium"
    return _one_location(chosen, confidence)


def _one_location(hit: _PlaceHit, confidence: str) -> FieldResult:
    value = _place_value(hit)
    reasons: list[str] = []
    if hit.tier == "key":
        reasons.append("Labelled as location.")
    elif hit.tier == "strong":
        reasons.append("Written after 'from' / 'based in'.")
    elif hit.tier == "weak_prep":
        reasons.append("Written after 'in' / 'at'.")
    else:
        reasons.append("A known place name.")
    if hit.typed.casefold() != hit.place.name.casefold():
        reasons.append(f"'{hit.typed}' is stored as {hit.place.name}.")
    if hit.place.kind == "state":
        reasons.append("Only a state was given.")
    if hit.place.kind == "country":
        reasons.append("Only a country was given.")
    conf: Literal["high", "medium", "low"] = (
        "high" if confidence == "high" else "medium" if confidence == "medium" else "low"
    )
    return found("current_location", value, value, conf, " ".join(reasons))


# --- Company ----------------------------------------------------------------------------------

_COMPANY_KEYS = frozenset({None, "company", "title"})
_PREV_COMPANY = re.compile(
    r"(?:(?<![\w])ex[-\s]?|(?<![\w])formerly(?:\s+(?:at|with|from))?\s+|"
    r"(?<![\w])previously(?:\s+(?:at|with|from|worked\s+(?:at|with|for)))?\s+|"
    r"(?<![\w])earlier(?:\s+(?:at|with))?\s+|(?<![\w])worked\s+(?:at|with|for)\s+|"
    r"(?<![\w])left\s+|(?<![\w])resigned\s+from\s+|(?<![\w])moved\s+from\s+)$",
    re.IGNORECASE,
)
_COMPANY_PREP = re.compile(
    r"(?:(?<![\w])(?:currently\s+)?(?:working|works|employed|placed|serving)\s+(?:at|with|for|in|by)|"
    r"(?<![\w])(?:at|with|@))\s+(?=[A-Za-z])",
    re.IGNORECASE,
)
_COMPANY_TAIL_STOP = re.compile(
    r"\s+(?:as|since|from|for|with|in|on|ctc|and|having|where|who|currently|at|\(|-)(?:\s|$)",
    re.IGNORECASE,
)
_TITLE_HEAD_AFTER = re.compile(
    r"^\s+(?:developer|engineer|consultant|architect|analyst|admin|cloud|dba|consulting|db)\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class _CompanyHit:
    name: str
    start: int
    end: int
    tier: Literal["key", "prep", "known", "suffix"]
    previous: bool
    known: bool


def _canonical_company(raw: str) -> tuple[str, bool]:
    company = get_rules().company_by_alias.get(norm_key(raw))
    if company is not None:
        return company.name, True
    text = tidy_words(raw)
    return (text if any(c.isupper() for c in text) else smart_title(text)), False


_AS_TITLE = re.compile(r"\s+as\s+(?:an?\s+|the\s+)?", re.IGNORECASE)


def _company_hits(doc: Doc) -> list[_CompanyHit]:
    rules = get_rules()
    hits: list[_CompanyHit] = []
    for chunk in doc.chunks:
        if chunk.key not in _COMPANY_KEYS:
            continue
        free = doc.free_text(chunk)
        body = free.strip()
        if chunk.key == "company":
            value = free[chunk.value_start - chunk.start :].strip()
            value = _AS_TITLE.split(value, maxsplit=1)[0].strip()  # "Cognizant as Senior Associate"
            if value and not re.search(r"\d{3}|@", value):
                name, known = _canonical_company(value)
                offset = free.find(value)
                hits.append(
                    _CompanyHit(
                        name,
                        chunk.start + offset,
                        chunk.start + offset + len(value),
                        "key",
                        False,
                        known,
                    )
                )
            continue
        taken: list[tuple[int, int]] = []
        for m in _COMPANY_PREP.finditer(free):
            rest = free[m.end() :]
            tail = _COMPANY_TAIL_STOP.search(rest)
            raw = rest[: tail.start()] if tail else rest
            raw = re.split(r"[,;|]", raw)[0].strip(" .")
            words = raw.split()
            if not raw or len(words) > 6 or re.search(r"\d|@", raw):
                continue
            if get_gazetteer().places.get(norm_key(raw)) is not None:
                continue  # "at Pune" is a place
            if raw.casefold() in rules.non_name_words or (
                is_known_skill(raw) and not _is_known_company(raw)
            ):
                continue
            if not (_is_known_company(raw) or _looks_like_company(words)):
                continue
            before = free[: m.start()]
            previous = bool(_PREV_COMPANY.search(before)) or bool(
                re.search(r"(?<![\w])(?:was|were|had\s+worked)\s+$", before, re.IGNORECASE)
            )
            name, known = _canonical_company(raw)
            start = chunk.start + m.end()
            hits.append(_CompanyHit(name, start, start + len(raw), "prep", previous, known))
            taken.append((m.end(), m.end() + len(raw)))
        for m in rules.company_re.finditer(free):
            if any(a <= m.start() < b for a, b in taken):
                continue
            after = free[m.end() :]
            if _TITLE_HEAD_AFTER.match(after):
                continue  # "Oracle DBA", "SAP consultant": a skill, not an employer
            previous = bool(_PREV_COMPANY.search(free[: m.start()]))
            standalone = len(m.group(0)) >= len(body.strip(" .")) - 1 or _only_suffixes_follow(
                free[m.end() :]
            )
            if not standalone and not previous:
                continue  # inside a longer sentence only "at/with X" is trusted (handled above)
            name, known = _canonical_company(m.group(0))
            hits.append(
                _CompanyHit(
                    name, chunk.start + m.start(), chunk.start + m.end(), "known", previous, True
                )
            )
        if chunk.key is None and not taken and not rules.company_re.search(free):
            words = body.strip(" .").split()
            if (
                2 <= len(words) <= 6
                and words[-1].casefold().strip(".") in rules.company_suffixes
                and not re.search(r"\d|@", body)
                and all(
                    w[:1].isupper() or w.casefold().strip(".") in rules.company_suffixes
                    for w in words
                )
            ):
                name, known = _canonical_company(body.strip(" ."))
                offset = free.find(body)
                hits.append(
                    _CompanyHit(
                        name,
                        chunk.start + offset,
                        chunk.start + offset + len(body.strip(" .")),
                        "suffix",
                        False,
                        False,
                    )
                )
    return hits


def _only_suffixes_follow(rest: str) -> bool:
    """ "Infosys Pvt. Ltd.": after the known name only company words (Pvt, Ltd, Inc ...) remain."""
    suffixes = get_rules().company_suffixes
    words = rest.replace(".", " ").split()
    return bool(words) and all(w.casefold() in suffixes for w in words)


def _is_known_company(raw: str) -> bool:
    return norm_key(raw) in get_rules().company_by_alias


def _looks_like_company(words: list[str]) -> bool:
    """Capitalised words, or ending in a company suffix ("Acme Pvt Ltd")."""
    suffixes = get_rules().company_suffixes
    if words[-1].casefold().strip(".") in suffixes:
        return True
    return all(w[:1].isupper() or w[:1] == "&" for w in words) and not any(
        w.casefold() in get_rules().non_name_words for w in words
    )


def extract_company(doc: Doc) -> list[FieldResult]:
    hits = _company_hits(doc)
    if not hits:
        return []
    for hit in hits:
        doc.claim(hit.start, hit.end)
    current = [h for h in hits if not h.previous]
    previous = [h for h in hits if h.previous]
    if not current:
        first = previous[0]
        return [
            found(
                "current_company",
                first.name,
                first.name,
                "low",
                "Written as a past employer (ex- / formerly / previously).",
                warning="This looks like a previous employer, not the current one: check before using it.",
            )
        ]
    distinct: dict[str, _CompanyHit] = {}
    for hit in current:
        distinct.setdefault(hit.name.casefold(), hit)
    if len(distinct) > 1:
        keyed = [h for h in current if h.tier == "key"]
        if len({h.name.casefold() for h in keyed}) == 1:
            return [
                _company_result(
                    keyed[0], note=f"{len(distinct)} companies found; the labelled one was used."
                )
            ]
        options = [Alternative(h.name, h.name, "A company in the text") for h in distinct.values()]
        return [
            ambiguous(
                "current_company",
                options,
                f"{len(distinct)} companies found: which is the current employer?",
            )
        ]
    (hit,) = distinct.values()
    return [_company_result(hit, note=None, has_previous=bool(previous))]


def _company_result(
    hit: _CompanyHit, *, note: str | None, has_previous: bool = False
) -> FieldResult:
    reasons: list[str] = []
    confidence: Literal["high", "medium", "low"]
    if hit.tier == "key":
        confidence = "high"
        reasons.append("Labelled as company.")
    elif hit.tier == "prep":
        confidence = "high" if hit.known else "medium"
        reasons.append("Written after 'at' / 'working with'.")
    elif hit.tier == "known":
        confidence = "high"
        reasons.append("A well-known employer name.")
    else:
        confidence = "medium"
        reasons.append("Ends with a company word such as Ltd or Technologies.")
    if hit.known:
        reasons.append("Matched the known company list.")
    if has_previous:
        reasons.append("A past employer in the text was left out.")
    return found("current_company", hit.name, hit.name, confidence, " ".join(reasons), warning=note)


# --- Job title --------------------------------------------------------------------------------

_TITLE_KEYS = frozenset({None, "title", "company"})
_TITLE_LEAD = re.compile(
    r"^(?:(?:currently\s+)?working\s+as\s+(?:an?\s+|the\s+)?|(?:he|she|they)\s+is\s+(?:an?\s+)?|"
    r"is\s+(?:an?\s+)?|as\s+(?:an?\s+|the\s+)?|designation\s*[:=-]?\s*|role\s*[:=-]?\s*)",
    re.IGNORECASE,
)
_LEVEL = re.compile(r"^(?:i{1,3}|iv|v|[1-5]|l[1-6]|sde[1-3]?)$", re.IGNORECASE)
_TITLE_WORD = re.compile(r"^[A-Za-z][A-Za-z.+#&/'-]*$")
_TITLE_TAIL_PREP = re.compile(r"\s+(?:at|with|@|in|for|from)\s*$", re.IGNORECASE)


@dataclass(slots=True)
class _TitleHit:
    text: str
    start: int
    end: int
    tier: Literal["key", "lead", "shape"]
    all_known: bool


def _is_head(word: str) -> bool:
    return word.casefold().strip(".") in get_rules().title_heads


def _is_known_title_word(word: str) -> bool:
    rules = get_rules()
    low = word.casefold().strip(".")
    return (
        low in rules.title_heads
        or low in rules.title_modifiers
        or low in rules.title_acronyms
        or bool(_LEVEL.match(low))
        or is_known_skill(word)
    )


def _title_core(text: str) -> tuple[str, bool] | None:
    """Clean title text and whether every word is a known title word, or None if it is no title."""
    words = text.split()
    if not 1 <= len(words) <= 7:
        return None
    if any(not _TITLE_WORD.match(w) for w in words):
        return None
    core = [w for w in words if not _LEVEL.match(w)] or words
    head_ok = _is_head(core[-1]) or (
        len(core) >= 3
        and core[0].casefold() in ("head", "vp", "director")
        and core[1].casefold() == "of"
    )
    if not head_ok:
        return None
    covered = _multiword_modifier_words(text)

    def known(word: str) -> bool:
        low = word.casefold().strip(".")
        return low in covered or low in ("of", "and") or _is_known_title_word(word)

    if any(w.casefold() in get_rules().non_name_words and not known(w) for w in words):
        return None
    return smart_title(text), all(known(w) for w in words)


def _multiword_modifier_words(text: str) -> frozenset[str]:
    """Words that belong to a known multi-word modifier ("full stack", "machine learning")."""
    low = " ".join(text.casefold().split())
    words: set[str] = set()
    for modifier in get_rules().title_modifiers:
        if (" " in modifier or "-" in modifier) and modifier in low:
            words.update(modifier.replace("-", " ").split())
    return frozenset(words)


_TITLE_PHRASE = re.compile(
    r"(?<![\w])(?:working|employed|serving|currently\s+working)\s+as\s+(?:an?\s+|the\s+)?|"
    r"(?<![\w])(?:is|was|currently)\s+(?:an?\s+|the\s+)|(?<![\w])as\s+(?:an?\s+|the\s+)?",
    re.IGNORECASE,
)
_TITLE_STOP = frozenset(
    {"at", "with", "in", "since", "for", "from", "and", "who", "ctc", "having", "based", "of", "on"}
)


def _phrase_title(free: str) -> tuple[str, int, int] | None:
    """A title inside a sentence: "... working as a data analyst. 3 years ..."."""
    for m in _TITLE_PHRASE.finditer(free):
        words: list[str] = []
        rest = free[m.end() :]
        pos = 0
        for match in re.finditer(r"[A-Za-z][A-Za-z.+#&/'-]*", rest):
            if rest[pos : match.start()].strip():
                break  # punctuation or a number: the phrase ended
            pos = match.end()
            words.append(match.group(0))
            if len(words) >= 7 or match.group(0).casefold() in _TITLE_STOP:
                break
        while words and words[-1].casefold() in _TITLE_STOP:
            words.pop()
        last_head = max((i for i, w in enumerate(words) if _is_head(w)), default=-1)
        if last_head < 0:
            continue
        words = words[: last_head + 1]
        text = " ".join(words)
        offset = free.find(words[0], m.end())
        core = _title_core(text)
        if core is None:
            continue
        return core[0], offset, offset + len(text)
    return None


def _title_hits(doc: Doc) -> list[_TitleHit]:
    hits: list[_TitleHit] = []
    for chunk in doc.chunks:
        if chunk.key not in _TITLE_KEYS:
            continue
        free = doc.free_text(chunk)
        if chunk.key == "company":
            # "working at Cognizant as Senior Associate": the title follows the company.
            parts = _AS_TITLE.split(free, maxsplit=1)
            if len(parts) == 2:
                stripped = _TITLE_TAIL_PREP.sub("", parts[1].strip()).strip(" .")
                core = _title_core(stripped) if stripped else None
                if core is not None:
                    offset = free.find(stripped)
                    hits.append(
                        _TitleHit(
                            core[0],
                            chunk.start + offset,
                            chunk.start + offset + len(stripped),
                            "lead",
                            core[1],
                        )
                    )
            continue
        if chunk.key == "title":
            value = free[chunk.value_start - chunk.start :]
            value = _TITLE_TAIL_PREP.sub("", value.strip()).strip(" .")
            if value and not re.search(r"\d{2}|@", value):
                offset = free.find(value)
                hits.append(
                    _TitleHit(
                        smart_title(value),
                        chunk.start + offset,
                        chunk.start + offset + len(value),
                        "key",
                        all(_is_known_title_word(w) for w in value.split()),
                    )
                )
            continue
        body = _TITLE_TAIL_PREP.sub("", free.strip()).strip(" .")
        if not body:
            continue
        lead = _TITLE_LEAD.match(body)
        stripped = body[lead.end() :] if lead else body
        core = _title_core(stripped)
        if core is None:
            phrase = _phrase_title(free)
            if phrase is not None:
                hits.append(
                    _TitleHit(
                        phrase[0], chunk.start + phrase[1], chunk.start + phrase[2], "lead", True
                    )
                )
            continue
        text, known = core
        offset = free.find(stripped)
        hits.append(
            _TitleHit(
                text,
                chunk.start + offset,
                chunk.start + offset + len(stripped),
                "lead" if lead else "shape",
                known,
            )
        )
    return hits


def extract_title(doc: Doc) -> list[FieldResult]:
    hits = _title_hits(doc)
    if not hits:
        return []
    for hit in hits:
        doc.claim(hit.start, hit.end, block=False)
    distinct: dict[str, _TitleHit] = {}
    for hit in hits:
        distinct.setdefault(hit.text.casefold(), hit)
    if len(distinct) > 1:
        keyed = [h for h in hits if h.tier == "key"]
        if len({h.text.casefold() for h in keyed}) == 1:
            return [
                _title_result(keyed[0], f"{len(distinct)} titles found; the labelled one was used.")
            ]
        options = [
            Alternative(h.text, h.text, "A job title in the text") for h in distinct.values()
        ]
        return [
            ambiguous(
                "current_title",
                options,
                f"{len(distinct)} job titles found: which is the current one?",
            )
        ]
    (hit,) = distinct.values()
    return [_title_result(hit, None)]


def _title_result(hit: _TitleHit, warning: str | None) -> FieldResult:
    confidence: Literal["high", "medium", "low"]
    if hit.tier == "key":
        confidence, reason = "high", "Labelled as title / designation."
    elif hit.tier == "lead":
        confidence, reason = "high", "Written after 'working as' / 'is a'."
    elif hit.all_known:
        confidence, reason = "high", "Reads as a job title (known title words)."
    else:
        confidence, reason = (
            "medium",
            "Ends with a job-title word, but it has words we do not know.",
        )
    return found("current_title", hit.text, hit.text, confidence, reason, warning=warning)
