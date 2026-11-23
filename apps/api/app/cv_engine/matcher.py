"""JD match scoring. CV-05 / Part 8.2. Advisory only — never rejects."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.cv_engine.explain import build_explanation
from app.cv_engine.skills import canonicalize
from app.cv_engine.types import CandidateMatchInput, JobRequirements, MatchOutput, SkillSpec

MATCH_VERSION = "match-1.0"

DEFAULT_WEIGHTS: dict[str, float] = {
    "required_skills": 40.0,
    "preferred_skills": 10.0,
    "experience": 20.0,
    "title": 10.0,
    "education": 10.0,
    "location": 10.0,
}

_EDU_RANK = {
    "high school": 1,
    "diploma": 2,
    "associate": 3,
    "bachelor": 4,
    "b.tech": 4,
    "btech": 4,
    "ba": 4,
    "bsc": 4,
    "master": 5,
    "m.tech": 5,
    "mba": 5,
    "msc": 5,
    "ms": 5,
    "phd": 6,
    "doctorate": 6,
}


def _skill_set(skills: list[str]) -> dict[str, str]:
    """Map canonical lower -> display name."""
    out: dict[str, str] = {}
    for skill in skills:
        canon = canonicalize(skill).strip()
        if canon:
            out[canon.lower()] = canon
    return out


def _weighted_skill_score(
    required: list[SkillSpec], candidate_skills: dict[str, str]
) -> tuple[float, list[str], list[str]]:
    if not required:
        return 0.0, [], []
    matched: list[str] = []
    missing: list[str] = []
    total_w = 0.0
    got_w = 0.0
    for spec in required:
        name = canonicalize(spec.name)
        weight = float(spec.weight or 1.0)
        total_w += weight
        if name.lower() in candidate_skills:
            matched.append(candidate_skills[name.lower()])
            got_w += weight
        else:
            missing.append(name)
    score = (got_w / total_w) * 100.0 if total_w else 0.0
    return score, matched, missing


def _experience_score(
    years: float | None, min_exp: float | None, max_exp: float | None
) -> float | None:
    if years is None or (min_exp is None and max_exp is None):
        return None
    lo = min_exp if min_exp is not None else 0.0
    hi = max_exp if max_exp is not None else max(lo, years)
    if lo <= years <= hi:
        return 100.0
    if years < lo:
        if lo <= 0:
            return 100.0
        return max(0.0, 100.0 * (years / lo))
    # mild penalty above max
    over = years - hi
    return max(40.0, 100.0 - over * 5.0)


def _title_similarity(job_title: str, candidate_titles: list[str]) -> float | None:
    if not job_title.strip() or not candidate_titles:
        return None
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        # Fallback: token Jaccard
        job_tokens = set(re.findall(r"[a-z0-9]+", job_title.lower()))
        best = 0.0
        for title in candidate_titles:
            tokens = set(re.findall(r"[a-z0-9]+", title.lower()))
            if not tokens:
                continue
            best = max(best, len(job_tokens & tokens) / len(job_tokens | tokens))
        return best * 100.0

    corpus = [job_title] + candidate_titles
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(corpus)
    sims = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    return float(max(sims) * 100.0) if len(sims) else 0.0


def _edu_level(text: str) -> int:
    lowered = text.lower()
    best = 0
    for key, rank in _EDU_RANK.items():
        if key in lowered:
            best = max(best, rank)
    return best


def _education_score(job: JobRequirements, candidate: CandidateMatchInput) -> float | None:
    if not job.education_level and not job.certifications:
        return None
    score = 100.0
    if job.education_level:
        required = _edu_level(job.education_level)
        got = max((_edu_level(d) for d in candidate.education_degrees), default=0)
        score = 100.0 if got >= required else max(0.0, (got / max(required, 1)) * 100.0)
    if job.certifications:
        cand = {c.lower() for c in candidate.certifications}
        hits = sum(1 for c in job.certifications if c.lower() in cand)
        cert_score = (hits / len(job.certifications)) * 100.0
        score = (score + cert_score) / 2.0 if job.education_level else cert_score
    return score


def _location_score(job: JobRequirements, candidate: CandidateMatchInput) -> float | None:
    has_signal = bool(job.work_mode or job.location_name or job.target_notice_days is not None)
    if not has_signal:
        return None
    scores: list[float] = []
    if job.work_mode and job.work_mode.lower() == "remote":
        scores.append(100.0)
    elif job.location_name and candidate.location:
        job_loc = job.location_name.lower()
        cand_loc = candidate.location.lower()
        scores.append(100.0 if job_loc in cand_loc or cand_loc in job_loc else 50.0)
    if job.target_notice_days is not None and candidate.notice_period_days is not None:
        if candidate.notice_period_days <= job.target_notice_days:
            scores.append(100.0)
        else:
            over = candidate.notice_period_days - job.target_notice_days
            scores.append(max(0.0, 100.0 - over))
    return sum(scores) / len(scores) if scores else None


def _renormalize(weights: dict[str, float], active: set[str]) -> dict[str, float]:
    subset = {k: v for k, v in weights.items() if k in active and v > 0}
    total = sum(subset.values())
    if total <= 0:
        return dict.fromkeys(weights, 0.0)
    return {k: (subset.get(k, 0.0) / total) * 100.0 for k in weights}


def _inputs_hash(job: JobRequirements, candidate: CandidateMatchInput) -> str:
    payload = {
        "job": {
            "title": job.title,
            "required": [(s.name, s.weight) for s in job.required_skills],
            "preferred": [(s.name, s.weight) for s in job.preferred_skills],
            "min_experience": job.min_experience,
            "max_experience": job.max_experience,
            "education_level": job.education_level,
            "certifications": job.certifications,
            "weights_override": job.weights_override,
        },
        "candidate": {
            "skills": sorted(candidate.skills),
            "titles": candidate.titles,
            "years": candidate.total_experience_years,
            "education": candidate.education_degrees,
            "certs": candidate.certifications,
            "location": candidate.location,
            "notice": candidate.notice_period_days,
        },
        "version": MATCH_VERSION,
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def score_match(job: JobRequirements, candidate: CandidateMatchInput) -> MatchOutput:
    """Compute advisory JD match. Never rejects; hard filters are flags only."""
    weights = dict(DEFAULT_WEIGHTS)
    if job.weights_override:
        for key, value in job.weights_override.items():
            if key in weights:
                weights[key] = float(value)

    cand_skills = _skill_set(candidate.skills)
    req_score, matched_req, missing_req = _weighted_skill_score(job.required_skills, cand_skills)
    pref_score, matched_pref, missing_pref = _weighted_skill_score(
        job.preferred_skills, cand_skills
    )

    component: dict[str, float | None] = {
        "required_skills": req_score if job.required_skills else None,
        "preferred_skills": pref_score if job.preferred_skills else None,
        "experience": _experience_score(
            candidate.total_experience_years, job.min_experience, job.max_experience
        ),
        "title": _title_similarity(job.title, candidate.titles),
        "education": _education_score(job, candidate),
        "location": _location_score(job, candidate),
    }

    active = {k for k, v in component.items() if v is not None}
    # Always keep required_skills active if defined; if empty job, use zeros
    if not active:
        active = set(DEFAULT_WEIGHTS)
        component = dict.fromkeys(DEFAULT_WEIGHTS, 0.0)

    norm = _renormalize(weights, active)
    numeric = {k: float(component[k] or 0.0) for k in DEFAULT_WEIGHTS}
    overall = sum(numeric[k] * (norm[k] / 100.0) for k in DEFAULT_WEIGHTS)
    overall_i = int(round(max(0.0, min(100.0, overall))))

    matched = list(dict.fromkeys(matched_req + matched_pref))
    extra = [
        name
        for key, name in cand_skills.items()
        if key not in {m.lower() for m in matched} and key not in {m.lower() for m in missing_req}
    ][:20]

    hard_flags: list[str] = []
    for cert in job.mandatory_certifications:
        if cert.lower() not in {c.lower() for c in candidate.certifications}:
            hard_flags.append(f"Missing mandatory certification: {cert}")

    # Map component keys to explanation-friendly names used in UI/spec
    display_components = {
        "skills": numeric["required_skills"],
        "preferred_skills": numeric["preferred_skills"],
        "experience": numeric["experience"],
        "title": numeric["title"],
        "education": numeric["education"],
        "location": numeric["location"],
    }

    explanation = build_explanation(
        component_scores=display_components,
        matched_skills=matched,
        missing_required=missing_req,
        missing_preferred=missing_pref,
        extra_skills=extra,
        hard_filter_flags=hard_flags,
        experience_years=candidate.total_experience_years,
        min_experience=job.min_experience,
        score_version=MATCH_VERSION,
    )

    breakdown = {
        "skills": int(round(numeric["required_skills"])),
        "preferred_skills": int(round(numeric["preferred_skills"])),
        "experience": int(round(numeric["experience"])),
        "education": int(round(numeric["education"])),
        "title": int(round(numeric["title"])),
        "location": int(round(numeric["location"])),
        "weights_used": {k: round(v, 2) for k, v in norm.items() if k in active},
    }
    explanation["component_scores"] = {
        "skills": breakdown["skills"],
        "experience": breakdown["experience"],
        "education": breakdown["education"],
        "title": breakdown["title"],
        "location": breakdown["location"],
    }

    return MatchOutput(
        overall_score=overall_i,
        component_scores={k: float(v) for k, v in breakdown.items() if isinstance(v, int)},
        matched_skills=matched,
        missing_required=missing_req,
        missing_preferred=missing_pref,
        extra_skills=extra,
        hard_filter_flags=hard_flags,
        explanation=explanation,
        engine_version=MATCH_VERSION,
        inputs_hash=_inputs_hash(job, candidate),
    )


def match_result_to_breakdown(result: MatchOutput) -> dict[str, Any]:
    return {
        "skills": int(result.explanation.get("component_scores", {}).get("skills", 0)),
        "experience": int(result.explanation.get("component_scores", {}).get("experience", 0)),
        "education": int(result.explanation.get("component_scores", {}).get("education", 0)),
        "title": int(result.explanation.get("component_scores", {}).get("title", 0)),
        "location": int(result.explanation.get("component_scores", {}).get("location", 0)),
        "hard_filter_flags": result.hard_filter_flags,
    }
