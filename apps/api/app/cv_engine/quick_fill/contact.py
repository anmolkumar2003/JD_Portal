"""Email, phone and URL (LinkedIn / portfolio) extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.cv_engine.quick_fill.common import ambiguous, found
from app.cv_engine.quick_fill.normalize import NormalizedPhone, normalize_phone
from app.cv_engine.quick_fill.text import Chunk, Doc
from app.cv_engine.quick_fill.types import Alternative, Confidence, FieldResult

EMAIL_RE = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])"
)
# Runs of digit groups ("+91 98765 43210", "(415) 555-2671"); windows of it are tested below.
PHONE_RUN_RE = re.compile(r"(?<![\w@.])(?:\+\s?|00\s?)?\(?\d[\d\s().-]{6,28}\d(?![\w@])")
_GROUP_RE = re.compile(r"\+?\(?\d+\)?")

URL_RE = re.compile(
    r"(?<![\w@./-])(?P<url>(?:https?://)?(?:www\.)?(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,24}"
    r"(?::\d+)?(?:/[^\s,;<>\"'()]*)?)",
    re.IGNORECASE,
)
_KNOWN_SITES = frozenset(
    {
        "linkedin.com",
        "github.com",
        "gitlab.com",
        "bitbucket.org",
        "behance.net",
        "dribbble.com",
        "medium.com",
        "kaggle.com",
        "stackoverflow.com",
        "leetcode.com",
        "hackerrank.com",
        "codepen.io",
        "figma.com",
        "notion.site",
    }
)
_SLUG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_%-]{2,99}")


# --- Email ------------------------------------------------------------------------------------


@dataclass(slots=True)
class _Hit:
    value: str
    start: int
    end: int
    keyed: bool


def extract_email(doc: Doc) -> list[FieldResult]:
    hits: list[_Hit] = []
    for chunk in doc.chunks:
        if chunk.key in ("ignore",):
            continue
        for m in EMAIL_RE.finditer(doc.free_text(chunk)):
            hits.append(
                _Hit(
                    m.group(0).lower(),
                    chunk.start + m.start(),
                    chunk.start + m.end(),
                    chunk.key == "email",
                )
            )
    if not hits:
        return []
    for hit in hits:
        doc.claim(hit.start, hit.end)
    distinct: dict[str, _Hit] = {}
    for hit in hits:
        known = distinct.get(hit.value)
        if known is None or (hit.keyed and not known.keyed):
            distinct[hit.value] = hit
    if len(distinct) == 1:
        (only,) = distinct.values()
        reason = "Labelled as email." if only.keyed else "Looks like an email address."
        return [found("email", only.value, only.value, "high", reason)]
    keyed = [h for h in distinct.values() if h.keyed]
    if len(keyed) == 1:
        return [
            found(
                "email",
                keyed[0].value,
                keyed[0].value,
                "medium",
                "Labelled as email; other addresses in the text were left out.",
                warning=f"{len(distinct)} email addresses found; the labelled one was used.",
            )
        ]
    options = [
        Alternative(h.value, h.value, "An email address in the text") for h in distinct.values()
    ]
    return [ambiguous("email", options, f"{len(distinct)} email addresses found: choose one.")]


# --- Phone ------------------------------------------------------------------------------------


def _windows(run: str) -> list[tuple[str, int, int]]:
    """Candidate phone numbers inside a run of digit groups, longest first, with their offsets.

    "411001 9876543210" is a pincode followed by a number: the pincode is dropped by trying
    shorter windows of the groups.
    """
    groups = list(_GROUP_RE.finditer(run))
    spans = [(i, j) for i in range(len(groups)) for j in range(i + 1, len(groups) + 1)]
    spans.sort(key=lambda ij: (-(ij[1] - ij[0]), ij[0]))
    return [
        (" ".join(g.group(0) for g in groups[i:j]), groups[i].start(), groups[j - 1].end())
        for i, j in spans
    ]


def _good(parsed: NormalizedPhone, window: str) -> bool:
    digits = parsed.digits
    has_prefix = window.lstrip().startswith(("+", "(+", "00"))
    if parsed.kind == "unclear":
        return 10 <= len(digits) <= 15
    return has_prefix or len(digits) >= 10


@dataclass(slots=True)
class _PhoneHit:
    phone: NormalizedPhone
    start: int
    end: int
    keyed: bool


_KIND_RANK = {"indian_mobile": 0, "international": 1, "unclear": 2}


def _best_window(run: str) -> tuple[NormalizedPhone, int, int] | None:
    """The most phone-like window of a digit run: Indian mobile > prefixed > anything, then longest."""
    prefixed = run.lstrip().startswith(("+", "(+", "00"))
    first = _GROUP_RE.search(run)
    first_start = first.start() if first else 0
    scored: list[tuple[tuple[int, int, int], NormalizedPhone, int, int]] = []
    for index, (window, lo, hi) in enumerate(_windows(run)):
        parsed = normalize_phone(window)
        if parsed is None or not _good(parsed, window):
            continue
        # With a +/00 prefix the number starts at the prefix ("+44 7911 123456" is not 7911...).
        starts_at_prefix = lo == first_start
        rank = (0 if (not prefixed or starts_at_prefix) else 1, _KIND_RANK[parsed.kind], index)
        scored.append((rank, parsed, lo, hi))
    if not scored:
        return None
    _, parsed, lo, hi = min(scored, key=lambda item: item[0])
    return parsed, lo, hi


def _phone_hits(doc: Doc, chunk: Chunk) -> list[_PhoneHit]:
    free = doc.free_text(chunk)
    hits: list[_PhoneHit] = []
    for m in PHONE_RUN_RE.finditer(free):
        best = _best_window(m.group(0))
        if best is None:
            continue
        parsed, lo, hi = best
        base = chunk.start + m.start()
        hits.append(_PhoneHit(parsed, base + lo, base + hi, chunk.key == "phone"))
    return hits


def extract_phone(doc: Doc) -> list[FieldResult]:
    hits: list[_PhoneHit] = []
    for chunk in doc.chunks:
        if chunk.key in ("ignore", "alt_phone"):
            continue
        hits.extend(_phone_hits(doc, chunk))
    if not hits:
        return []
    for hit in hits:
        doc.claim(hit.start, hit.end)
    distinct: dict[str, _PhoneHit] = {}
    for hit in hits:
        key = hit.phone.digits[-10:]
        known = distinct.get(key)
        if known is None or (hit.keyed and not known.keyed):
            distinct[key] = hit
    if len(distinct) == 1:
        (only,) = distinct.values()
        return [_phone_result(only)]
    keyed = [h for h in distinct.values() if h.keyed]
    if len(keyed) == 1:
        result = _phone_result(keyed[0])
        result.warning = f"{len(distinct)} phone numbers found; the labelled one was used."
        return [result]
    options = [
        Alternative(h.phone.display, h.phone.display, h.phone.note) for h in distinct.values()
    ]
    return [ambiguous("phone", options, f"{len(distinct)} phone numbers found: choose one.")]


def _phone_result(hit: _PhoneHit) -> FieldResult:
    phone = hit.phone
    confidence: Confidence = (
        ("medium" if hit.keyed else "low") if phone.kind == "unclear" else "high"
    )
    reason = ("Labelled as a phone number. " if hit.keyed else "") + phone.note
    return found("phone", phone.display, phone.display, confidence, reason.strip())


# --- URLs -------------------------------------------------------------------------------------


def _host_and_path(url: str) -> tuple[str, str]:
    bare = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    host, _, path = bare.partition("/")
    host = host.split(":")[0].casefold()
    host = host.removeprefix("www.")
    return host, path


def _with_scheme(url: str) -> str:
    return url if re.match(r"https?://", url, re.IGNORECASE) else f"https://{url}"


def _linkedin_profile(host: str, path: str) -> str | None:
    if host not in ("linkedin.com", "in.linkedin.com") and not host.endswith(".linkedin.com"):
        return None
    parts = [p for p in path.split("?", maxsplit=1)[0].split("/") if p]
    if len(parts) >= 2 and parts[0].casefold() in ("in", "pub"):
        return f"https://www.linkedin.com/{parts[0].casefold()}/{parts[1]}"
    return None


def extract_urls(doc: Doc) -> list[FieldResult]:
    linkedin: dict[str, tuple[int, int, bool]] = {}
    portfolio: dict[str, tuple[int, int, bool]] = {}
    for chunk in doc.chunks:
        if chunk.key in ("ignore",):
            continue
        free = doc.free_text(chunk)
        for m in URL_RE.finditer(free):
            raw = m.group("url").rstrip(".,;:!?)")
            host, path = _host_and_path(raw)
            has_scheme = bool(re.match(r"https?://|www\.", raw, re.IGNORECASE))
            profile = _linkedin_profile(host, path)
            start = chunk.start + m.start()
            end = start + len(raw)
            if profile is not None:
                linkedin.setdefault(profile, (start, end, chunk.key == "linkedin"))
                continue
            if host.endswith("linkedin.com"):
                doc.claim(start, end)  # a company page or similar: not a profile
                continue
            labelled = chunk.key in ("portfolio", "linkedin")
            if not (has_scheme or labelled or host in _KNOWN_SITES):
                continue
            portfolio.setdefault(
                _with_scheme(raw.rstrip("/")), (start, end, chunk.key == "portfolio")
            )
        if chunk.key == "linkedin" and not any(
            v[0] >= chunk.start and v[1] <= chunk.end for v in linkedin.values()
        ):
            value = chunk.value.strip().strip("/")
            if _SLUG_RE.fullmatch(value):
                linkedin.setdefault(
                    f"https://www.linkedin.com/in/{value}", (chunk.start, chunk.end, True)
                )
    results: list[FieldResult] = []
    for name, urls in (("linkedin_url", linkedin), ("portfolio_url", portfolio)):
        if not urls:
            continue
        for start, end, _ in urls.values():
            doc.claim(start, end)
        results.append(_url_result(name, urls))
    return results


def _url_result(name: str, urls: dict[str, tuple[int, int, bool]]) -> FieldResult:
    label = "LinkedIn" if name == "linkedin_url" else "portfolio"
    if len(urls) == 1:
        ((url, (_, _, keyed)),) = urls.items()
        reason = f"Labelled as {label}." if keyed else f"A {label} link."
        if name == "linkedin_url":
            reason += " Normalized to the standard profile URL."
        return found(name, url, url, "high", reason)
    keyed_urls = [u for u, (_, _, k) in urls.items() if k]
    if len(keyed_urls) == 1:
        return found(
            name,
            keyed_urls[0],
            keyed_urls[0],
            "medium",
            f"Labelled as {label}; other links were left out.",
            warning=f"{len(urls)} links found; the labelled one was used.",
        )
    options = [Alternative(u, u, "A link in the text") for u in urls]
    return ambiguous(name, options, f"{len(urls)} {label} links found: choose one.")
