"""Loaders for the JSON rule dictionaries in `data/` (cached; read once per process)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"


def _load(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


_SPACE_LABEL_HEADS = frozenset(
    {
        "current",
        "present",
        "total",
        "notice",
        "expected",
        "expecting",
        "offered",
        "last",
        "full",
        "first",
        "contact",
        "mobile",
        "email",
        "e-mail",
        "home",
        "preferred",
    }
)


def _alias_pattern(words: list[str]) -> str:
    """Regex alternation, longest first, with flexible whitespace inside multi-word entries."""
    ordered = sorted(set(words), key=lambda w: (-len(w), w))
    return "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in ordered)


@dataclass(frozen=True, slots=True)
class Place:
    name: str
    kind: str  # city | state | country
    state: str | None = None
    country: str | None = None
    international: bool = False


@dataclass(frozen=True, slots=True)
class Company:
    name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Rules:
    key_aliases: dict[str, str]  # normalized alias -> canonical key
    key_re: re.Pattern[str]
    key_space_re: re.Pattern[str]  # multi-word labels written without a colon
    title_heads: frozenset[str]
    title_modifiers: frozenset[str]
    title_acronyms: dict[str, str]  # lower -> display
    company_suffixes: frozenset[str]
    companies: tuple[Company, ...]
    company_re: re.Pattern[str]
    company_by_alias: dict[str, Company]
    departments: frozenset[str]
    non_name_words: frozenset[str]
    first_names: frozenset[str]
    sources: dict[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class Gazetteer:
    places: dict[str, Place]  # normalized alias -> place
    place_re: re.Pattern[str]
    weak_aliases: frozenset[str]
    state_of_city: dict[str, str]


def norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold().strip())


@lru_cache(maxsize=1)
def get_rules() -> Rules:
    raw = _load("rules.json")
    key_aliases: dict[str, str] = {}
    for canonical, aliases in raw["keys"].items():
        for alias in aliases:
            key_aliases.setdefault(norm_key(alias), canonical)
    # `name:` style labels: the label, optional spaces, then a colon/equals/dash separator.
    key_re = re.compile(
        rf"^\s*(?P<key>{_alias_pattern(list(key_aliases))})\s*(?P<sep>[:=]|\s-\s|-)\s*(?P<val>.*)$",
        re.IGNORECASE | re.DOTALL,
    )
    # "current location Pune", "notice period 30 days", "NP 45": a label with no colon at all. Only
    # column-style labels qualify: sentence openers such as "working for" or "years of experience"
    # must keep going through the sentence rules.
    spaced = [
        a for a in key_aliases if a == "np" or (" " in a and a.split()[0] in _SPACE_LABEL_HEADS)
    ]
    key_space_re = re.compile(
        rf"^\s*(?P<key>{_alias_pattern(spaced)})\s+(?:(?:is|are|was|of)\s+)?(?P<val>\S.*)$",
        re.IGNORECASE | re.DOTALL,
    )
    companies = tuple(Company(c["name"], tuple(c["aliases"])) for c in raw["known_companies"])
    by_alias: dict[str, Company] = {}
    for company in companies:
        for alias in (company.name, *company.aliases):
            by_alias.setdefault(norm_key(alias), company)
    company_re = re.compile(
        rf"(?<![\w&])(?:{_alias_pattern(list(by_alias))})(?![\w&])", re.IGNORECASE
    )
    names = _load("first_names.json")["names"]
    return Rules(
        key_aliases=key_aliases,
        key_re=key_re,
        key_space_re=key_space_re,
        title_heads=frozenset(raw["title_heads"]),
        title_modifiers=frozenset(raw["title_modifiers"]),
        title_acronyms={a.casefold(): a for a in raw["title_acronyms"]},
        company_suffixes=frozenset(raw["company_suffixes"]),
        companies=companies,
        company_re=company_re,
        company_by_alias=by_alias,
        departments=frozenset(raw["departments"]),
        non_name_words=frozenset(raw["non_name_words"]),
        first_names=frozenset(names),
        sources={k: tuple(v) for k, v in raw["sources"].items()},
    )


@lru_cache(maxsize=1)
def get_gazetteer() -> Gazetteer:
    raw = _load("locations.json")
    places: dict[str, Place] = {}
    state_of_city: dict[str, str] = {}
    for city in raw["cities"]:
        place = Place(
            name=city["name"],
            kind="city",
            state=city["state"] if not city.get("international") else None,
            country=city["state"] if city.get("international") else "India",
            international=bool(city.get("international")),
        )
        state_of_city[city["name"]] = city["state"]
        for alias in (city["name"], *city["aliases"]):
            places.setdefault(norm_key(alias), place)
    for state in raw["states"]:
        place = Place(name=state["name"], kind="state", country="India")
        for alias in (state["name"], *state["aliases"]):
            places.setdefault(norm_key(alias), place)
    for country in raw["countries"]:
        place = Place(name=country["name"], kind="country")
        for alias in (country["name"], *country["aliases"]):
            places.setdefault(norm_key(alias), place)
    pattern = _alias_pattern(list(places))
    # Word-ish boundaries that also treat "&" and "." inside names (J&K, St.) as part of a word.
    place_re = re.compile(rf"(?<![\w&])(?:{pattern})(?![\w&])", re.IGNORECASE)
    return Gazetteer(
        places=places,
        place_re=place_re,
        weak_aliases=frozenset(norm_key(a) for a in raw["weak_aliases"]),
        state_of_city=state_of_city,
    )
