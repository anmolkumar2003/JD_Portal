"""Upload golden/real CVs through the API, wait for parsing, print score table.

Usage (stack up, migrated, seeded):
  docker compose exec api python scripts/eval_real_cvs.py
  docker compose exec api python scripts/eval_real_cvs.py --out /tmp/eval_before.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

API = "http://localhost:8000/api/v1"
REAL_DIR = Path(__file__).resolve().parents[1] / "tests" / "golden" / "real"
# Demo seed account (make seed-demo); the password comes from the environment.
LOGIN_EMAIL = os.environ.get("DEMO_LOGIN_EMAIL", "recruiter@demo.example.com")
LOGIN_PASSWORD = os.environ.get("DEMO_PASSWORD", "")

# Form hints from golden labels / source text (apply still sends multipart identity).
CV_META: dict[str, dict[str, str]] = {
    "cv01_backend.pdf": {
        "first_name": "Priya",
        "last_name": "Sharma",
        "email": "priya.sharma@example.com",
        "phone": "+91 98111 22334",
    },
    "cv02_frontend.pdf": {
        "first_name": "Rahul",
        "last_name": "Mehta",
        "email": "rahul.mehta@example.com",
        "phone": "+91 99000 11223",
    },
    "cv03_data.pdf": {
        "first_name": "Ananya",
        "last_name": "Iyer",
        "email": "ananya.iyer@example.com",
        "phone": "+91 91234 56789",
    },
    "cv04_devops.pdf": {
        "first_name": "Vikram",
        "last_name": "Singh",
        "email": "vikram.singh@example.com",
        "phone": "+91 98765 00112",
    },
    "cv05_fullstack.pdf": {
        "first_name": "Sara",
        "last_name": "Ali",
        "email": "sara.ali@example.com",
        "phone": "+44 7700 900123",
    },
}

OPEN_SLUGS = ("senior-android-developer", "shopify-developer")


def _login(client: httpx.Client) -> str:
    r = client.post(
        f"{API}/auth/login",
        json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _apply(client: httpx.Client, slug: str, meta: dict[str, str], pdf: Path) -> dict[str, Any]:
    data = {
        **meta,
        "consent": "true",
        "website": "",
        "current_location": "",
        "current_company": "",
        "current_title": "",
        "cover_letter": "",
    }
    files = {"cv": (pdf.name, pdf.read_bytes(), "application/pdf")}
    r = client.post(f"{API}/public/jobs/{slug}/apply", data=data, files=files)
    if r.status_code == 409:
        return {"duplicate": True, "status_code": 409, "body": r.json()}
    if r.status_code >= 400:
        return {"error": True, "status_code": r.status_code, "body": r.text}
    return r.json()


def _list_jobs(client: httpx.Client, token: str) -> dict[str, str]:
    """slug -> job id (includes draft jobs recruiters can see)."""
    r = client.get(
        f"{API}/jobs",
        headers={"Authorization": f"Bearer {token}"},
        params={"page_size": 50},
    )
    r.raise_for_status()
    return {item["slug"]: item["id"] for item in r.json().get("items", [])}


def _manual_upload(
    client: httpx.Client,
    token: str,
    meta: dict[str, str],
    pdf: Path,
    job_id: str | None,
) -> dict[str, Any]:
    """CAND-10 portal upload — avoids public apply rate limit (5/hour)."""
    data = {
        "first_name": meta["first_name"],
        "last_name": meta["last_name"],
        "email": meta["email"],
        "phone": meta.get("phone") or "",
        "source": "manual",
    }
    if job_id:
        data["job_id"] = job_id
    files = {"cv": (pdf.name, pdf.read_bytes(), "application/pdf")}
    r = client.post(
        f"{API}/candidates",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    if r.status_code >= 400:
        return {"error": True, "status_code": r.status_code, "body": r.text}
    return r.json()


def _job_matches_slug(job: dict[str, Any], job_slug: str) -> bool:
    title = (job.get("name") or job.get("title") or "").lower()
    if job.get("slug") == job_slug:
        return True
    if job_slug == "senior-backend-engineer":
        return "backend" in title
    if job_slug == "frontend-engineer":
        return "frontend" in title
    if job_slug == "hr-business-partner":
        return "hr" in title and "partner" in title
    return False


def _find_application(
    client: httpx.Client, token: str, email: str, job_slug: str
) -> dict[str, Any] | None:
    r = client.get(
        f"{API}/applications",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": email, "page_size": 50},
    )
    r.raise_for_status()
    for item in r.json().get("items", []):
        if item.get("email", "").lower() != email.lower():
            continue
        if _job_matches_slug(item.get("job") or {}, job_slug):
            return item
    return None


def _wait_analysis(
    client: httpx.Client, token: str, application_id: str, timeout: float = 120.0
) -> dict[str, Any]:
    deadline = time.time() + timeout
    headers = {"Authorization": f"Bearer {token}"}
    last: dict[str, Any] = {}
    while time.time() < deadline:
        r = client.get(f"{API}/applications/{application_id}/analysis", headers=headers)
        if r.status_code == 200:
            last = r.json()
            profile = last.get("parsed_profile") or {}
            status = profile.get("parse_status")
            if status in ("done", "failed"):
                return last
        time.sleep(1.5)
    return last or {"error": "timeout"}


def _profile_fields(analysis: dict[str, Any]) -> dict[str, Any]:
    profile = analysis.get("parsed_profile") or {}
    data = profile.get("data") or {}
    skills = data.get("skills") or []
    skill_names: list[str] = []
    for s in skills:
        if isinstance(s, str):
            skill_names.append(s)
        elif isinstance(s, dict):
            skill_names.append(str(s.get("name") or s.get("canonical") or ""))
    name = str(data.get("full_name") or data.get("name") or "").strip()
    ats = analysis.get("ats_check") or {}
    match = analysis.get("match_result") or {}
    return {
        "parse_status": profile.get("parse_status"),
        "parse_error": profile.get("error"),
        "name": name,
        "email": str(data.get("email") or ""),
        "phone": str(data.get("phone") or ""),
        "skills_count": len([n for n in skill_names if n]),
        "skills": [n for n in skill_names if n],
        "experience_years": profile.get("total_experience_years"),
        "ats_score": ats.get("score"),
        "ats_checks": ats.get("checks") or [],
        "match_score": match.get("overall_score"),
        "matched_skills": match.get("matched_skills") or [],
        "missing_required": match.get("missing_required") or [],
    }


def _skills_to_specs(items: list[Any]) -> list[Any]:
    from app.cv_engine.types import SkillSpec

    specs: list[SkillSpec] = []
    for item in items or []:
        if isinstance(item, dict) and item.get("name"):
            specs.append(SkillSpec(name=str(item["name"]), weight=float(item.get("weight") or 1.0)))
        elif isinstance(item, str):
            specs.append(SkillSpec(name=item))
    return specs


def _score_against_jobs_via_engine(
    pdf: Path, job_specs: list[dict[str, Any]]
) -> dict[str, int | None]:
    """Score one CV against job requirement dicts using in-process cv_engine."""
    from app.cv_engine.extract import extract_text
    from app.cv_engine.matcher import score_match
    from app.cv_engine.parser import RuleBasedParser
    from app.cv_engine.types import CandidateMatchInput, JobRequirements

    extracted = extract_text(pdf.read_bytes(), "application/pdf")
    parsed = RuleBasedParser().parse(extracted.text, file_meta=extracted)
    candidate = CandidateMatchInput(
        skills=list(parsed.skills),
        titles=[e.title for e in parsed.experience if e.title],
        total_experience_years=parsed.total_experience_years,
        education_degrees=[e.degree for e in parsed.education if e.degree],
        certifications=[c.name for c in parsed.certifications if c.name],
        location=parsed.location,
    )
    scores: dict[str, int | None] = {}
    for job in job_specs:
        try:
            req = JobRequirements(
                title=str(job.get("title") or ""),
                required_skills=_skills_to_specs(job.get("required_skills") or []),
                preferred_skills=_skills_to_specs(job.get("preferred_skills") or []),
                min_experience=job.get("min_experience"),
                max_experience=job.get("max_experience"),
                education_level=job.get("education_level"),
            )
            result = score_match(req, candidate)
            scores[job["slug"]] = int(result.overall_score)
        except Exception as exc:
            scores[job["slug"]] = None
            scores[f"{job['slug']}_error"] = str(exc)  # type: ignore[assignment]
    return scores


def _load_job_specs() -> list[dict[str, Any]]:
    """Pull job requirements from DB for all seeded jobs."""
    import asyncio
    import sys
    from pathlib import Path as _Path

    # `python scripts/eval_real_cvs.py` does not put /app on sys.path
    root = _Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from sqlalchemy import select

    from app.core.db import SessionLocal, engine
    from app.models import Job, JobRequirement

    async def _run() -> list[dict[str, Any]]:
        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(Job, JobRequirement).join(
                        JobRequirement, JobRequirement.job_id == Job.id
                    )
                )
            ).all()
            out: list[dict[str, Any]] = []
            for job, req in rows:
                out.append(
                    {
                        "slug": job.slug,
                        "title": job.title,
                        "required_skills": req.required_skills or [],
                        "preferred_skills": req.preferred_skills or [],
                        "min_experience": float(req.min_experience)
                        if req.min_experience is not None
                        else None,
                        "max_experience": float(req.max_experience)
                        if req.max_experience is not None
                        else None,
                        "education_level": req.education_level,
                    }
                )
            return out

    try:
        return asyncio.run(_run())
    finally:
        try:
            asyncio.run(engine.dispose())
        except Exception:
            pass


def evaluate(*, run_id: str) -> list[dict[str, Any]]:
    pdfs = sorted(REAL_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs in {REAL_DIR}")

    job_specs = _load_job_specs()
    results: list[dict[str, Any]] = []

    with httpx.Client(timeout=60.0) as client:
        token = _login(client)
        jobs = _list_jobs(client, token)
        primary = OPEN_SLUGS[0]
        primary_job_id = jobs.get(primary)

        for pdf in pdfs:
            meta = dict(CV_META.get(pdf.name, {}))
            if not meta:
                stem = pdf.stem
                meta = {
                    "first_name": "Eval",
                    "last_name": stem[:40],
                    "email": f"eval-{stem}-{run_id[:8]}@example.com",
                    "phone": "+91 90000 00000",
                }
            else:
                # Unique email per run so re-evals don't collide
                base = meta["email"].split("@")
                meta["email"] = f"{base[0]}+{run_id[:8]}@{base[1]}"

            row: dict[str, Any] = {
                "file": pdf.name,
                "form_email": meta["email"],
                "applications": {},
                "problems": [],
            }

            # Upload through portal (CAND-10) linked to primary seeded job
            uploaded = _manual_upload(client, token, meta, pdf, primary_job_id)
            if uploaded.get("error"):
                row["problems"].append(f"upload failed: {uploaded}")
                results.append(row)
                continue

            application_id = uploaded.get("application_id")
            if not application_id:
                time.sleep(2)
                app_item = _find_application(client, token, meta["email"], primary)
                application_id = app_item["id"] if app_item else None
            if not application_id:
                row["problems"].append("application not found after upload")
                results.append(row)
                continue

            analysis = _wait_analysis(client, token, str(application_id))
            fields = _profile_fields(analysis)
            row.update(fields)
            row["applications"][primary] = fields.get("match_score")

            # Link same candidate to other jobs for live match scores
            for slug, job_id in jobs.items():
                if slug == primary:
                    continue
                linked = _manual_upload(client, token, meta, pdf, job_id)
                if linked.get("error"):
                    row["problems"].append(f"link {slug} failed: {linked.get('status_code')}")
                    continue
                other_id = linked.get("application_id")
                if not other_id:
                    other = _find_application(client, token, meta["email"], slug)
                    other_id = other["id"] if other else None
                if other_id:
                    other_analysis = _wait_analysis(client, token, str(other_id), timeout=90)
                    row["applications"][slug] = _profile_fields(other_analysis).get("match_score")

            # Engine scores fill any gaps (and act as cross-check)
            try:
                engine_scores = _score_against_jobs_via_engine(pdf, job_specs)
                row["engine_match_by_job"] = engine_scores
                for job in job_specs:
                    slug = job["slug"]
                    if slug not in row["applications"] or row["applications"][slug] is None:
                        row["applications"][slug] = engine_scores.get(slug)
            except Exception as exc:
                row["problems"].append(f"engine match failed: {exc}")

            results.append(row)

    return results


def print_table(rows: list[dict[str, Any]], job_slugs: list[str]) -> None:
    headers = [
        "file",
        "name",
        "email",
        "phone",
        "skills",
        "exp_yrs",
        "ats",
        *job_slugs,
    ]
    print(" | ".join(headers))
    print("-+-".join("-" * len(h) for h in headers))
    for r in rows:
        cells = [
            str(r.get("file", "")),
            str(r.get("name") or ""),
            str(r.get("email") or ""),
            str(r.get("phone") or ""),
            str(r.get("skills_count", "")),
            str(r.get("experience_years") if r.get("experience_years") is not None else ""),
            str(r.get("ats_score") if r.get("ats_score") is not None else ""),
        ]
        apps = r.get("applications") or {}
        for slug in job_slugs:
            cells.append(str(apps.get(slug) if apps.get(slug) is not None else ""))
        print(" | ".join(cells))


def collect_problems(rows: list[dict[str, Any]]) -> list[str]:
    expected = {
        "cv01_backend.pdf": {
            "name": "Priya Sharma",
            "email_part": "priya.sharma",
            "phone": "98111",
            "min_skills": 7,
            "min_exp": 6,
        },
        "cv02_frontend.pdf": {
            "name": "Rahul Mehta",
            "email_part": "rahul.mehta",
            "phone": "99000",
            "min_skills": 5,
            "min_exp": 5,
        },
        "cv03_data.pdf": {
            "name": "Ananya Iyer",
            "email_part": "ananya.iyer",
            "phone": "91234",
            "min_skills": 5,
            "min_exp": 6,
        },
        "cv04_devops.pdf": {
            "name": "Vikram Singh",
            "email_part": "vikram.singh",
            "phone": "98765",
            "min_skills": 6,
            "min_exp": 7,
        },
        "cv05_fullstack.pdf": {
            "name": "Sara Ali",
            "email_part": "sara.ali",
            "phone": "7700",
            "min_skills": 5,
            "min_exp": 6,
        },
    }
    problems: list[str] = []
    for r in rows:
        for p in r.get("problems") or []:
            problems.append(f"{r.get('file')}: {p}")
        if r.get("parse_status") == "failed":
            problems.append(f"{r.get('file')}: parse failed: {r.get('parse_error')}")
        exp = expected.get(str(r.get("file")), {})
        if not exp:
            continue
        name = (r.get("name") or "").strip()
        if exp["name"].lower() not in name.lower() and name.lower() not in exp["name"].lower():
            problems.append(
                f"{r.get('file')}: wrong/missing name got={name!r} want={exp['name']!r}"
            )
        email = (r.get("email") or "").lower()
        if exp["email_part"] not in email:
            problems.append(f"{r.get('file')}: missing/wrong email got={email!r}")
        phone = r.get("phone") or ""
        if exp["phone"] not in phone.replace(" ", ""):
            problems.append(f"{r.get('file')}: missing/wrong phone got={phone!r}")
        if int(r.get("skills_count") or 0) < exp["min_skills"]:
            problems.append(
                f"{r.get('file')}: skills under-detected count={r.get('skills_count')} "
                f"skills={r.get('skills')}"
            )
        try:
            years = float(r.get("experience_years") or 0)
        except (TypeError, ValueError):
            years = 0
        if years < exp["min_exp"]:
            problems.append(
                f"{r.get('file')}: experience too low got={r.get('experience_years')} "
                f"want>={exp['min_exp']}"
            )
        if r.get("ats_score") is None:
            problems.append(f"{r.get('file')}: missing ATS score")
        elif int(r.get("ats_score") or 0) < 40:
            problems.append(f"{r.get('file')}: suspiciously low ATS score={r.get('ats_score')}")
        checks = r.get("ats_checks") or []
        for c in checks:
            if (
                isinstance(c, dict)
                and c.get("passed") is False
                and c.get("id")
                in {
                    "contact_email",
                    "contact_phone",
                    "sections",
                }
            ):
                # flag if we have the field but check failed
                if c.get("id") == "contact_email" and email:
                    problems.append(f"{r.get('file')}: ATS email check failed despite parsed email")
                if c.get("id") == "contact_phone" and phone:
                    problems.append(f"{r.get('file')}: ATS phone check failed despite parsed phone")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    run_id = args.run_id or uuid.uuid4().hex

    rows = evaluate(run_id=run_id)
    job_slugs = sorted({k for r in rows for k in (r.get("applications") or {})})
    if not job_slugs:
        job_slugs = list(OPEN_SLUGS)

    print("\n=== CV EVAL TABLE ===")
    print_table(rows, job_slugs)
    problems = collect_problems(rows)
    print("\n=== PROBLEMS ===")
    if not problems:
        print("(none)")
    else:
        for p in problems:
            print(f"- {p}")

    payload = {"run_id": run_id, "rows": rows, "problems": problems}
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2, default=str))
        print(f"\nWrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
