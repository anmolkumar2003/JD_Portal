"""Skill taxonomy: canonical names, synonyms ("JS" = "JavaScript") and text scanning."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "skills.json"

# Aliases that are ordinary words or single letters. They only count when they stand alone as an
# item in a list ("Python, Go, C") with the exact capitalization of the taxonomy entry.
AMBIGUOUS_ALIASES = frozenset({"c", "r", "go", "pr", "ip", "tf", "py", "ts", "ui"})

_TOKEN_EDGE = ".,;:!?\"'`*"
_SEPARATORS = re.compile(r"[,;:|\u2022\u00b7\u25aa\u25cf\u25e6\u2023()\[\]{}<>]")
_LIST_SPLIT = re.compile(r"[,;|\u2022\u00b7\u25aa\u25cf\u25e6\u2023/\n]")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    synonyms: tuple[str, ...]


@dataclass(frozen=True)
class SkillMention:
    name: str
    category: str
    count: int


def _clean_token(raw: str) -> str:
    token = raw.rstrip(_TOKEN_EDGE)
    # Keep a leading "." only for names like ".NET"; keep a trailing "+"/"#" (C++, C#).
    token = token.lstrip(_TOKEN_EDGE.replace(".", "")).lstrip("-\u2013\u2014")
    if token.startswith(".") and not token[1:2].isalpha():
        token = token.lstrip(".")
    return token.rstrip("-")


def _tokens(line: str) -> list[str]:
    """Split a line into lowercase tokens, keeping tech punctuation such as C++, .NET, CI/CD."""
    cleaned = _SEPARATORS.sub(" ", line.casefold())
    return [token for raw in cleaned.split() if (token := _clean_token(raw))]


def _key(text: str) -> str:
    return " ".join(_tokens(text))


class Taxonomy:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = skills
        self.by_name: dict[str, Skill] = {s.name: s for s in skills}
        self._alias: dict[str, Skill] = {}
        self.max_words = 1
        for skill in skills:
            for alias in (skill.name, *skill.synonyms):
                key = _key(alias)
                if not key:
                    continue
                # First entry wins when two skills share an alias (e.g. "GCP").
                self._alias.setdefault(key, skill)
                self.max_words = max(self.max_words, len(key.split()))

    def lookup(self, text: str) -> Skill | None:
        return self._alias.get(_key(text))

    def scan(self, text: str) -> dict[str, int]:
        """Count skill mentions per canonical name, in order of first appearance."""
        found: dict[str, int] = {}
        for line in text.splitlines():
            tokens = _tokens(line)
            index = 0
            while index < len(tokens):
                match = self._match_at(tokens, index)
                if match is None:
                    index += 1
                    continue
                matched, length = match
                for skill in matched:
                    found[skill.name] = found.get(skill.name, 0) + 1
                index += length
            self._scan_list_items(line, found)
        return found

    def _match_at(self, tokens: list[str], index: int) -> tuple[list[Skill], int] | None:
        for length in range(min(self.max_words, len(tokens) - index), 0, -1):
            phrase = " ".join(tokens[index : index + length])
            skill = self._alias.get(phrase)
            if skill is not None and phrase not in AMBIGUOUS_ALIASES:
                return [skill], length
        token = tokens[index]
        if "/" in token:  # "HTML/CSS" yields both parts
            parts = token.split("/")
            hits = [
                skill
                for part in parts
                if (skill := self._alias.get(part)) is not None and part not in AMBIGUOUS_ALIASES
            ]
            if hits:
                return hits, 1
        return None

    def _scan_list_items(self, line: str, found: dict[str, int]) -> None:
        """Ambiguous aliases (C, R, Go...) count only as stand-alone list items."""
        for item in _LIST_SPLIT.split(line):
            item = item.strip(" \t-\u2013\u2014*.")
            key = _key(item)
            if key not in AMBIGUOUS_ALIASES:
                continue
            skill = self._alias.get(key)
            if skill is None:
                continue
            exact = item == skill.name or item in skill.synonyms
            if exact or (item.isupper() and key in skill.synonyms):
                found[skill.name] = found.get(skill.name, 0) + 1


@lru_cache(maxsize=1)
def get_taxonomy() -> Taxonomy:
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    skills = [
        Skill(
            name=str(item["name"]),
            category=str(item.get("category", "")),
            synonyms=tuple(str(s) for s in item.get("synonyms", [])),
        )
        for item in raw
    ]
    return Taxonomy(skills)


def canonicalize(skill: str) -> str:
    """Canonical taxonomy name for a skill or synonym; unknown skills are returned tidied."""
    tidy = _WHITESPACE.sub(" ", skill).strip()
    known = get_taxonomy().lookup(tidy)
    return known.name if known is not None else tidy


def is_known_skill(skill: str) -> bool:
    return get_taxonomy().lookup(skill) is not None


def skill_category(skill: str) -> str | None:
    known = get_taxonomy().lookup(skill)
    return known.category if known is not None else None


def find_skills_in_text(text: str) -> list[str]:
    """Canonical names of every taxonomy skill mentioned in the text, in order of appearance."""
    return list(get_taxonomy().scan(text))


def find_skill_mentions(text: str) -> list[SkillMention]:
    taxonomy = get_taxonomy()
    return [
        SkillMention(name=name, category=taxonomy.by_name[name].category, count=count)
        for name, count in taxonomy.scan(text).items()
    ]


def skills_in_list(text: str) -> list[str]:
    """Skills in a delimited list (a Skills section). Unlike scanning, this treats each item as
    a unit, so "Go" and "R" count here while they would be ignored inside a sentence."""
    seen: dict[str, None] = {}
    for line in text.splitlines():
        # Drop a leading label such as "Languages:".
        body = line.split(":", 1)[1] if ":" in line and len(line.split(":", 1)[0]) < 30 else line
        for item in _LIST_SPLIT.split(body):
            item = item.strip(" \t-\u2013\u2014*.")
            skill = get_taxonomy().lookup(item) if item else None
            if skill is not None:
                seen.setdefault(skill.name)
    return list(seen)


def skill_in_text(skill: str, text: str) -> bool:
    """Is a single skill (any synonym) mentioned in the text? Works for skills outside the
    taxonomy by falling back to a word-boundary search."""
    known = get_taxonomy().lookup(skill)
    if known is not None:
        return known.name in get_taxonomy().scan(text)
    pattern = r"(?<![\w+#])" + re.escape(skill.strip()) + r"(?![\w+#])"
    return re.search(pattern, text, re.IGNORECASE) is not None
