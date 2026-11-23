# Licenses

The portal uses only free, open-source software and no paid APIs, SaaS or external AI
services. CV parsing, scoring, OCR and email all run on our own servers.

The portal is an internal tool used by the company's HR team; it is not distributed to anyone.
Copyleft licenses below (LGPL, AGPL, GPL) are fine for that use. The notes column says what
would matter if that ever changed.

## Runtime services (Docker images)

| Component                 | License            | Notes                                                                 |
| ------------------------- | ------------------ | --------------------------------------------------------------------- |
| PostgreSQL + pgvector     | PostgreSQL License | Permissive                                                            |
| Valkey                    | BSD-3-Clause       | Replaces Redis: Redis 7.4+ is source-available (RSAL/SSPL), not open source |
| MinIO (Chainguard build)  | AGPL-3.0           | Used unmodified as a separate service; we only call its S3 API        |
| Mailpit (development only) | MIT               | Not part of production                                                |
| Caddy (production)        | Apache-2.0         | Reverse proxy and automatic HTTPS                                     |
| ClamAV (production)       | GPL-2.0            | Separate daemon, called over its socket protocol                      |
| Tesseract OCR             | Apache-2.0         | Installed in the API image                                            |

## API (Python)

| Package                                    | License                  |
| ------------------------------------------ | ------------------------ |
| FastAPI, Starlette, Pydantic, uvicorn      | MIT / BSD-3-Clause       |
| SQLAlchemy, Alembic                        | MIT                      |
| asyncpg                                    | Apache-2.0               |
| psycopg                                    | LGPL-3.0 (dynamic use)   |
| Celery, redis-py                           | BSD-3-Clause / MIT       |
| argon2-cffi, PyJWT, email-validator        | MIT / MIT / Unlicense    |
| python-multipart                           | Apache-2.0               |
| boto3                                      | Apache-2.0               |
| pdfplumber (with pdfminer.six)             | MIT                      |
| pypdf                                      | BSD-3-Clause             |
| pypdfium2 (with PDFium)                    | Apache-2.0 / BSD-3-Clause |
| python-docx                                | MIT                      |
| pytesseract                                | Apache-2.0               |
| Pillow                                     | MIT-CMU (HPND)           |
| spaCy and the `en_core_web_sm` model       | MIT                      |
| scikit-learn                               | BSD-3-Clause             |
| ReportLab (open-source toolkit)            | BSD-3-Clause             |

Development only: pytest, ruff, mypy (MIT), httpx (BSD-3-Clause).

## Web (JavaScript)

| Package                                   | License    |
| ----------------------------------------- | ---------- |
| Next.js, React                            | MIT        |
| TanStack Query                            | MIT        |
| Radix UI, shadcn/ui components            | MIT        |
| Tailwind CSS, tailwind-merge, tailwindcss-animate, class-variance-authority, clsx | MIT |
| react-hook-form, @hookform/resolvers, zod | MIT        |
| dnd-kit                                   | MIT        |
| lucide-react                              | ISC        |
| sonner                                    | MIT        |
| Recharts                                  | MIT        |
| Playwright (tests only)                   | Apache-2.0 |

## Decisions

### PyMuPDF removed

PyMuPDF is AGPL-3.0 (or a paid commercial license). It was the fallback PDF text extractor and
rendered pages for OCR. It is replaced by pypdf (BSD) for fallback text and pypdfium2
(Apache-2.0/BSD) for page rendering. pdfplumber stays the primary extractor.

The replacement was made only after checking that extraction quality did not drop. Each library
extracted the 10 labelled golden PDFs in `apps/api/tests/golden/`, and the text went through the
same parser (`tests/golden/compare_pdf_backends.py`):

| Library    | Email | Phone | Experience | Skill precision | Skill recall |
| ---------- | ----- | ----- | ---------- | --------------- | ------------ |
| pdfplumber | 100%  | 100%  | 100%       | 82%             | 100%         |
| pypdf      | 100%  | 100%  | 100%       | 82%             | 100%         |
| pypdfium2  | 100%  | 100%  | 100%       | 82%             | 100%         |
| PyMuPDF    | 100%  | 100%  | 100%       | 82%             | 100%         |

Results were identical, so nothing was lost.

### ReportLab

An earlier audit listed ReportLab as AGPL. That is wrong. The open-source ReportLab toolkit
used here (`reportlab` on PyPI) is BSD-3-Clause; only the separate commercial "ReportLab PLUS"
product is paid. It stays for generating offer letter PDFs and test fixtures.

### Redis replaced with Valkey

Redis 7.4 and later are released under RSALv2/SSPLv1, which are not open-source licenses (Redis
8 added AGPL as a third option). Valkey is the BSD-licensed Linux Foundation fork of Redis 7.2
and is protocol-compatible, so the code and the `redis` Python client are unchanged.
