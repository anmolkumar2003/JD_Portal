"""First and last name.

Names are the hardest field: there is no keyword to anchor on. The extractor therefore only
accepts a piece of text as a name when everything else has already been explained (it runs after
the other extractors), when it has the shape of a name, and when no dictionary says otherwise.
When two pieces look like names the result lists both and picks neither.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.cv_engine.quick_fill.common import ambiguous, found, title_name
from app.cv_engine.quick_fill.data import get_gazetteer, get_rules, norm_key
from app.cv_engine.quick_fill.text import Chunk, Doc
from app.cv_engine.quick_fill.types import Alternative, FieldResult
from app.cv_engine.skills import is_known_skill

_NAME_LEAD = re.compile(
    r"^(?:(?:my\s+name\s+is|name\s+is|name|this\s+is|i\s+am|i'm|candidate|applicant|meet|"
    r"add|adding|please\s+add|mr|mrs|ms|miss|mx|shri|smt|dr|prof)\.?\s+)+",
    re.IGNORECASE,
)
_SENTENCE_NAME = re.compile(
    r"^(?P<n>[^\W\d_][\w'.-]*(?:\s+[^\W\d_][\w'.-]*){0,3}?)\s+"
    r"(?:is|has|have|works|working|lives|living|from|based|currently|with|having|was|will|"
    r"stays|staying|resides|located)\b",
    re.IGNORECASE,
)
_TOKEN = re.compile(r"^[^\W\d_][\w'.-]*$")
_NAME_KEYS = frozenset({None, "name", "first_name", "last_name"})
_SUFFIXES = frozenset({"jr", "sr", "ii", "iii"})


@dataclass(slots=True)
class _NameHit:
    tokens: list[str]
    start: int
    end: int
    confidence: Literal["high", "medium", "low"]
    reason: str


def _tokens(text: str) -> list[str] | None:
    words = text.strip(" .,;:").split()
    if not 1 <= len(words) <= 4 or any(not _TOKEN.match(w) for w in words):
        return None
    return words


def _is_non_name(words: list[str]) -> bool:
    rules = get_rules()
    gazetteer = get_gazetteer()
    whole = " ".join(words)
    if norm_key(whole) in gazetteer.places or norm_key(whole) in rules.company_by_alias:
        return True
    if is_known_skill(whole) and whole.casefold() not in rules.first_names:
        return True
    for word in words:
        low = word.casefold().strip(".")
        if low in rules.non_name_words or low in rules.title_heads or low in rules.departments:
            return True
        if low in rules.title_modifiers and low not in rules.first_names:
            return True
        if len(low.strip(".")) > 1 and is_known_skill(word) and low not in rules.first_names:
            return True  # "knows Docker": a skill, not a person
        if norm_key(low) in gazetteer.places and low not in rules.first_names:
            return True
        initial = len(word.strip(".")) == 1  # "C. Ramesh": a single initial is fine
        if word.isupper() and len(word) <= 3 and not initial and low not in rules.first_names:
            return True  # QA, HR, AWS, NA ...
        if any(low in alias for alias in rules.sources.values()):
            return True
    return False


def _first_known(words: list[str]) -> bool:
    return words[0].casefold().strip(".") in get_rules().first_names


def _shape_ok(words: list[str]) -> bool:
    return all(w[:1].isupper() for w in words)


def _score(words: list[str], doc: Doc, start: int, end: int, *, keyed: bool) -> _NameHit | None:
    if keyed:
        return _NameHit(words, start, end, "high", "Labelled as name.")
    if _is_non_name(words):
        return None
    known = _first_known(words)
    shape = _shape_ok(words)
    if len(words) == 1:
        if not known:
            return None
        return _NameHit(
            words, start, end, "medium", "A single known first name; no last name found."
        )
    spacy = _spacy_label(doc, start, end)
    if spacy in ("GPE", "ORG", "LOC") and not known:
        suffixes = get_rules().company_suffixes
        if (
            spacy == "ORG"
            and shape
            and len(words) <= 3
            and not any(w.casefold().strip(".") in suffixes for w in words)
        ):
            # spaCy often reads unfamiliar Indian names as organisations. Offer, never tick.
            return _NameHit(
                words,
                start,
                end,
                "medium",
                "Capitalised words; spaCy read them as an organisation but no known company matches.",
            )
        return None
    if known and shape:
        return _NameHit(words, start, end, "high", "Starts with a common first name.")
    if spacy == "PERSON" and shape:
        return _NameHit(words, start, end, "high", "Recognised as a person name (spaCy).")
    if known:
        return _NameHit(words, start, end, "medium", "Looks like a name, but is not capitalised.")
    if spacy == "PERSON":
        return _NameHit(
            words, start, end, "low", "Recognised as a name by spaCy, but not capitalised."
        )
    if shape and len(words) <= 3:
        return _NameHit(
            words, start, end, "medium", "Capitalised words that no other rule explains."
        )
    return _NameHit(words, start, end, "low", "Unexplained words that might be a name.")


def _spacy_label(doc: Doc, start: int, end: int) -> str | None:
    for ent in doc.entities():
        if ent.start <= start and ent.end >= end - 1 and ent.start >= start - 1:
            return ent.label
    for ent in doc.entities():
        if not (ent.end <= start or ent.start >= end):
            return ent.label
    return None


def _chunk_hit(doc: Doc, chunk: Chunk) -> _NameHit | None:
    keyed = chunk.key in ("name", "first_name", "last_name")
    if chunk.key not in _NAME_KEYS:
        return None
    if not keyed and any(doc.seen[chunk.start : chunk.end]):
        # Part of the chunk is already explained. Only the sentence form may still hold a name.
        return _sentence_hit(doc, chunk)
    value = chunk.value if keyed else doc.text[chunk.start : chunk.end]
    offset = chunk.value_start if keyed else chunk.start
    lead = _NAME_LEAD.match(value) if not keyed or chunk.key == "name" else None
    if lead:
        offset += lead.end()
        value = value[lead.end() :]
    words = _tokens(value)
    if words is None:
        return _sentence_hit(doc, chunk) if not keyed else None
    hit = _score(words, doc, offset, offset + len(value), keyed=keyed)
    if hit is not None and lead:
        hit.confidence = "high" if hit.confidence != "low" else "medium"
        hit.reason = "Written after 'my name is' / 'candidate' / a title such as Mr."
    return hit


def _sentence_hit(doc: Doc, chunk: Chunk) -> _NameHit | None:
    free = doc.free_text(chunk).strip()
    lead = _NAME_LEAD.match(free)
    rest = free[lead.end() :] if lead else free
    m = _SENTENCE_NAME.match(rest)
    if m is None:
        return None
    words = _tokens(m.group("n"))
    if words is None:
        return None
    begin = chunk.start + doc.free_text(chunk).find(rest) + m.start("n")
    hit = _score(words, doc, begin, begin + len(m.group("n")), keyed=False)
    if hit is None or hit.confidence == "low":
        return None
    hit.reason = "A name at the start of a sentence."
    return hit


def _clean(words: list[str]) -> list[str]:
    return [
        title_name(w.strip(".")) if w.casefold().strip(".") not in _SUFFIXES else w for w in words
    ]


def _split(words: list[str]) -> tuple[str, str | None]:
    cleaned = _clean(words)
    if len(cleaned) == 1:
        return cleaned[0], None
    return " ".join(cleaned[:-1]), cleaned[-1]


def extract_name(doc: Doc) -> list[FieldResult]:
    results: list[FieldResult] = []
    keyed_first = [c for c in doc.chunks if c.key == "first_name"]
    keyed_last = [c for c in doc.chunks if c.key == "last_name"]
    keyed_full = [c for c in doc.chunks if c.key == "name"]
    taken: set[str] = set()
    for chunk in keyed_first[:1]:
        hit = _chunk_hit(doc, chunk)
        if hit:
            doc.claim(hit.start, hit.end)
            results.append(
                found(
                    "first_name",
                    " ".join(_clean(hit.tokens)),
                    " ".join(_clean(hit.tokens)),
                    "high",
                    hit.reason,
                )
            )
            taken.add("first_name")
    for chunk in keyed_last[:1]:
        hit = _chunk_hit(doc, chunk)
        if hit:
            doc.claim(hit.start, hit.end)
            results.append(
                found(
                    "last_name",
                    " ".join(_clean(hit.tokens)),
                    " ".join(_clean(hit.tokens)),
                    "high",
                    hit.reason,
                )
            )
            taken.add("last_name")
    if len(keyed_full) > 1:
        names = [_chunk_hit(doc, c) for c in keyed_full]
        return results + _ambiguous_names([h for h in names if h])
    pool: list[_NameHit] = []
    for chunk in keyed_full:
        hit = _chunk_hit(doc, chunk)
        if hit:
            pool.append(hit)
    if not pool and not ({"first_name", "last_name"} & taken):
        for chunk in doc.chunks:
            if chunk.key is not None:
                continue
            hit = _chunk_hit(doc, chunk)
            if hit is not None:
                pool.append(hit)
        if not pool:
            pool.extend(_spacy_fallback(doc))
    if not pool:
        return results
    distinct: dict[str, _NameHit] = {}
    for hit in pool:
        distinct.setdefault(" ".join(hit.tokens).casefold(), hit)
    if len(distinct) > 1:
        strong = [h for h in distinct.values() if h.confidence != "low"]
        if len(strong) == 1:
            # Weaker word groups stay unclaimed: they show up under "not understood".
            return results + _name_results(doc, strong[0], taken, None)
        chosen = strong or list(distinct.values())
        for hit in chosen:
            doc.claim(hit.start, hit.end)
        return results + _ambiguous_names(chosen)
    (hit,) = distinct.values()
    return results + _name_results(doc, hit, taken, None)


def _name_results(
    doc: Doc, hit: _NameHit, taken: set[str], warning: str | None
) -> list[FieldResult]:
    doc.claim(hit.start, hit.end)
    first, last = _split(hit.tokens)
    out: list[FieldResult] = []
    note = hit.reason
    if last is not None and len(hit.tokens) > 2:
        note += " Everything before the last word is the first name."
    if "first_name" not in taken:
        out.append(found("first_name", first, first, hit.confidence, note, warning=warning))
    if last is not None and "last_name" not in taken:
        out.append(found("last_name", last, last, hit.confidence, note, warning=warning))
    return out


def _ambiguous_names(hits: list[_NameHit]) -> list[FieldResult]:
    if not hits:
        return []
    firsts: list[Alternative] = []
    lasts: list[Alternative] = []
    for hit in hits:
        first, last = _split(hit.tokens)
        full = " ".join(_clean(hit.tokens))
        firsts.append(Alternative(first, full, hit.reason))
        if last is not None:
            lasts.append(Alternative(last, full, hit.reason))
    warning = f"{len(hits)} different names found: choose one."
    out = [ambiguous("first_name", firsts, warning)]
    if lasts:
        out.append(ambiguous("last_name", lasts, warning))
    return out


def _spacy_fallback(doc: Doc) -> list[_NameHit]:
    """A PERSON entity in text the other rules left alone ("Please call Rahul Sharma")."""
    hits: list[_NameHit] = []
    for ent in doc.entities():
        if ent.label != "PERSON" or doc.is_claimed(ent.start, ent.end):
            continue
        words = _tokens(ent.text)
        if words is None or _is_non_name(words):
            continue
        hits.append(
            _NameHit(
                words,
                ent.start,
                ent.end,
                "low",
                "Recognised as a person name (spaCy) inside other text.",
            )
        )
    return hits
