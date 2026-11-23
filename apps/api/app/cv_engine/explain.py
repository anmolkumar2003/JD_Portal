"""Build match explanation JSON. CV-06 / Part 8.2."""

from __future__ import annotations

from typing import Any


def build_explanation(
    *,
    component_scores: dict[str, float],
    matched_skills: list[str],
    missing_required: list[str],
    missing_preferred: list[str],
    extra_skills: list[str],
    hard_filter_flags: list[str],
    experience_years: float | None,
    min_experience: float | None,
    score_version: str = "match-1.0",
) -> dict[str, Any]:
    strengths: list[str] = []
    concerns: list[str] = []

    req_total = len(matched_skills) + len(missing_required)
    if matched_skills and req_total:
        strengths.append(f"{len(matched_skills)} of {req_total} required skills")
    if component_scores.get("title", 0) >= 70:
        strengths.append("Relevant role title alignment")
    if component_scores.get("education", 0) >= 80:
        strengths.append("Education / certifications meet the bar")
    if component_scores.get("experience", 0) >= 80:
        strengths.append("Experience within the target range")

    if missing_required:
        concerns.append(f"Missing required: {', '.join(missing_required[:5])}")
    if (
        experience_years is not None
        and min_experience is not None
        and experience_years < min_experience
    ):
        gap = round(min_experience - experience_years, 1)
        concerns.append(f"{gap} years less experience than required")
    if missing_preferred:
        concerns.append(f"Preferred gaps: {', '.join(missing_preferred[:3])}")
    concerns.extend(hard_filter_flags)

    if not strengths:
        strengths.append("Partial skill overlap with the role")
    if not concerns:
        concerns.append("No major gaps detected (advisory)")

    summary_bits: list[str] = []
    if matched_skills:
        summary_bits.append(f"Strong on {', '.join(matched_skills[:3])}")
    if missing_required:
        summary_bits.append(f"lacks {', '.join(missing_required[:2])}")
    if (
        experience_years is not None
        and min_experience is not None
        and experience_years < min_experience
    ):
        summary_bits.append(
            f"has {round(min_experience - experience_years, 1)} years less experience than required"
        )
    summary = (
        "; ".join(summary_bits) + "." if summary_bits else "Advisory match summary unavailable."
    )

    return {
        "summary": summary,
        "strengths": strengths,
        "concerns": concerns,
        "component_scores": {k: int(round(v)) for k, v in component_scores.items()},
        "matched_skills": matched_skills,
        "missing_required": missing_required,
        "missing_preferred": missing_preferred,
        "extra_skills": extra_skills,
        "hard_filter_flags": hard_filter_flags,
        "score_version": score_version,
        "disclaimer": "Score is advisory; a recruiter makes the decision.",
    }
