from app.cv_engine.ats_check import run_ats_check
from app.cv_engine.matcher import score_match
from app.cv_engine.parser import RuleBasedParser
from app.cv_engine.types import CandidateMatchInput, ExtractResult, JobRequirements, SkillSpec

SAMPLE = """
Alex Kumar
alex.kumar@example.com
+91 98765 43210

Experience
Backend Engineer
FinTech Co
Jan 2019 – Present
Python FastAPI PostgreSQL

Education
Bachelor of Technology
Skills
Python, FastAPI, PostgreSQL, Docker
"""


def test_ats_check_weights_and_band() -> None:
    extracted = ExtractResult(
        text=SAMPLE, ocr_used=False, page_count=1, method="pdfplumber", file_size=1000
    )
    parsed = RuleBasedParser().parse(SAMPLE, file_meta=extracted)
    result = run_ats_check(extracted=extracted, parsed=parsed, mime_type="application/pdf")
    assert 0 <= result.score <= 100
    assert result.band in {"good", "needs_improvement", "poor"}
    assert len(result.checks) == 12
    assert sum(c.weight for c in result.checks) == 100
    assert {c.id for c in result.checks} == {f"A{i}" for i in range(1, 13)}


def test_matcher_required_skills_and_never_rejects() -> None:
    job = JobRequirements(
        title="Backend Engineer",
        required_skills=[
            SkillSpec("Python", 2),
            SkillSpec("FastAPI", 1),
            SkillSpec("Kubernetes", 1),
        ],
        preferred_skills=[SkillSpec("Terraform", 1)],
        min_experience=3,
        max_experience=8,
        education_level="bachelor",
    )
    candidate = CandidateMatchInput(
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        titles=["Backend Engineer"],
        total_experience_years=5,
        education_degrees=["B.Tech Computer Science"],
        certifications=[],
        location="Bengaluru",
        notice_period_days=30,
    )
    out = score_match(job, candidate)
    assert 0 <= out.overall_score <= 100
    assert "Python" in out.matched_skills
    assert "Kubernetes" in out.missing_required
    assert "Terraform" in out.missing_preferred
    assert out.explanation["score_version"] == "match-1.0"
    assert "advisory" in out.explanation["disclaimer"].lower()
    # Hard filters never cause rejection — score still returned
    assert isinstance(out.overall_score, int)


def test_weight_renormalization_when_no_preferred() -> None:
    job = JobRequirements(
        title="Engineer",
        required_skills=[SkillSpec("Python")],
        preferred_skills=[],
        min_experience=2,
    )
    candidate = CandidateMatchInput(
        skills=["Python"], titles=["Engineer"], total_experience_years=3
    )
    out = score_match(job, candidate)
    assert out.overall_score >= 50
