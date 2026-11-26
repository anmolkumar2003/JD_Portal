"""Salary (current / expected / offered CTC), negotiable, notice period and experience."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from app.cv_engine.quick_fill.common import ambiguous, found
from app.cv_engine.quick_fill.normalize import (
    EXPERIENCE_RE,
    FRESHER_RE,
    IMMEDIATE_RE,
    MAX_EXPERIENCE_YEARS,
    MONEY_RE,
    MONTH_UNIT,
    MONTHS_ONLY_RE,
    NOTICE_RE,
    NUM,
    YEAR_UNIT,
    YOE_RE,
    Money,
    MoneyValue,
    Quantity,
    amount_json,
    experience_from_match,
    format_money,
    make_money,
    money_from_match,
    notice_from_match,
    parse_number,
    round_years,
)
from app.cv_engine.quick_fill.text import Chunk, Doc
from app.cv_engine.quick_fill.types import Alternative, FieldResult, Json

Label = Literal["current", "expected", "offered"]
LABELS: tuple[Label, ...] = ("current", "expected", "offered")

# --- Salary labels ----------------------------------------------------------------------------

_EXPLICIT_LABELS: dict[Label, re.Pattern[str]] = {
    "expected": re.compile(
        r"(?<![\w])(?:expected|expecting|expects?|expectations?|e[\s-]?ctc|exp[\s.]*ctc|"
        r"looking\s+for|looking\s+at|wants?|asking(?:\s+for)?|asks?\s+for|demand(?:ing)?|"
        r"desired|target(?:ing)?|hoping(?:\s+for)?|aiming(?:\s+for)?|seeking)(?![a-z])",
        re.IGNORECASE,
    ),
    "current": re.compile(
        r"(?<![\w])(?:current(?:ly)?|present(?:ly)?|existing|c{1,2}[\s-]?ctc|drawing|drawn|"
        r"earning|getting|last\s+drawn|in[\s-]?hand|take[\s-]?home)(?![a-z])",
        re.IGNORECASE,
    ),
    "offered": re.compile(
        r"(?<![\w])(?:offered|offering|offer(?:\s+(?:of|ctc|salary|package))?|we\s+offer)(?![a-z])",
        re.IGNORECASE,
    ),
}
_GENERIC_LABEL = re.compile(
    r"(?<![\w])(?:ctc|salary|package|compensation|pay|remuneration)(?![a-z])", re.IGNORECASE
)
# Words allowed between a label and its amount ("expected CTC is around 12 LPA").
_FILLER = re.compile(
    r"^[\s:=\-~.,()]*(?:(?:ctc|salary|package|compensation|pay|amount|is|of|at|around|approx"
    r"(?:imately)?|about|nearly|roughly|drawing|getting|earning|in\s+hand|take\s+home|"
    r"currently|presently|now|currency|fixed|variable|total|annual|monthly|rs|inr)"
    r"(?![a-z])[\s:=\-~.,()]*)*$",
    re.IGNORECASE,
)
_INHAND = re.compile(r"in[\s-]?hand|take[\s-]?home", re.IGNORECASE)
_COMPETING = re.compile(
    r"(?:another|other|competing|counter|different|alternate)\s+offer|offer\s+(?:in\s+hand|from)"
    r"|offer\s+of\s+[\d\u20b9$]+[^,;]{0,25}\s+from|from\s+[A-Z]",
)
_AFTER_LABEL = re.compile(
    r"^[\s:()\-]*(?:ctc\s*)?(?P<word>current(?:ly)?|present|expected|expecting|offered|offer|"
    r"e[\s-]?ctc|c{1,2}[\s-]?ctc)(?![a-z])",
    re.IGNORECASE,
)
_PAIR_LABEL = (
    r"(?:c{1,2}[\s-]?ctc|current(?:\s+ctc)?|present(?:\s+ctc)?|ctc)\s*(?:/|&|\+|and)\s*"
    r"(?:e[\s-]?ctc|exp(?:ected)?[\s.]*ctc|expected(?:\s+ctc)?|expected)"
)
_NUM_TOKEN = rf"(?:\u20b9\s?|rs\.?\s?|\$\s?)?{NUM}\s*(?:lpa|lakhs?|lacs?|lks?|cr(?:ores?)?|k|l)?"
_PAIR_RE = re.compile(
    rf"(?P<label>{_PAIR_LABEL})\s*[:=\-]*\s*(?P<a>{_NUM_TOKEN})\s*(?:/|&|,|\+|and|-)\s*(?P<b>{_NUM_TOKEN})"
    rf"(?P<tail>\s*(?:lpa|lakhs?|lacs?|per\s+(?:annum|month|year)|pa|pm|p\.a\.|p\.m\.))?",
    re.IGNORECASE,
)
# A bare number straight after a label: "current 8", "ECTC: 12", "CTC - 8,50,000".
_BARE_AFTER_LABEL = re.compile(
    rf"(?<![\w])(?P<label>current(?:\s+ctc)?|present(?:\s+ctc)?|existing(?:\s+ctc)?|cctc|c[\s-]ctc|"
    rf"expected(?:\s+(?:ctc|salary|package))?|expecting|e[\s-]?ctc|exp[\s.]*ctc|offered(?:\s+ctc)?|"
    rf"ctc|salary|package)\s*(?:is|of|:|=|-|~)?\s*(?:\u20b9\s?|rs\.?\s?|inr\s?)?(?P<n>{NUM})"
    rf"(?![\d.,]*\s*(?:%|years?|yrs?|y\b|days?|d\b|months?|mo|weeks?|lpa|l\b|k\b|cr|lakh|lac|"
    rf"[a-z]*@))",
    re.IGNORECASE,
)
_NEGATIVE_NEGOTIABLE = re.compile(
    r"(?<![\w])(?:non[\s-]?negotiable|not\s+negotiable|no\s+negotiation|not\s+flexible)(?![a-z])",
    re.IGNORECASE,
)
_NEGOTIABLE = re.compile(
    r"(?<![\w])(?:negotiable|negotiate[sd]?|negotiation|nego|neg\.?|open\s+to\s+negotiat\w*|"
    r"(?:salary|ctc|package)\s+is\s+flexible|flexible\s+(?:on|with)\s+(?:salary|ctc|package))"
    r"(?![a-z])",
    re.IGNORECASE,
)
_NOTICE_WORDS = re.compile(r"notice|(?<![\w])np(?![\w])|joining|serving", re.IGNORECASE)


# Keys whose values are never a number we extract here (so "Skills: Python 3" is left alone).
_OTHER_KEYS = frozenset(
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
        "location",
        "experience",
        "notice",
        "current_ctc",
        "expected_ctc",
        "offered_ctc",
        "negotiable",
    }
)


def _skip(chunk: Chunk, *own: str) -> bool:
    """True when the chunk is labelled as something other than the field being extracted."""
    return chunk.key is not None and chunk.key in _OTHER_KEYS and chunk.key not in own


@dataclass(slots=True)
class _Mention:
    start: int
    end: int
    money: Money
    chunk: Chunk
    label: Label | None = None
    strength: Literal["key", "explicit", "generic", "pair", "bare"] | None = None
    inhand: bool = False
    competing: bool = False
    notes: list[str] = field(default_factory=list)


def _key_label(chunk: Chunk) -> tuple[Label, bool] | None:
    """Label from a "key: value" chunk, and whether the key itself was explicit."""
    mapping: dict[str, Label] = {
        "current_ctc": "current",
        "expected_ctc": "expected",
        "offered_ctc": "offered",
    }
    label = mapping.get(chunk.key or "")
    if label is None:
        return None
    key_text = chunk.text[: chunk.value_start - chunk.start]
    explicit = bool(_EXPLICIT_LABELS[label].search(key_text)) or label != "current"
    return label, explicit


def _window_label(before: str, after: str) -> tuple[Label | None, str | None]:
    """Nearest explicit label before the amount (only filler words between), else after it."""
    best: tuple[int, Label] | None = None
    for label, pattern in _EXPLICIT_LABELS.items():
        for m in pattern.finditer(before):
            if _FILLER.match(before[m.end() :]) and (best is None or m.end() > best[0]):
                best = (m.end(), label)
    if best is not None:
        return best[1], "explicit"
    trailing = _AFTER_LABEL.match(after)
    if trailing:
        word = trailing.group("word").casefold()
        if word.startswith(("expect", "e")):
            return "expected", "explicit"
        if word.startswith(("offer",)):
            return "offered", "explicit"
        return "current", "explicit"
    for m in _GENERIC_LABEL.finditer(before):
        if _FILLER.match(before[m.end() :]):
            return "current", "generic"
    return None, None


def _collect_mentions(doc: Doc) -> list[_Mention]:
    mentions: list[_Mention] = []
    for chunk in doc.chunks:
        if _skip(chunk, "current_ctc", "expected_ctc", "offered_ctc"):
            continue
        free = doc.free_text(chunk)
        found_here: list[_Mention] = []
        for m in MONEY_RE.finditer(free):
            money = money_from_match(m)
            if money is None:
                continue
            found_here.append(
                _Mention(chunk.start + m.start(), chunk.start + m.end(), money, chunk)
            )
        # Bare numbers after a label ("current 8") that carry no unit of their own.
        for m in _BARE_AFTER_LABEL.finditer(free):
            start, end = chunk.start + m.start("n"), chunk.start + m.end("n")
            if any(not (end <= f.start or start >= f.end) for f in found_here):
                continue
            number = parse_number(m.group("n"))
            if number is None:
                continue
            low_label = m.group("label").casefold()
            value = make_money(m.group("n"), None, "INR", None, bare_lakhs=True)
            mention = _Mention(chunk.start + m.start("label"), end, Money(value), chunk)
            mention.label = _label_from_word(low_label)
            mention.strength = (
                "generic"
                if mention.label == "current" and low_label in ("ctc", "salary", "package")
                else "explicit"
            )
            mention.notes.append("A small number next to a CTC label is read as lakhs per annum.")
            found_here.append(mention)
        # "CTC: 800000" style: a keyed chunk whose value is just a number.
        if chunk.key in ("current_ctc", "expected_ctc", "offered_ctc") and not found_here:
            bare = re.fullmatch(rf"\s*(?:\u20b9|rs\.?|inr)?\s*(?P<n>{NUM})\s*", chunk.value, re.I)
            if bare:
                value = make_money(bare.group("n"), None, "INR", None, bare_lakhs=True)
                found_here.append(_Mention(chunk.value_start, chunk.end, Money(value), chunk))
        found_here.sort(key=lambda mention: mention.start)
        mentions.extend(_label_mentions(doc, chunk, found_here))
    return mentions


def _label_from_word(word: str) -> Label:
    if word.startswith(("expect", "e-", "e ", "ectc", "exp")):
        return "expected"
    if word.startswith("offer"):
        return "offered"
    return "current"


def _label_mentions(doc: Doc, chunk: Chunk, here: list[_Mention]) -> list[_Mention]:
    keyed = _key_label(chunk)
    text = doc.text
    for index, mention in enumerate(here):
        if mention.label is not None:  # already labelled by a bare "label number" match
            continue
        prev_end = here[index - 1].end if index else chunk.start
        next_start = here[index + 1].start if index + 1 < len(here) else chunk.end
        before = text[prev_end : mention.start]
        after = text[mention.end : min(next_start, mention.end + 30)]
        if keyed is not None:
            mention.label = keyed[0]
            mention.strength = "key" if keyed[1] else "generic"
        else:
            label, strength = _window_label(before, after)
            if label is not None:
                mention.label = label
                mention.strength = "explicit" if strength == "explicit" else "generic"
        context = text[max(chunk.start, mention.start - 30) : min(chunk.end, mention.end + 30)]
        if _INHAND.search(before) or _INHAND.search(after):
            mention.inhand = True
        if mention.label == "offered" and _COMPETING.search(context):
            mention.competing = True
    return here


def _pair_mentions(doc: Doc) -> list[_Mention]:
    """ "CTC/ECTC: 8/12 LPA": two labels and two amounts written side by side."""
    out: list[_Mention] = []
    for m in _PAIR_RE.finditer(doc.masked()):
        a_text, b_text = m.group("a"), m.group("b")
        tail = (m.group("tail") or "").strip()
        a_money = _pair_money(a_text, b_text, tail)
        b_money = _pair_money(b_text, a_text, tail)
        if a_money is None or b_money is None:
            continue
        chunk = doc.chunk_at(m.start("label")) or doc.chunks[0]
        left = _Mention(m.start("a"), m.end("a"), a_money, chunk, "current", "pair")
        right = _Mention(m.start("b"), m.end("b"), b_money, chunk, "expected", "pair")
        doc.claim(m.start(), m.end())
        out.extend([left, right])
    return out


def _pair_money(own: str, other: str, tail: str) -> Money | None:
    """Amount with the unit of its partner when it has none ("8/12 LPA")."""
    text = own if re.search(r"[a-z\u20b9$]", own, re.I) else f"{own} {_unit_word(other)} {tail}"
    for m in MONEY_RE.finditer(text):
        money = money_from_match(m)
        if money is not None:
            return money
    match = re.fullmatch(rf"\s*(?P<n>{NUM})\s*", own)
    if match:
        return Money(make_money(match.group("n"), None, "INR", None, bare_lakhs=True))
    return None


def _unit_word(text: str) -> str:
    m = re.search(r"(?:lpa|lakhs?|lacs?|lks?|cr(?:ores?)?|k|l)\b", text, re.I)
    return m.group(0) if m else ""


def _money_json(value: MoneyValue) -> Json:
    return {"amount": amount_json(value.amount), "currency": value.currency, "unit": value.unit}


def _alt(value: MoneyValue, reason: str) -> Alternative:
    return Alternative(_money_json(value), format_money(value), reason)


def _sanity_warning(value: MoneyValue) -> str | None:
    annual = value.amount * (12 if value.unit == "pm" else 1)
    if value.currency == "INR" and annual > Decimal(50_000_000):
        return "Unusually large amount: check for a typo."
    if value.currency == "INR" and annual < Decimal(12_000):
        return "Unusually small amount: check the unit."
    return None


def _salary_result(label: Label, mention: _Mention) -> FieldResult:
    name = f"{label}_ctc"
    money = mention.money
    value = money.value
    notes: list[str] = []
    confidence: Literal["high", "medium", "low"] = "high"
    if mention.strength == "key":
        notes.append("Labelled as " + label + " CTC.")
    elif mention.strength == "pair":
        notes.append("Read from paired labels (CTC/ECTC): first current, second expected.")
    elif mention.strength == "explicit":
        notes.append(f"The word '{label}' sits next to the amount.")
    else:
        notes.append("Only 'CTC' / 'salary' was written, which usually means current CTC.")
        confidence = "medium"
    if value.assumed:
        notes.append(value.assumed)
        confidence = "medium"
    notes.extend(mention.notes)
    warning: str | None = None
    candidates: list[Alternative] = []
    if money.low is not None:
        confidence = "medium"
        midpoint = money.midpoint
        assert midpoint is not None  # noqa: S101
        candidates = [
            _alt(money.low, "Lower end of the range"),
            _alt(midpoint, "Midpoint of the range"),
            _alt(value, "Upper end of the range (filled)"),
        ]
        warning = (
            f"Range {format_money(money.low)} to {format_money(value)}: the maximum was filled. "
            f"Choose the midpoint ({format_money(midpoint)}) if you prefer."
        )
    if mention.inhand:
        confidence = "low"
        notes.append("Written as in-hand / take-home pay, which is not the same as CTC.")
        warning = (warning + " " if warning else "") + "In-hand pay is not CTC: check this value."
    if mention.competing:
        confidence = "low"
        notes.append("This may be another company's offer, not ours.")
        warning = (warning + " " if warning else "") + "Looks like a competing offer."
    sanity = _sanity_warning(value)
    if sanity:
        confidence = "low"
        warning = (warning + " " if warning else "") + sanity
    return found(
        name,
        _money_json(value),
        format_money(value),
        confidence,
        " ".join(notes),
        candidates=candidates,
        warning=warning,
    )


def extract_salary(doc: Doc) -> list[FieldResult]:
    mentions = _pair_mentions(doc) + _collect_mentions(doc)
    if not mentions:
        return []
    results: list[FieldResult] = []
    by_label: dict[Label, list[_Mention]] = {"current": [], "expected": [], "offered": []}
    unlabeled: list[_Mention] = []
    for mention in sorted(mentions, key=lambda x: x.start):
        doc.claim(mention.start, mention.end)
        if mention.label is None:
            unlabeled.append(mention)
        else:
            by_label[mention.label].append(mention)
    assigned: dict[Label, _Mention] = {}
    for label in LABELS:
        group = by_label[label]
        if not group:
            continue
        distinct = {(m.money.value.amount, m.money.value.unit) for m in group}
        if len(distinct) == 1:
            best = max(group, key=lambda m: _strength_rank(m.strength))
            assigned[label] = best
            results.append(_salary_result(label, best))
            continue
        strong = [m for m in group if m.strength in ("key", "pair")]
        if len(strong) == 1:
            assigned[label] = strong[0]
            result = _salary_result(label, strong[0])
            result.warning = (result.warning + " " if result.warning else "") + (
                f"{len(group)} amounts were labelled {label}; the explicitly labelled one was used."
            )
            results.append(result)
            continue
        options = [_alt(m.money.value, f"Written next to '{label}'") for m in group]
        results.append(
            ambiguous(
                f"{label}_ctc",
                options,
                f"{len(group)} different amounts are labelled {label}: choose one.",
            )
        )
    if unlabeled:
        results.extend(_unlabeled_results(unlabeled, assigned))
    results.extend(_negotiable_results(doc, mentions, assigned))
    return results


def _strength_rank(strength: str | None) -> int:
    return {"key": 4, "pair": 4, "explicit": 3, "generic": 2, "bare": 1}.get(strength or "", 0)


def _unlabeled_results(
    unlabeled: list[_Mention], assigned: dict[Label, _Mention]
) -> list[FieldResult]:
    """Amounts with no current/expected label are offered as choices, never assigned."""
    open_labels = [label for label in ("current", "expected") if label not in assigned]
    if not open_labels:
        return []
    seen: dict[tuple[Decimal, str], _Mention] = {}
    for mention in unlabeled:
        seen.setdefault((mention.money.value.amount, mention.money.value.unit), mention)
    options = [_alt(m.money.value, "An amount with no label") for m in seen.values()]
    shown = ", ".join(format_money(m.money.value) for m in seen.values())
    count = len(seen)
    if count == 1:
        warning = f"One salary ({shown}) has no current/expected label: say which it is."
    else:
        warning = f"{count} salaries ({shown}) have no current/expected label: say which is which."
    return [ambiguous(f"{label}_ctc", options, warning) for label in open_labels]


def _negotiable_results(
    doc: Doc, mentions: list[_Mention], assigned: dict[Label, _Mention]
) -> list[FieldResult]:
    hits: list[tuple[int, int, bool, Chunk]] = []
    for chunk in doc.chunks:
        if _skip(chunk, "negotiable", "current_ctc", "expected_ctc", "offered_ctc"):
            continue
        free = doc.free_text(chunk)
        for m in _NEGATIVE_NEGOTIABLE.finditer(free):
            hits.append((chunk.start + m.start(), chunk.start + m.end(), False, chunk))
        if chunk.key == "negotiable":
            answer = chunk.value.strip().casefold()
            if answer in ("no", "n", "false", "not negotiable", "non negotiable", "non-negotiable"):
                hits.append((chunk.start, chunk.end, False, chunk))
            else:
                hits.append((chunk.start, chunk.end, True, chunk))
            continue
        for m in _NEGOTIABLE.finditer(free):
            if any(
                chunk.start + m.start() >= s and chunk.start + m.start() < e for s, e, _, _ in hits
            ):
                continue
            hits.append((chunk.start + m.start(), chunk.start + m.end(), True, chunk))
    if not hits:
        return []
    results: dict[Label, FieldResult] = {}
    for start, end, value, chunk in sorted(hits):
        chunk_text = doc.text[chunk.start : chunk.end]
        in_chunk = [m for m in mentions if m.chunk is chunk and m.label is not None]
        has_notice_words = bool(_NOTICE_WORDS.search(chunk_text)) or chunk.key == "notice"
        if has_notice_words and not in_chunk:
            continue  # "30 days negotiable": about the notice period, not the salary
        target: _Mention | None = None
        how = ""
        if in_chunk:
            target = min(in_chunk, key=lambda m: min(abs(m.start - end), abs(m.end - start)))
            how = "next to the amount in the same item"
        else:
            earlier = [m for m in mentions if m.end <= start and m.label is not None]
            adjacent = [m for m in earlier if chunk.index - m.chunk.index <= 1]
            if adjacent:
                target = max(adjacent, key=lambda m: m.end)
                how = "right after that amount"
            elif len(assigned) == 1:
                target = next(iter(assigned.values()))
                how = "the only labelled salary in the text"
        doc.claim(start, end)
        if target is None or target.label is None:
            labels: list[Label] = list(assigned) or ["expected"]
            for lbl in labels:
                results.setdefault(
                    lbl,
                    ambiguous(
                        f"{lbl}_ctc_negotiable",
                        [Alternative(value, "Yes" if value else "No", f"Applies to {lbl} CTC")],
                        "'Negotiable' is not next to a salary: tick the CTC it refers to.",
                    ),
                )
            continue
        label = target.label
        word = "negotiable" if value else "not negotiable"
        confidence: Literal["high", "medium"] = (
            "high" if target.strength in ("key", "explicit", "pair") and in_chunk else "medium"
        )
        results[label] = found(
            f"{label}_ctc_negotiable",
            value,
            "Yes" if value else "No",
            confidence,
            f"'{word}' written {how}.",
        )
    return list(results.values())


# --- Notice period ----------------------------------------------------------------------------

_NOTICE_BEFORE = re.compile(
    r"(?:notice(?:\s+period)?|(?<![\w])np|n\.p\.?|join(?:ing)?(?:\s+(?:in|after|within|time))?|"
    r"available(?:\s+(?:in|after|from))?|serving(?:\s+notice(?:\s+period)?)?|lwd|"
    r"last\s+working\s+day|buy\s*out)\W*(?:is|of|:|-|=|in|after|within|for|only)?\W*$",
    re.IGNORECASE,
)
_NOTICE_AFTER = re.compile(
    r"^\W*(?:notice|np\b|n\.p|to\s+join|for\s+joining|(?:of\s+)?(?:notice\s+period))", re.IGNORECASE
)
_NOT_NOTICE_AFTER = re.compile(
    r"^\s*(?:a\s+week|per\s+week|/\s*week|working|leave|holiday|ago|old|of\s+(?:experience|exp)|"
    r"experience|exp\b|in\s+(?:a|the)\s+(?:week|role))",
    re.IGNORECASE,
)
_SERVING_RE = re.compile(
    r"(?<![\w])(?:currently\s+)?(?:serving|under|on)\s+(?:the\s+)?(?:notice(?:\s+period)?|np)|"
    r"(?<![\w])serving\s+(?:his|her|their)\s+notice|(?<![\w])resigned",
    re.IGNORECASE,
)
_LEFT_AFTER = re.compile(r"^\W*(?:days?\s+)?(?:left|remaining|more|to\s+go|balance)", re.IGNORECASE)


@dataclass(slots=True)
class _NoticeHit:
    start: int
    end: int
    quantity: Quantity
    labelled: bool
    keyed: bool
    kind: Literal["number", "immediate"]


def _notice_hits(doc: Doc) -> list[_NoticeHit]:
    hits: list[_NoticeHit] = []
    for chunk in doc.chunks:
        if _skip(chunk, "notice"):
            continue
        free = doc.free_text(chunk)
        keyed = chunk.key == "notice"
        for m in IMMEDIATE_RE.finditer(free):
            hits.append(
                _NoticeHit(
                    chunk.start + m.start(),
                    chunk.start + m.end(),
                    Quantity(Decimal(0), None, "Immediate joiner: zero days."),
                    True,
                    keyed,
                    "immediate",
                )
            )
        for m in NOTICE_RE.finditer(free):
            before = free[: m.start()]
            after = free[m.end() :]
            if _NOT_NOTICE_AFTER.match(after):
                continue
            unit = m.group("u")[0].casefold()
            labelled = keyed or bool(_NOTICE_BEFORE.search(before) or _NOTICE_AFTER.match(after))
            quantity = notice_from_match(m)
            if (
                not labelled
                and unit == "m"
                and re.search(rf"{YEAR_UNIT}\s*(?:and|&)?\s*$", before, re.IGNORECASE)
            ):
                continue  # "5 years 3 months": the months belong to the experience
            if not labelled and unit == "m":
                months = parse_number(m.group("n2") or m.group("n1")) or Decimal(0)
                if months > 3:
                    continue  # more likely experience: left for the experience extractor
                quantity = Quantity(quantity.value, quantity.low, quantity.note, assumed=True)
            hits.append(
                _NoticeHit(
                    chunk.start + m.start(),
                    chunk.start + m.end(),
                    quantity,
                    labelled,
                    keyed,
                    "number",
                )
            )
        if keyed and not any(h.start >= chunk.start and h.end <= chunk.end for h in hits):
            bare = re.fullmatch(rf"\s*(?P<n>{NUM})\s*", chunk.value)
            if bare:
                days = parse_number(bare.group("n")) or Decimal(0)
                hits.append(
                    _NoticeHit(
                        chunk.value_start,
                        chunk.end,
                        Quantity(
                            days, None, "A bare number after 'notice period' is read as days."
                        ),
                        True,
                        True,
                        "number",
                    )
                )
    return hits


def extract_notice(doc: Doc) -> list[FieldResult]:
    serving: tuple[int, int] | None = None
    for chunk in doc.chunks:
        if _skip(chunk, "notice"):
            continue
        m = _SERVING_RE.search(doc.free_text(chunk))
        if m:
            serving = (chunk.start + m.start(), chunk.start + m.end())
            break
    hits = _notice_hits(doc)
    if serving is not None:
        doc.claim(*serving)
    if not hits:
        if serving is None:
            return []
        return [
            FieldResult(
                field="notice_period_days",
                value=None,
                display=None,
                confidence="low",
                reason="The candidate is serving notice, but no days or last working day was given.",
                warning="Serving notice: add the days left (or the notice length) by hand.",
            )
        ]
    for hit in hits:
        doc.claim(hit.start, hit.end)
    labelled = [h for h in hits if h.labelled]
    pool = labelled or hits
    distinct: dict[Decimal, _NoticeHit] = {}
    for hit in pool:
        distinct.setdefault(hit.quantity.value, hit)
    if len(distinct) > 1:
        keyed_hits = [h for h in pool if h.keyed]
        if len({h.quantity.value for h in keyed_hits}) == 1:
            pool = keyed_hits
            distinct = {pool[0].quantity.value: pool[0]}
        else:
            options = [
                Alternative(int(v), _days_text(int(v)), "A notice period in the text")
                for v in distinct
            ]
            return [
                ambiguous(
                    "notice_period_days",
                    options,
                    f"{len(distinct)} different notice periods found: choose one.",
                )
            ]
    hit = next(iter(distinct.values()))
    days = int(hit.quantity.value)
    reasons: list[str] = []
    confidence: Literal["high", "medium", "low"] = "high" if hit.labelled else "medium"
    if hit.keyed:
        reasons.append("Labelled as notice period.")
    elif hit.kind == "immediate":
        reasons.append("Written as an immediate joiner.")
    elif hit.labelled:
        reasons.append("Written next to the word notice / NP / join.")
    elif hit.kind == "number":
        reasons.append("A number of days with no label is read as a notice period.")
    if hit.quantity.assumed:
        reasons.append("Months with no label are read as notice (1-3 months is typical).")
        confidence = "medium"
    if hit.quantity.note:
        reasons.append(hit.quantity.note)
    warning: str | None = None
    candidates: list[Alternative] = []
    if hit.quantity.low is not None:
        confidence = "medium"
        low = int(hit.quantity.low)
        mid = (low + days) // 2
        candidates = [
            Alternative(low, _days_text(low), "Lower end of the range"),
            Alternative(mid, _days_text(mid), "Midpoint of the range"),
            Alternative(days, _days_text(days), "Upper end of the range (filled)"),
        ]
        warning = f"Range {low}-{days} days: the maximum was filled. Choose the midpoint ({mid}) if you prefer."
    if serving is not None:
        reasons.append("The candidate is serving notice, so this is the time left.")
    if days > 365:
        confidence = "low"
        warning = (warning + " " if warning else "") + "More than 365 days: check the value."
    return [
        found(
            "notice_period_days",
            days,
            _days_text(days),
            confidence,
            " ".join(reasons),
            candidates=candidates,
            warning=warning,
        )
    ]


def _days_text(days: int) -> str:
    return "Immediate (0 days)" if days == 0 else f"{days} days"


# --- Experience -------------------------------------------------------------------------------

_TOTAL_LABEL = re.compile(
    r"(?:total|overall|work(?:ing)?|professional|industry|it)?\s*(?:experience|exp|yoe)\W*(?:of|is|:|-|=)?\W*$",
    re.IGNORECASE,
)
_EXP_AFTER = re.compile(
    r"^\s*(?:of\s+)?(?:total\s+|overall\s+|work\s+)?(?:experience|exp)\b", re.IGNORECASE
)
_SCOPED_AFTER = re.compile(
    r"^\s*(?:of\s+(?!exp)|in\s+|with\s+|on\s+|at\s+|as\s+(?:a|an)\s+|using\s+|working\s+(?:in|on|with))",
    re.IGNORECASE,
)
_NOT_EXPERIENCE_AFTER = re.compile(r"^\s*(?:old|of\s+age|back|ago|since|\+?\s*old)", re.IGNORECASE)
_TOTAL_WORD = re.compile(r"(?:total|overall)\s*(?:work\s+)?(?:experience|exp)?\W*$", re.IGNORECASE)


@dataclass(slots=True)
class _ExpHit:
    start: int
    end: int
    quantity: Quantity
    scope: Literal["total", "bare", "scoped", "fresher"]
    strong: bool  # "total"/"overall" or a key
    standalone: bool
    keyed: bool


def _experience_hits(doc: Doc) -> list[_ExpHit]:
    hits: list[_ExpHit] = []
    for chunk in doc.chunks:
        if _skip(chunk, "experience"):
            continue
        free = doc.free_text(chunk)
        keyed = chunk.key == "experience"
        covered: list[tuple[int, int]] = []

        def add(
            m: re.Match[str],
            quantity: Quantity,
            *,
            chunk: Chunk = chunk,
            free: str = free,
            keyed: bool = keyed,
            covered: list[tuple[int, int]] = covered,
        ) -> None:
            before, after = free[: m.start()], free[m.end() :]
            if _NOT_EXPERIENCE_AFTER.match(after):
                return
            labelled = keyed or bool(_TOTAL_LABEL.search(before) or _EXP_AFTER.match(after))
            scoped = (not labelled) and bool(_SCOPED_AFTER.match(after))
            scope: Literal["total", "bare", "scoped", "fresher"] = (
                "total" if labelled else "scoped" if scoped else "bare"
            )
            strong = keyed or bool(_TOTAL_WORD.search(before))
            body = free.strip()
            standalone = len(body) > 0 and (m.end() - m.start()) >= 0.8 * len(body)
            hits.append(
                _ExpHit(
                    chunk.start + m.start(),
                    chunk.start + m.end(),
                    quantity,
                    scope,
                    strong,
                    standalone,
                    keyed,
                )
            )
            covered.append((m.start(), m.end()))

        fresher = FRESHER_RE.search(free)
        if fresher:
            hits.append(
                _ExpHit(
                    chunk.start + fresher.start(),
                    chunk.start + fresher.end(),
                    Quantity(Decimal("0.0"), None, "Fresher: zero years."),
                    "fresher",
                    True,
                    True,
                    keyed,
                )
            )
            covered.append((fresher.start(), fresher.end()))
        for m in EXPERIENCE_RE.finditer(free):
            if any(not (m.end() <= a or m.start() >= b) for a, b in covered):
                continue
            add(m, experience_from_match(m))
        for m in YOE_RE.finditer(free):
            if any(not (m.end() <= a or m.start() >= b) for a, b in covered):
                continue
            add(m, Quantity(round_years(parse_number(m.group("y")) or Decimal(0))))
        for m in MONTHS_ONLY_RE.finditer(free):
            if any(not (m.end() <= a or m.start() >= b) for a, b in covered):
                continue
            months = parse_number(m.group("m2") or m.group("m1")) or Decimal(0)
            quantity = Quantity(
                round_years(months / 12), None, f"{float(months):g} months converted to years."
            )
            add(m, quantity)
        if keyed and not covered:
            bare = re.fullmatch(rf"\s*(?P<y>{NUM})\s*(?P<plus>\+)?\s*", chunk.value)
            if bare:
                years = parse_number(bare.group("y")) or Decimal(0)
                hits.append(
                    _ExpHit(
                        chunk.value_start,
                        chunk.end,
                        Quantity(
                            round_years(years),
                            None,
                            "A bare number after 'experience' is read as years.",
                        ),
                        "total",
                        True,
                        True,
                        True,
                    )
                )
    # "Experience 5" (no unit, no colon) in an unkeyed chunk.
    for m in re.finditer(
        rf"(?<![\w])(?:total\s+|overall\s+)?(?:experience|exp|yoe)\s*(?:of|is)?\s*(?P<y>{NUM})(?![\d.,]*\s*(?:lpa|l\b|k\b|cr|lakh|%|days?|months?|{MONTH_UNIT}))",
        doc.masked(),
        re.IGNORECASE,
    ):
        years = parse_number(m.group("y")) or Decimal(0)
        if any(not (m.end() <= h.start or m.start("y") >= h.end) for h in hits):
            continue
        hits.append(
            _ExpHit(
                m.start("y"),
                m.end("y"),
                Quantity(
                    round_years(years), None, "A bare number after 'experience' is read as years."
                ),
                "total",
                True,
                False,
                False,
            )
        )
    return hits


def extract_experience(doc: Doc) -> list[FieldResult]:
    hits = _experience_hits(doc)
    if not hits:
        return []
    for hit in hits:
        doc.claim(hit.start, hit.end)
    totals = [h for h in hits if h.scope in ("total", "fresher")]
    bare = [h for h in hits if h.scope == "bare"]
    scoped = [h for h in hits if h.scope == "scoped"]
    tier, scope_note = (
        (totals, "labelled as experience") if totals else (bare, "") if bare else (scoped, "scoped")
    )
    distinct: dict[Decimal, _ExpHit] = {}
    for hit in tier:
        distinct.setdefault(hit.quantity.value, hit)
    if len(distinct) > 1:
        strong = {h.quantity.value: h for h in tier if h.strong}
        if len(strong) == 1:
            distinct = strong
        else:
            options = [
                Alternative(float(v), f"{float(v):g} years", "An experience figure in the text")
                for v in distinct
            ]
            return [
                ambiguous(
                    "total_experience_years",
                    options,
                    f"{len(distinct)} different experience figures found "
                    "(for example per skill): which is the total?",
                )
            ]
    hit = next(iter(distinct.values()))
    years = hit.quantity.value
    if years > MAX_EXPERIENCE_YEARS:
        return [
            FieldResult(
                field="total_experience_years",
                value=None,
                confidence="low",
                reason=f"{float(years):g} years is above the 50-year limit.",
                warning=f"Experience of {float(years):g} years is above 50: check the figure.",
            )
        ]
    reasons: list[str] = []
    confidence: Literal["high", "medium", "low"]
    if hit.scope == "fresher":
        confidence = "high"
        reasons.append("Fresher / no experience means zero years.")
    elif hit.scope == "total":
        confidence = "high"
        reasons.append(
            "Labelled as experience." if hit.keyed else "Written next to the word experience."
        )
    elif hit.scope == "bare":
        confidence = "high" if hit.standalone else "medium"
        reasons.append(
            "A standalone 'N years' item is read as total experience."
            if hit.standalone
            else "A number of years with no label is read as total experience."
        )
    else:
        confidence = "low"
        reasons.append("The years are tied to a skill or employer, which may not be the total.")
    if hit.quantity.note:
        reasons.append(hit.quantity.note)
    warning: str | None = None
    candidates: list[Alternative] = []
    if hit.quantity.low is not None:
        confidence = "medium"
        low = hit.quantity.low
        mid = round_years((low + years) / 2)
        candidates = [
            Alternative(float(low), f"{float(low):g} years", "Lower end of the range"),
            Alternative(float(mid), f"{float(mid):g} years", "Midpoint of the range"),
            Alternative(float(years), f"{float(years):g} years", "Upper end of the range (filled)"),
        ]
        warning = f"Range {float(low):g}-{float(years):g} years: the maximum was filled. Choose the midpoint ({float(mid):g}) if you prefer."
    if scope_note == "scoped" and len(hits) > 1:
        warning = warning or "Only a skill-specific figure was found."
    return [
        found(
            "total_experience_years",
            float(years),
            f"{float(years):g} years",
            confidence,
            " ".join(reasons),
            candidates=candidates,
            warning=warning,
        )
    ]
