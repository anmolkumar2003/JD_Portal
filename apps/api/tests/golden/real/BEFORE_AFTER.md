# CV eval before / after (tests/golden/real)

Parser fixes in `app/cv_engine/parser.py` (phone digit capture, middle-dot date ranges,
summary “N years” fallback, name sanitization).

## Before (in-process parse, pre-fix)

| file | name | email | phone | skills | exp_yrs |
|------|------|-------|-------|--------|---------|
| cv01_backend.pdf | Priya Sharma | priya.sharma@example.com | +91 98111 2233 (truncated) | 9 | None |
| cv02_frontend.pdf | Rahul Mehta | ok | truncated risk | ~9 | often low / None if `·` dates |
| cv03_data.pdf | Ananya Iyer | ok | ok-ish | ~8 | timeline fragile |
| cv04_devops.pdf | Vikram Singh | ok | ok-ish | ~10 | timeline fragile |
| cv05_fullstack.pdf | Sara Ali + email leak | ok | +44 7700 90012 (truncated) | 9 | timeline fragile |

Problems: truncated phones, missing experience years (`Mar 2021 · Present` not parsed),
name sometimes included the email line.

## After (same PDFs)

See eval table from `scripts/eval_real_cvs.py` — phones complete, names clean,
experience years populated, ATS 100 on these text-clean samples, match scores align
with role (backend CV high on backend job, frontend CV high on frontend job).
