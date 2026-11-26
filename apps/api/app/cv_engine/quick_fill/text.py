"""Text cleaning, chunking ("key: value", commas, lines) and the claimed-span bookkeeping."""

from __future__ import annotations

import functools
import itertools
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from app.cv_engine.quick_fill.data import get_rules, norm_key

# Characters that carry no meaning for extraction and break matching.
_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")
_QUOTES = {
    ord("\u2018"): "'",
    ord("\u2019"): "'",
    ord("\u201c"): '"',
    ord("\u201d"): '"',
    ord("\u2026"): "...",
    ord("\u00a0"): " ",
    ord("\u2192"): " , ",
    ord("\u27a1"): " , ",
}
_BULLETS = "\u2022\u00b7\u25aa\u25cf\u25e6\u2023\u2043\u2219"
# Unicode categories treated as noise: symbols (emoji, dingbats), surrogates, private use.
_NOISE_CATEGORIES = frozenset({"So", "Sk", "Cs", "Co", "Cn"})

_WORD_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "ninety": 90,
}
_WORD_NUM_ALT = "|".join(sorted(_WORD_NUMBERS, key=len, reverse=True))
_UNIT_AHEAD = (
    r"(?=\s*(?:(?:and\s+)?(?:a\s+)?half\s+)?"
    r"(?:years?|yrs?|months?|mos?|days?|weeks?|wks?|lpa|lakhs?|lacs?|lac|crores?|cr)\b)"
)
_WORD_NUMBER_RE = re.compile(
    rf"\b({_WORD_NUM_ALT})(?:[\s-]+({_WORD_NUM_ALT}))?\b{_UNIT_AHEAD}", re.I
)
_BETWEEN_RE = re.compile(r"\bbetween\s+(?=\d)(.{1,24}?)\s+(?:and|&)\s+(?=\d)", re.I)
_AND_HALF_RE = re.compile(
    r"\b(\d+)\s+(?:and\s+(?:a\s+)?half|&\s*(?:a\s+)?half)\s+(years?|yrs?|months?|lakhs?|lacs?)\b",
    re.I,
)
_HALF_RE = re.compile(r"\b(\d+)\s*(?:and\s+)?(?:a\s+)?half\s+(years?|yrs?|months?)\b", re.I)


def _word_number(match: re.Match[str]) -> str:
    first = _WORD_NUMBERS[match.group(1).casefold()]
    second = match.group(2)
    if second is None:
        return str(first)
    extra = _WORD_NUMBERS[second.casefold()]
    # "twenty five" -> 25, but "five six" (two units digits) is left alone.
    if first >= 20 and extra < 10:
        return str(first + extra)
    return match.group(0)


def clean_text(raw: str) -> str:
    """Normalise unicode, drop emoji and symbols, turn number words into digits.

    Non-English letters are kept (they simply will not match any rule). Offsets in the result
    are the only offsets used afterwards.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = text.translate(_DASHES).translate(_QUOTES)
    out: list[str] = []
    for ch in text:
        category = unicodedata.category(ch)
        if ch in _BULLETS:
            out.append(" , ")
        elif ch in "\n\t":
            out.append(ch)
        elif category == "Cf" or ch in "\r\x0b\x0c":
            out.append(" " if ch in "\r\x0b\x0c" else "")
        elif (
            category == "So"
        ):  # emoji and pictographs usually separate the facts: "📍 Pune 💼 5 yrs"
            out.append(" , ")
        elif category in _NOISE_CATEGORIES or category == "Cc":
            out.append(" ")
        elif ch == "\u20b9":  # the rupee sign is a Sc symbol; keep it, spaced for matching
            out.append(" \u20b9")
        else:
            out.append(ch)
    text = "".join(out)
    text = _WORD_NUMBER_RE.sub(_word_number, text)
    text = _BETWEEN_RE.sub(lambda m: f"{m.group(1)} to ", text)  # "between 10 and 12 LPA"
    text = _AND_HALF_RE.sub(lambda m: f"{m.group(1)}.5 {m.group(2)}", text)
    text = _HALF_RE.sub(lambda m: f"{m.group(1)}.5 {m.group(2)}", text)
    text = _MARKDOWN_RE.sub("", text)
    lines = [_tidy_line(line) for line in text.split("\n")]
    return _BLANK_RUN_RE.sub("\n\n", "\n".join(lines)).strip("\n")


_MARKDOWN_RE = re.compile(r"\*\*|`+|~~")
# A list marker at the start of a line: "- ", "* ", "> ", "1. ", "2) ", "(3) ". Letters are not markers: "A. Kumar" is a name.
_LIST_MARKER_RE = re.compile(r"^(?:[-*>#]+|\(?\d{1,2}[.)])\s+")
_BLANK_RUN_RE = re.compile(r"\n{3,}")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,;:])")
_REPEATED_SEP_RE = re.compile(r"([,;])(?:\s*[,;])+")


def _tidy_line(line: str) -> str:
    """Whitespace, list markers and stray separators; the words themselves are untouched."""
    line = re.sub(r"[ \t]+", " ", line).strip()
    line = re.sub(r"^[,;\s]+", "", line)  # bullets became " , ": nothing before the first word
    line = _LIST_MARKER_RE.sub("", line, count=1)
    line = _REPEATED_SEP_RE.sub(r"\1", line)
    line = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", line)
    return line.strip(" ,;")


# --- Chunks -----------------------------------------------------------------------------------

# Splits a line into pieces. A comma between two digits stays (8,00,000).
# A full stop that ends a sentence ("... 6 years. Current CTC ...") also breaks, but not after an
# initial ("C. Ramesh"), a title ("Dr. Rao"), a company suffix ("Pvt. Ltd.") or inside a number.
_ABBREVIATIONS = (
    # titles and company suffixes
    "mr",
    "mrs",
    "ms",
    "dr",
    "sr",
    "jr",
    "prof",
    "st",
    "no",
    "pvt",
    "ltd",
    "inc",
    "co",
    "corp",
    "llc",
    "smt",
    "sh",
    # labels and units that are followed by a number: "Exp. 5 yrs", "Rs. 65,000"
    "rs",
    "exp",
    "approx",
    "ctc",
    "ectc",
    "cctc",
    "np",
    "tel",
    "ph",
    "mob",
    "ext",
    "ref",
    "min",
    "max",
    "avg",
    "sal",
    "curr",
    "expt",
    "inr",
    "usd",
)
_SENTENCE_END = (
    r"(?<=[A-Za-z0-9]{2})"
    + "".join(rf"(?i:(?<!\b{a}))" for a in _ABBREVIATIONS)
    + r"\.\s+(?=[A-Z0-9])"
)
_PIECE_BREAK = re.compile(rf"[;|\t]|(?<!\d),|,(?!\d)|{_SENTENCE_END}")
# Inside a piece: " - ", " / " and arrows separate ideas, except between two numbers (12 - 15).
_SUB_BREAK = re.compile(r"(?<!\d)\s+[-/]\s+|\s+[-/]\s+(?!\d)")
_LIST_KEYS = frozenset({"skills", "tags"})


@dataclass(slots=True)
class Chunk:
    """A piece of the text: one comma/line/"key: value" segment."""

    start: int
    end: int
    text: str
    key: str | None = None  # canonical key when written "key: value"
    value_start: int = 0
    value: str = ""
    index: int = 0


@functools.lru_cache(maxsize=1)
def _inner_key_re() -> re.Pattern[str]:
    """A label written after other text with only spaces between: "phone: 98... name: Tarun"."""
    aliases = sorted(get_rules().key_aliases, key=lambda a: (-len(a), a))
    body = "|".join(re.escape(a).replace(r"\ ", r"\s+") for a in aliases)
    return re.compile(rf"(?<![\w])(?:{body})\s*[:=]", re.IGNORECASE)


def _pieces(line: str, offset: int) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    pos = 0
    for m in _PIECE_BREAK.finditer(line):
        spans.append((pos, m.start()))
        pos = m.end()
    spans.append((pos, len(line)))
    out: list[tuple[int, int]] = []
    for a, b in spans:
        lead = a + len(line[a:b]) - len(line[a:b].lstrip())
        cuts = [m.start() for m in _inner_key_re().finditer(line, a, b) if m.start() > lead]
        edges = [a, *cuts, b]
        out.extend((x, y) for x, y in itertools.pairwise(edges) if line[x:y].strip())
    return [(offset + a, offset + b) for a, b in out]


def _key_of(piece: str) -> tuple[str, int] | None:
    """Canonical key and the offset (within `piece`) where its value starts."""
    m = get_rules().key_re.match(piece) or get_rules().key_space_re.match(piece)
    if m is None:
        return None
    canonical = get_rules().key_aliases.get(norm_key(m.group("key")))
    if canonical is None:
        return None
    value = m.group("val")
    if canonical == "current_any":
        # "Current: 8 LPA" is a salary label; "Current: Infosys" is not, so it needs a digit.
        if not any(ch.isdigit() for ch in value):
            return None
        canonical = "current_ctc"
    return canonical, m.start("val")


def build_chunks(text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    offset = 0
    for line in text.split("\n"):
        if line.strip():
            chunks.extend(_line_chunks(text, line, offset))
        offset += len(line) + 1
    for index, chunk in enumerate(chunks):
        chunk.index = index
    return chunks


def _line_chunks(text: str, line: str, offset: int) -> list[Chunk]:
    out: list[Chunk] = []
    spans = _pieces(line, offset)
    i = 0
    while i < len(spans):
        start, end = spans[i]
        piece = text[start:end]
        keyed = _key_of(piece)
        if keyed is not None and keyed[0] in _LIST_KEYS:
            # "Skills: Python, Django, AWS": the commas belong to the value, up to the next label.
            j = i + 1
            while j < len(spans) and _key_of(text[spans[j][0] : spans[j][1]]) is None:
                j += 1
            end = spans[j - 1][1]
            i = j
        else:
            i += 1
        out.extend(_make_chunks(text, start, end, keyed))
    return [c for c in out if c.text.strip()]


def _make_chunks(text: str, start: int, end: int, keyed: tuple[str, int] | None) -> list[Chunk]:
    piece = text[start:end]
    lead = len(piece) - len(piece.lstrip())
    stripped = piece.strip()
    if not stripped:
        return []
    if keyed is not None:
        key, value_off = keyed
        value = piece[value_off:].strip()
        if key in ("ignore",):
            return [Chunk(start + lead, end - (len(piece) - len(piece.rstrip())), stripped, key)]
        if value:
            return [
                Chunk(
                    start=start + lead,
                    end=end - (len(piece) - len(piece.rstrip())),
                    text=stripped,
                    key=key,
                    value_start=start + value_off,
                    value=value,
                )
            ]
    # Not keyed (or a key with no value): split on spaced hyphens and slashes.
    chunks: list[Chunk] = []
    pos = 0
    for m in _SUB_BREAK.finditer(piece):
        chunks.append(_plain(text, start, piece, pos, m.start()))
        pos = m.end()
    chunks.append(_plain(text, start, piece, pos, len(piece)))
    return [c for c in chunks if c.text]


def _plain(text: str, base: int, piece: str, a: int, b: int) -> Chunk:
    segment = piece[a:b]
    lead = len(segment) - len(segment.lstrip())
    stripped = segment.strip()
    s = base + a + lead
    return Chunk(start=s, end=s + len(stripped), text=stripped, value_start=s, value=stripped)


# --- Document ---------------------------------------------------------------------------------


@dataclass(slots=True)
class Entity:
    label: str
    text: str
    start: int
    end: int


@dataclass(slots=True)
class Doc:
    """The cleaned text plus what earlier extractors have already used ("claimed" spans)."""

    text: str
    chunks: list[Chunk]
    claimed: bytearray  # used by an extractor: later extractors must not reuse these characters
    seen: bytearray  # understood (claimed or a soft match such as a job title)
    _ents: list[Entity] | None = field(default=None, repr=False)

    @classmethod
    def from_raw(cls, raw: str) -> Doc:
        text = clean_text(raw)
        return cls(
            text=text,
            chunks=build_chunks(text),
            claimed=bytearray(len(text)),
            seen=bytearray(len(text)),
        )

    def claim(self, start: int, end: int, *, block: bool = True) -> None:
        """Mark a span as understood. `block=False` keeps it available to later extractors."""
        lo, hi = max(start, 0), min(end, len(self.claimed))
        for i in range(lo, hi):
            self.seen[i] = 1
            if block:
                self.claimed[i] = 1

    def masked(self) -> str:
        """The text with claimed characters blanked out (newlines and offsets preserved)."""
        return "".join(
            " " if self.claimed[i] and ch != "\n" else ch for i, ch in enumerate(self.text)
        )

    def is_claimed(self, start: int, end: int) -> bool:
        return any(self.claimed[max(start, 0) : min(end, len(self.claimed))])

    def chunk_at(self, pos: int) -> Chunk | None:
        for chunk in self.chunks:
            if chunk.start <= pos < chunk.end:
                return chunk
        return None

    def keyed(self, *keys: str) -> list[Chunk]:
        wanted = set(keys)
        return [c for c in self.chunks if c.key in wanted]

    def unkeyed(self) -> list[Chunk]:
        return [c for c in self.chunks if c.key is None]

    def free_text(self, chunk: Chunk) -> str:
        """The chunk's text with already-claimed characters blanked out (offsets preserved)."""
        chars = list(self.text[chunk.start : chunk.end])
        for i in range(len(chars)):
            if self.claimed[chunk.start + i]:
                chars[i] = " "
        return "".join(chars)

    def entities(self) -> list[Entity]:
        if self._ents is None:
            self._ents = _run_ner(self.text)
        return self._ents


# --- spaCy (optional) -------------------------------------------------------------------------

_NLP_CACHE: dict[str, Any] = {}


def _load_nlp() -> Any | None:
    if "nlp" in _NLP_CACHE:
        return _NLP_CACHE["nlp"]
    nlp: Any | None = None
    try:
        import spacy

        nlp = spacy.load(
            "en_core_web_sm", exclude=["parser", "lemmatizer", "attribute_ruler", "tagger"]
        )
    except (ImportError, OSError):
        nlp = None
    _NLP_CACHE["nlp"] = nlp
    return nlp


def _run_ner(text: str) -> list[Entity]:
    """spaCy named entities (PERSON, GPE, ORG). Empty when the model is not installed."""
    nlp = _load_nlp()
    if nlp is None or not text.strip():
        return []
    entities: list[Entity] = []
    for ent in nlp(text[:5000]).ents:
        if ent.label_ in {"PERSON", "GPE", "ORG", "LOC"}:
            entities.append(Entity(ent.label_, ent.text, ent.start_char, ent.end_char))
    return entities
