"""Normalizers: phone, experience (years), notice period (days) and salary (amount + unit).

Each `normalize_*` function takes a short phrase ("5 yrs 3 months", "80k per month") and returns
a structured value, or None. The extractors reuse the same compiled patterns on longer text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal

# One number: Indian (8,00,000), western (800,000), plain or decimal.
NUM = r"(?:\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
_ONE = Decimal(1)
_TENTH = Decimal("0.1")


def parse_number(raw: str) -> Decimal | None:
    cleaned = raw.replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _num(raw: str | None) -> Decimal:
    value = parse_number(raw) if raw else None
    return value if value is not None else Decimal(0)


# --- Phone ------------------------------------------------------------------------------------

# Country calling codes we split off (longest first). Anything else is kept as "+<digits>".
_CALLING_CODES = (
    "971",
    "966",
    "974",
    "973",
    "968",
    "972",
    "880",
    "977",
    "975",
    "234",
    "254",
    "91",
    "92",
    "94",
    "60",
    "61",
    "62",
    "63",
    "65",
    "81",
    "82",
    "86",
    "1",
    "7",
    "20",
    "27",
    "30",
    "31",
    "32",
    "33",
    "34",
    "39",
    "40",
    "41",
    "43",
    "44",
    "45",
    "46",
    "47",
    "48",
    "49",
    "52",
    "55",
    "64",
    "66",
    "84",
    "90",
    "98",
)
_CALLING_CODES_SORTED = sorted(set(_CALLING_CODES), key=lambda c: (-len(c), c))
PhoneKind = Literal["indian_mobile", "international", "unclear"]


@dataclass(frozen=True, slots=True)
class NormalizedPhone:
    display: str  # "+91 98765 43210"
    digits: str  # "919876543210"
    kind: PhoneKind
    note: str


def _split_calling_code(digits: str) -> tuple[str, str]:
    for code in _CALLING_CODES_SORTED:
        if digits.startswith(code) and len(digits) - len(code) >= 6:
            return code, digits[len(code) :]
    return digits[:2], digits[2:]


def normalize_phone(raw: str) -> NormalizedPhone | None:
    """Standard format: "+91 98765 43210" for India, "+<code> <number>" elsewhere.

    10 digits starting 6-9 are taken as an Indian mobile; other bare numbers are not guessed.
    """
    text = raw.strip()
    digits = re.sub(r"\D", "", text)
    if not 8 <= len(digits) <= 15:
        return None
    international = text.startswith("+") or text.startswith("00") or text.startswith("(+")
    if international:
        digits = digits[2:] if text.startswith("00") else digits
        if digits.startswith("91") and len(digits) == 12 and digits[2] in "6789":
            return _indian(digits[2:], "Written with the +91 country code.")
        if digits.startswith("910") and len(digits) == 13 and digits[3] in "6789":
            return _indian(digits[3:], "Written with +91 and a leading 0 (removed).")
        code, rest = _split_calling_code(digits)
        if code == "1" and len(rest) == 10:  # North America: +1 415 555 2671
            rest = f"{rest[:3]} {rest[3:6]} {rest[6:]}"
        return NormalizedPhone(
            f"+{code} {rest}", digits, "international", "Written with an international prefix."
        )
    if len(digits) == 10 and digits[0] in "6789":
        return _indian(digits, "10 digits starting 6-9: read as an Indian mobile number.")
    if len(digits) == 11 and digits[0] == "0" and digits[1] in "6789":
        return _indian(digits[1:], "Leading 0 removed: read as an Indian mobile number.")
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return _indian(digits[2:], "Starts with 91: read as +91 and a 10-digit Indian mobile.")
    if len(digits) == 10:
        return NormalizedPhone(
            digits,
            digits,
            "unclear",
            "10 digits that do not start with 6-9: not assumed to be an Indian mobile.",
        )
    return NormalizedPhone(
        digits, digits, "unclear", "No country code given, so the number was kept as typed."
    )


def _indian(ten_digits: str, note: str) -> NormalizedPhone:
    return NormalizedPhone(
        f"+91 {ten_digits[:5]} {ten_digits[5:]}", "91" + ten_digits, "indian_mobile", note
    )


# --- Quantities: experience and notice --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Quantity:
    """A parsed number. For a range ("3-5 years") `value` is the maximum and `low` the minimum."""

    value: Decimal
    low: Decimal | None = None
    note: str | None = None
    # True when the unit was guessed (a bare "2 months" is read as a notice period).
    assumed: bool = False

    @property
    def midpoint(self) -> Decimal | None:
        if self.low is None:
            return None
        return (self.low + self.value) / 2


def round_years(years: Decimal) -> Decimal:
    """One decimal, halves rounded up (5.25 -> 5.3): the form and database hold one decimal."""
    return years.quantize(_TENTH, rounding=ROUND_HALF_UP)


YEAR_UNIT = r"(?:years?|yrs?|yr|y)(?![a-z])"
MONTH_UNIT = r"(?:months?|mos?|mnths?|mths?)(?![a-z])"
EXPERIENCE_RE = re.compile(
    rf"(?<![\w.])(?P<y1>{NUM})(?:\s*(?:-|to)\s*(?P<y2>{NUM}))?\s*(?P<plus>\+)?\s*{YEAR_UNIT}"
    rf"(?:\s*(?:and|&)?\s*(?P<m>{NUM})\s*{MONTH_UNIT})?",
    re.IGNORECASE,
)
YOE_RE = re.compile(rf"(?<![\w.])(?P<y>{NUM})\s*\+?\s*yoe(?![a-z])", re.IGNORECASE)
MONTHS_ONLY_RE = re.compile(
    rf"(?<![\w.])(?P<m1>{NUM})(?:\s*(?:-|to)\s*(?P<m2>{NUM}))?\s*{MONTH_UNIT}", re.IGNORECASE
)
FRESHER_RE = re.compile(
    r"(?<![\w])(?:freshers?|fresh\s+(?:graduates?|grads?)|no\s+(?:work\s+|prior\s+)?experience|"
    r"zero\s+experience|nil\s+experience|0\s*(?:years?|yrs?)(?:\s+of)?(?:\s+experience)?)(?![a-z])"
    r"(?!\s*(?:and\s*|&\s*)?\d)",  # "0 years 8 months" is not a fresher
    re.IGNORECASE,
)
BARE_YEARS_RE = re.compile(
    rf"^\s*(?P<y1>{NUM})(?:\s*(?:-|to)\s*(?P<y2>{NUM}))?\s*(?P<plus>\+)?\s*$"
)
MAX_EXPERIENCE_YEARS = Decimal(50)


def experience_from_match(match: re.Match[str]) -> Quantity:
    y1 = _num(match.group("y1"))
    y2raw = match.groupdict().get("y2")
    months = _num(match.groupdict().get("m")) / 12 if match.groupdict().get("m") else Decimal(0)
    if y2raw:
        high = round_years(_num(y2raw) + months)
        low = round_years(y1)
        if low > high:
            low, high = high, low
        return Quantity(
            high, low, f"Range {float(low):g}-{float(high):g} years: the maximum was used."
        )
    note = "'+' read as the plain number." if match.groupdict().get("plus") else None
    if months:
        note = f"{float(months * 12):g} extra months converted to a decimal year."
    return Quantity(round_years(y1 + months), None, note)


def normalize_experience(text: str) -> Quantity | None:
    """Total experience in years as a decimal: "5 yrs 3 months" -> 5.3, "fresher" -> 0."""
    if FRESHER_RE.search(text):
        return Quantity(Decimal("0.0"), None, "Fresher: zero years.")
    match = EXPERIENCE_RE.search(text)
    if match:
        return experience_from_match(match)
    yoe = YOE_RE.search(text)
    if yoe:
        return Quantity(round_years(_num(yoe.group("y"))))
    months = MONTHS_ONLY_RE.search(text)
    if months:
        high = _num(months.group("m2") or months.group("m1"))
        return Quantity(round_years(high / 12), None, "Months converted to years.", assumed=True)
    bare = BARE_YEARS_RE.match(text)
    if bare:
        high = _num(bare.group("y2") or bare.group("y1"))
        low = _num(bare.group("y1")) if bare.group("y2") else None
        return Quantity(round_years(high), None if low is None else round_years(low))
    return None


NOTICE_UNIT = r"(?:days?|d|weeks?|wks?|months?|mos?|mths?)(?![a-z])"
NOTICE_RE = re.compile(
    rf"(?<![\w.])(?P<n1>{NUM})(?:\s*(?:-|to)\s*(?P<n2>{NUM}))?\s*(?P<u>{NOTICE_UNIT})",
    re.IGNORECASE,
)
IMMEDIATE_RE = re.compile(
    r"(?<![\w])(?:immediate(?:ly)?(?:\s+(?:joiner|joining|join|availability|available|notice))?|"
    r"(?:can|ready\s+to|able\s+to|will)\s+join\s+immediately|join\s+immediately|"
    r"available\s+immediately|no\s+notice(?:\s+period)?|nil\s+notice(?:\s+period)?|"
    r"zero\s+notice(?:\s+period)?|0\s+days?\s+notice)(?![a-z])"
    r"(?!\s+(?:family|manager|supervisor|boss|reporting|team|lead))",
    re.IGNORECASE,
)
_UNIT_DAYS = {"d": 30, "w": 7, "m": 30}  # keyed by first letter of the unit


def to_days(amount: Decimal, unit: str) -> int:
    per = {"d": Decimal(1), "w": Decimal(7), "m": Decimal(30)}[unit[0].casefold()]
    return int((amount * per).quantize(_ONE, rounding=ROUND_HALF_UP))


def notice_from_match(match: re.Match[str]) -> Quantity:
    unit = match.group("u")
    first = _num(match.group("n1"))
    second = match.group("n2")
    if second:
        high = to_days(_num(second), unit)
        low = to_days(first, unit)
        if low > high:
            low, high = high, low
        return Quantity(
            Decimal(high), Decimal(low), f"Range {low}-{high} days: the maximum was used."
        )
    days = to_days(first, unit)
    note = None
    if unit[0].casefold() == "m":
        note = f"{float(first):g} month(s) counted as {days} days (30 days a month)."
    elif unit[0].casefold() == "w":
        note = f"{float(first):g} week(s) counted as {days} days."
    return Quantity(Decimal(days), None, note)


def normalize_notice(text: str) -> Quantity | None:
    """Notice period in days: "2 months" -> 60, "immediate" -> 0, "30 days" -> 30."""
    if IMMEDIATE_RE.search(text):
        return Quantity(Decimal(0), None, "Immediate joiner: zero days.")
    match = NOTICE_RE.search(text)
    if match:
        return notice_from_match(match)
    return None


# --- Salary -----------------------------------------------------------------------------------

Unit = Literal["pa", "pm"]
_CURRENCIES = {
    "\u20b9": "INR",
    "rs": "INR",
    "rs.": "INR",
    "inr": "INR",
    "rupee": "INR",
    "rupees": "INR",
    "$": "USD",
    "us$": "USD",
    "usd": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "\u00a3": "GBP",
    "gbp": "GBP",
    "pound": "GBP",
    "pounds": "GBP",
    "\u20ac": "EUR",
    "eur": "EUR",
    "euro": "EUR",
    "euros": "EUR",
}
_SCALES: dict[str, tuple[Decimal, Unit | None]] = {
    "lpa": (Decimal(100_000), "pa"),
    "lpm": (Decimal(100_000), "pm"),
    "lakh": (Decimal(100_000), None),
    "lakhs": (Decimal(100_000), None),
    "lac": (Decimal(100_000), None),
    "lacs": (Decimal(100_000), None),
    "lk": (Decimal(100_000), None),
    "lks": (Decimal(100_000), None),
    "l": (Decimal(100_000), None),
    "cr": (Decimal(10_000_000), None),
    "crore": (Decimal(10_000_000), None),
    "crores": (Decimal(10_000_000), None),
    "k": (Decimal(1000), None),
    "thousand": (Decimal(1000), None),
}
_LAKH_CRORE = frozenset({"lakh", "lakhs", "lac", "lacs", "lk", "lks", "l", "cr", "crore", "crores"})

_CUR_PRE = r"(?:\u20b9|(?<![a-z])rs\.?|inr|us\$|usd|\$|gbp|\u00a3|eur|\u20ac)"
_CUR_POST = r"(?:inr|usd|eur|gbp|rs\.?|rupees?|dollars?|euros?|pounds?)"
SCALE = r"(?:lpa|lpm|lakhs?|lacs?|lks?|crores?|cr|thousand|k|l)(?![a-z])"
_PA = r"(?:p\.?\s?a\.?|per\s+an+um|per\s+(?:year|yr)|yearly|annual(?:ly)?|/\s?(?:yr|year|annum|pa))(?![a-z])"
_PM = r"(?:p\.?\s?m\.?|per\s+(?:month|mo|mth)|monthly|/\s?(?:month|mo|mth|pm|m))(?![a-z])"
MONEY_RE = re.compile(
    rf"(?<![\w.,])(?P<cur1>{_CUR_PRE})?\s*(?P<n1>{NUM})\s*(?P<s1>{SCALE})?"
    rf"(?:\s*(?:-|to)\s*(?P<cur1b>{_CUR_PRE})?\s*(?P<n2>{NUM})\s*(?P<s2>{SCALE})?)?"
    rf"(?:\s*(?P<cur2>{_CUR_POST})(?![a-z]))?(?:\s*/-)?"
    rf"(?:\s*(?P<pa>{_PA})|\s*(?P<pm>{_PM}))?",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class MoneyValue:
    amount: Decimal  # absolute amount, e.g. 800000
    currency: str
    unit: Unit
    # Why the unit or scale was guessed, or None when the text said it outright.
    assumed: str | None = None


@dataclass(frozen=True, slots=True)
class Money:
    """One salary reading. For a range, `value` is the maximum and `low` the minimum."""

    value: MoneyValue
    low: MoneyValue | None = None

    @property
    def midpoint(self) -> MoneyValue | None:
        if self.low is None:
            return None
        mid = ((self.low.amount + self.value.amount) / 2).quantize(Decimal("0.01"))
        return MoneyValue(mid, self.value.currency, self.value.unit, self.value.assumed)


def _currency(raw: str | None) -> str | None:
    return _CURRENCIES.get(raw.casefold()) if raw else None


def _unit_for(
    amount: Decimal, scale: str | None, currency: str, period: Unit | None
) -> tuple[Unit, str | None]:
    if period is not None:
        return period, None
    key = scale.casefold() if scale else None
    if key is not None:
        implied = _SCALES[key][1]
        if implied is not None:
            return implied, None
        if key in _LAKH_CRORE:
            return "pa", "Lakh and crore amounts are read as per annum unless stated."
    if currency == "INR":
        if amount < 150_000:
            return "pm", "An amount under 1.5 lakh with no unit is read as per month."
        reason = "No unit given: read as per annum."
        return "pa", reason if amount < 300_000 else None
    if amount >= 20_000:
        return "pa", None
    return "pm", "A small amount with no unit is read as per month."


def make_money(
    number: str,
    scale: str | None,
    currency: str,
    period: Unit | None,
    *,
    bare_lakhs: bool = False,
) -> MoneyValue:
    amount = _num(number)
    reason: str | None = None
    if scale:
        amount *= _SCALES[scale.casefold()][0]
    elif bare_lakhs and amount < 1000:
        # "current 8, expected 12": a small bare number next to a CTC label means lakhs.
        amount *= Decimal(100_000)
        scale = "lpa"
        reason = "A small number next to a CTC label is read as lakhs per annum."
    unit, unit_reason = _unit_for(amount, scale, currency, period)
    return MoneyValue(amount.quantize(Decimal("0.01")), currency, unit, reason or unit_reason)


def money_from_match(match: re.Match[str], *, default_currency: str = "INR") -> Money | None:
    """Turn a MONEY_RE match into a salary, or None when it is just a number (no unit/currency)."""
    groups = match.groupdict()
    currency = _currency(groups["cur1"]) or _currency(groups["cur1b"]) or _currency(groups["cur2"])
    period: Unit | None = "pa" if groups["pa"] else "pm" if groups["pm"] else None
    s1, s2 = groups["s1"], groups["s2"]
    if groups["n2"]:
        s1 = s1 or s2  # "12-15 LPA": the unit written once applies to both ends
        s2 = s2 or s1
    amount_hint = _num(groups["n2"] or groups["n1"])
    has_unit = bool(s1 or s2 or currency)
    if not has_unit and not (period and amount_hint >= 1000):
        return None
    cur = currency or default_currency
    high_n = groups["n2"] or groups["n1"]
    high = make_money(high_n, s2 if groups["n2"] else s1, cur, period)
    if not groups["n2"]:
        return Money(high)
    low = make_money(groups["n1"], s1, cur, period)
    if low.amount > high.amount:
        low, high = high, low
    return Money(high, low)


def normalize_salary(text: str) -> Money | None:
    """First salary in a phrase: "8 LPA", "80k per month", "12-15 lakh", "$120k", "8,00,000"."""
    for match in MONEY_RE.finditer(text):
        money = money_from_match(match)
        if money is not None:
            return money
    bare = re.fullmatch(rf"\s*(?P<n1>{NUM})\s*", text)
    if bare:
        return Money(make_money(bare.group("n1"), None, "INR", None))
    return None


def amount_json(amount: Decimal) -> int | float:
    return int(amount) if amount == amount.to_integral_value() else float(amount)


def indian_group(value: int) -> str:
    """1200000 -> "12,00,000"."""
    digits = str(abs(value))
    if len(digits) <= 3:
        return ("-" if value < 0 else "") + digits
    head, tail = digits[:-3], digits[-3:]
    parts: list[str] = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ("-" if value < 0 else "") + ",".join([*parts, tail])


_SYMBOLS = {"INR": "\u20b9", "USD": "$", "GBP": "\u00a3", "EUR": "\u20ac"}


def format_money(value: MoneyValue) -> str:
    """ "8 LPA (₹8,00,000 per annum)" / "₹80,000 per month" / "$120,000 per annum"."""
    whole = int(value.amount.to_integral_value(rounding=ROUND_HALF_UP))
    grouped = indian_group(whole) if value.currency == "INR" else f"{whole:,}"
    symbol = _SYMBOLS.get(value.currency)
    shown = f"{symbol}{grouped}" if symbol else f"{value.currency} {grouped}"
    per = "per annum" if value.unit == "pa" else "per month"
    text = f"{shown} {per}"
    if value.currency == "INR" and value.unit == "pa" and value.amount >= 100_000:
        lakhs = float(value.amount / 100_000)
        text = f"{float(lakhs):g} LPA ({text})"
    return text
