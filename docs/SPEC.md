HR Recruitment Portal (ATS) — 
Specification Pack
Version 1.0 · 20 Nov 2026 · Audience: engineering team and Cursor AI agents
How to use this document. Parts 1–7 define what to build (product, requirements,
architecture, data). Parts 8–10 define how the CV engine, API and UI work. Part 11 gives the
rules file and the step-by-step agent prompts to build it fast in Cursor. Build in the order
of Part 12.
1. Product Overview
Vision. A single web portal that manages the full recruitment lifecycle: job requisition,
posting, application, CV analysis, screening, interviews, offers and reporting, with an
enterprise-grade UI.
Problem. Recruiters currently handle applications through email and spreadsheets. CVs
are read manually, there is no consistent scoring against job requirements, and there is no
visibility into the hiring funnel.
Goals
Capture every applicant's details in one structured profile.
Automatically parse CVs, check ATS-friendliness, and score each candidate against
the job requirements, with an explanation.
Give recruiters a Kanban pipeline and fast candidate review.
Give management hiring analytics.
Be secure, auditable and compliant (GDPR / India DPDP Act; confirm specifics with
legal).
In scope (v1): Auth and RBAC, job management, public careers site and application form,
candidate profiles, CV upload and parsing, ATS-friendliness check, JD match scoring,
Kanban pipeline, notes and tags, email templates and notifications, interview scheduling
and scorecards, offer tracking, dashboard and analytics, audit log.
Out of scope (v1): Payroll, full onboarding, job-board auto-posting, video interviews,
coding-test platform, multi-tenant SaaS billing. These are designed for (extensible) but
not built.
Design principle: human in the loop. AI scores assist recruiters and never auto-reject.
Every score stores its inputs, version and explanation. (EU AI Act and NYC Local Law 144
treat hiring AI as high-risk.)
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 1 of 27

Success metrics. Time-to-screen reduced by 50%; recruiter can review a candidate in
under 60 seconds; CV parse accuracy above 90% on name, email, phone and skills; page
load under 2 seconds.
2. Users, Roles and Permissions
Permission matrix (C = create, R = read, U = update, D = delete, own = only own/assigned
records)
Role Description
Candidate External applicant. Browses jobs, applies, tracks
status.
Recruiter Owns jobs and candidates. Screens, moves stages,
schedules, emails.
Hiring Manager Raises requisitions, reviews shortlists for own jobs,
gives feedback, approves offers.
Interviewer Sees only assigned interviews and their
candidates; submits scorecards.
HR Admin Configures pipelines, templates, departments,
users, scoring weights.
Super Admin / Auditor Everything, plus audit logs and data-retention
controls.
Resource Candidate Recruiter Hiring Mgr Interviewer HR Admin Super
Admin
Jobs R
(published)
CRUD R/U own R assigned CRUD CRUD
Requisitions – R C, R own,
approve
– CRUD CRUD
Candidates /
Applications
own CRUD R own jobs R assigned CRUD CRUD
CV and parsed data own R R own jobs R assigned R R
Match score – R R R (if
enabled)
R,
configure
R,
configure
Interviews /
Scorecards
R own CRUD R, C own jobs C/U own CRUD CRUD
Offers R own CRU Approve – CRUD CRUD
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 2 of 27

3. Functional Requirements
Priority uses MoSCoW: M must, S should, C could. Each ID is a traceable requirement;
reference IDs in commits and agent prompts.
3.1 Authentication and Access (AUTH)
AUTH-01 (M) Email/password login with hashed passwords (argon2/bcrypt), JWT
access plus refresh tokens.
AUTH-02 (M) Role-based access control enforced on the backend for every endpoint.
AUTH-03 (M) Password reset by email, account lockout after repeated failures.
AUTH-04 (S) Two-factor authentication (TOTP).
AUTH-05 (C) SSO via OIDC / SAML (Azure AD, Google).
AUTH-06 (M) Record-level access: interviewers see only assigned candidates; hiring
managers only their own jobs.
3.2 Organization Setup (ORG)
ORG-01 (M) Manage departments, locations, employment types, job levels.
ORG-02 (M) Manage users and assign roles.
ORG-03 (S) Configure pipeline stages per job template (default: Applied, Screening,
Interview, Offer, Hired, Rejected).
ORG-04 (S) Configure scoring weights and rejection reasons.
3.3 Requisitions (REQ)
REQ-01 (S) Hiring manager raises a requisition: title, department, headcount,
justification, budget band.
REQ-02 (S) Approval workflow (manager → HR → finance); statuses Draft, Pending,
Approved, Rejected.
REQ-03 (S) An approved requisition converts into a Job in one click.
Resource Candidate Recruiter Hiring Mgr Interviewer HR Admin Super
Admin
Users / Roles – – – – CRUD CRUD
Audit log – – – – R R
Analytics – R own R own – R all R all
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 3 of 27

3.4 Job Management (JOB)
JOB-01 (M) Create/edit job: title, department, location (onsite/hybrid/remote), type,
level, salary band, openings, description, responsibilities, qualifications.
JOB-02 (M) Structured requirements: required skills, nice-to-have skills (each with
optional weight), minimum/maximum years of experience, education, certifications.
JOB-03 (M) Job status lifecycle: Draft, Open, On Hold, Closed, Filled.
JOB-04 (M) Publish to the public careers site; unique slug URL; closing date.
JOB-05 (S) Clone job; AI-assisted JD skill extraction (suggest skills from the pasted
JD text).
JOB-06 (S) Assign recruiters, hiring manager and interview panel per job.
3.5 Careers Site and Application (APPLY)
APPLY-01 (M) Public job listing with search and filters (department, location, type).
APPLY-02 (M) Job detail page and Apply form: first/last name, email, phone, current
location, current company and title, total experience, current/expected CTC, notice
period, LinkedIn/portfolio URL, CV upload (PDF/DOCX, max 5 MB), optional cover
letter, custom screening questions per job.
APPLY-03 (M) Consent checkbox for data processing; timestamp stored.
APPLY-04 (M) CAPTCHA and rate limiting; file-type and malware validation.
APPLY-05 (M) Confirmation email and application reference number.
APPLY-06 (S) Candidate portal: log in via magic link, see application status, withdraw,
update details.
APPLY-07 (M) Duplicate detection by email/phone; same person applying to multiple
jobs reuses one Candidate record.
APPLY-08 (C) Apply with LinkedIn / autofill from CV.
3.5.1 Equal-opportunity data
APPLY-09 (C) Optional, separately stored diversity questionnaire, never shown during
screening.
3.6 Candidate Management (CAND)
CAND-01 (M) Candidate list: table with search, filters (job, stage, score range, skills,
experience, location, source, date), sorting, pagination, saved filters.
CAND-02 (M) Candidate profile with tabs: Overview, CV, Match Analysis, Timeline,
Interviews, Notes, Documents, Emails.
CAND-03 (M) Side drawer quick-view from list or Kanban.
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 4 of 27

CAND-04 (M) Activity timeline: applied, stage changes, emails, notes, interviews,
score changes, with user and timestamp.
CAND-05 (M) Notes with @mentions, tags, star/shortlist.
CAND-06 (S) Bulk actions: move stage, reject with reason, email, tag, export.
CAND-07 (S) Compare 2–4 candidates side by side.
CAND-08 (S) Talent pool: keep rejected/silver-medalist candidates searchable for
future roles.
CAND-09 (M) Source tracking (career site, referral, LinkedIn, agency, manual).
CAND-10 (S) Manual candidate creation and bulk CV import.
CAND-11 (S) Blind-screening toggle hides name, photo, age/gender indicators.
3.7 Pipeline (PIPE)
PIPE-01 (M) Kanban board per job with drag-and-drop between stages; list-view
toggle.
PIPE-02 (M) Stage change logs who and when; required reason when rejecting.
PIPE-03 (S) Stage automation: auto-send email template on entering a stage (e.g.,
rejection, interview invite).
PIPE-04 (S) Stage-level counts, SLA aging indicators (days in stage).
3.8 CV Intelligence (CV)
CV-01 (M) Upload and store CV securely; inline PDF viewer in the profile.
CV-02 (M) Text extraction from PDF and DOCX; OCR fallback for scanned files.
CV-03 (M) Structured parsing: name, email, phone, location, links, skills, education,
work experience (company, title, dates), certifications, summary, total experience
years.
CV-04 (M) ATS-friendliness score (0–100) with itemized checks and fix suggestions
(Part 8).
CV-05 (M) JD match score (0–100) per application with breakdown: skills, experience,
education, title, location (Part 8).
CV-06 (M) Explanation: matched skills, missing required skills, extra skills, experience
gap, strengths and concerns.
CV-07 (M) Parsing runs asynchronously; UI shows status Pending, Processing, Done,
Failed; manual retry.
CV-08 (S) Recruiter can correct parsed fields; corrections are stored and the score
recalculated.
CV-09 (S) Semantic matching with embeddings in addition to keyword matching.
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 5 of 27

CV-10 (S) Re-score all candidates when job requirements change.
CV-11 (S) Candidate-facing feedback: optionally show applicants their CV ATS check
before submitting.
CV-12 (M) Scores never auto-reject; show disclaimer and score version.
3.9 Interviews (INT)
INT-01 (S) Create interview rounds (type, mode, duration, panel) and schedule with
date/time and meeting link.
INT-02 (S) Calendar invites (ICS now; Google/Outlook sync later); reschedule and
cancel.
INT-03 (S) Structured scorecards: competencies with 1–5 ratings, comments,
recommendation (Strong No … Strong Yes).
INT-04 (S) Interviewers cannot see others' feedback until they submit their own.
INT-05 (C) Candidate self-scheduling link from available slots.
INT-06 (S) Interview summary: aggregated ratings and debrief view.
3.10 Offers (OFFER)
OFFER-01 (S) Create an offer: CTC breakdown, designation, joining date, expiry.
OFFER-02 (S) Approval chain; statuses Draft, Pending Approval, Approved, Sent,
Accepted, Declined, Withdrawn.
OFFER-03 (S) Generate offer letter PDF from a template with variables.
OFFER-04 (C) E-signature integration.
OFFER-05 (S) Hired status closes an opening and marks the candidate ready for HRIS
handoff.
3.11 Communication (COMM)
COMM-01 (M) Email templates with variables ({{candidate_name}}, {{job_title}}, …)
and preview.
COMM-02 (M) Send email from the candidate profile; all emails logged on the
timeline.
COMM-03 (S) In-app notifications (bell icon) and email digests.
COMM-04 (C) Inbound reply capture.
3.12 Dashboard and Analytics (DASH)
DASH-01 (M) KPI cards: open jobs, total applicants, new this week, interviews today,
offers pending, hires this month.
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 6 of 27

DASH-02 (M) Charts: applications over time, funnel by stage, source breakdown,
applicants per job.
DASH-03 (S) Time-to-hire, time-in-stage, offer acceptance rate, recruiter
performance.
DASH-04 (S) Export CSV/XLSX. DASH-05 (C) Diversity analytics (aggregated only).
3.13 Admin and Compliance (ADM)
ADM-01 (M) Immutable audit log: who viewed/changed what and when.
ADM-02 (M) Consent records, data export for a candidate, and delete/anonymize on
request.
ADM-03 (S) Retention policy: auto-anonymize rejected candidates after N months.
ADM-04 (S) Global search (candidates, jobs) with Cmd/Ctrl+K.
4. Non-Functional Requirements
Area Requirement
Performance List APIs p95 under 500 ms for 100k candidates; CV
parse completes in under 30 s; UI interactions
under 200 ms feedback.
Scalability Stateless API behind a load balancer; workers scale
horizontally; DB indexes on all filter columns.
Security HTTPS only, OWASP Top 10 mitigations, input
validation, parameterized queries, CSRF/XSS
protection, secrets in env/vault, encryption at rest,
signed expiring URLs for CVs, malware scan on
upload.
Privacy PII minimization, consent logging, right to erasure,
field-level access, data residency configurable.
Availability 99.5% target; daily DB backups; tested restore.
Accessibility WCAG 2.1 AA, keyboard navigation, screen-reader
labels, color-contrast safe score colors.
Usability Responsive (desktop first, tablet OK, careers site
mobile first), light and dark theme.
Observability Structured logs, error tracking (Sentry), health
endpoints, request IDs.
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 7 of 27

5. Key User Flows
Flow A: Candidate applies. Open job page → fill form → upload CV → consent → submit →
API validates and stores the file → creates Candidate (or matches an existing one) and
Application → enqueues parse job → confirmation email → worker parses CV, computes
ATS and match scores → application appears in recruiter's Applied column with score
badge.
Flow B: Recruiter screens. Dashboard → Job → Kanban → click card → drawer shows
summary, score ring, matched/missing skills → shortlist (move to Screening) or reject with
reason → email auto-sent by template.
Flow C: Interview. Recruiter schedules a round → invites go to interviewer and candidate
→ interviewer opens assigned interview, reads CV and match analysis → submits
scorecard → recruiter sees aggregate → moves to the next stage or the Offer stage.
Flow D: Offer. Recruiter drafts an offer → hiring manager and HR approve → letter
generated and sent → candidate accepted → stage becomes Hired → job openings
decrement and the job auto-closes at zero.
Flow E: Erasure request. Admin opens candidate → Privacy tab → Export or Anonymize →
system removes PII and files, keeps anonymized stats, and writes an audit entry.
6. Architecture and Tech Stack
Chosen for speed of building with AI agents and enterprise scalability: a modular
monolith API plus an async worker, deployed with Docker.
[Next.js web app] --HTTPS--> [FastAPI API] --> [PostgreSQL + pgvector]
                                  |--> [Redis] <--> [Celery workers: CV 
parse, scoring, email]
                                  |--> [S3 / MinIO: CV files]
                                  |--> [SMTP / SES: email]
Area Requirement
Maintainability Typed code, 70%+ test coverage on services,
OpenAPI docs, linting, CI pipeline.
Auditability Every score stores model/version, inputs hash and
timestamp.
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 8 of 27

Repository layout (monorepo)
hr-portal/
  apps/
    web/                 # Next.js app
      app/(public)/      # careers site
      app/(portal)/      # authenticated HR portal
      components/ui/     # shadcn primitives
      components/        # feature components
      lib/ hooks/ types/
    api/                 # FastAPI app
Layer Choice Why
Frontend Next.js 14 (App Router), TypeScript,
Tailwind CSS, shadcn/ui, TanStack
Query, React Hook Form + Zod, dnd-
kit, Recharts, Lucide icons
Fast to scaffold, polished enterprise
look, SSR for the careers site
Backend Python 3.11, FastAPI, SQLAlchemy 2 +
Alembic, Pydantic v2
Typed, auto OpenAPI, same language
as the NLP/CV stack
Database PostgreSQL 16 + pgvector Relational integrity, JSONB for
parsed data, vector search later
Queue Redis + Celery CV parsing and scoring off the
request path
Storage S3-compatible (MinIO locally, S3 in
prod)
Scalable file storage, signed URLs
CV
parsing
pdfplumber / PyMuPDF, python-docx,
Tesseract OCR, spaCy, rule + skill
taxonomy; pluggable adapter for
Affinda/RChilli or an LLM
Start in-house and swap without
code churn
Matching Skill taxonomy with synonyms, TF-IDF,
sentence-transformers embeddings
Progressive accuracy
Auth JWT (access plus refresh in httpOnly
cookie), argon2
Standard; OIDC later
Infra Docker Compose (dev), GitHub
Actions CI, Nginx/Traefik, cloud
container service
Simple to start
Quality pytest, Playwright, ESLint, Ruff, pre-
commit
Agents need guardrails
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 9 of 27

      app/
        core/            # config, security, db, deps
        models/          # SQLAlchemy
        schemas/         # Pydantic
        routers/         # one file per module
        services/        # business logic
        workers/         # celery tasks
        cv_engine/       # extract, parse, ats_check, matcher
      alembic/ tests/
  docs/                  # this spec, ADRs
  docker-compose.yml
  .cursor/rules/         # agent rules (Part 11)
Layering rule: routers → services → repositories/models. Routers hold no business logic.
The CV engine is a pure Python package with no web dependencies so it is independently
testable.
7. Data Model
All tables have id  (UUID), created_at , updated_at ; soft-deletable where marked (SD).
All foreign keys indexed.
organizations: name, domain, settings (JSONB).
users: org_id, email (unique), password_hash, full_name, role (enum), is_active,
last_login_at, mfa_secret.
departments: org_id, name, head_user_id. locations: org_id, name, city, country.
requisitions: org_id, title, department_id, requested_by, headcount, budget_min/max,
justification, status, approved_by, approved_at.
jobs (SD): org_id, requisition_id?, title, slug (unique), department_id, location_id,
work_mode, employment_type, level, description, responsibilities, qualifications,
salary_min/max/currency, openings, status, closes_at, hiring_manager_id, created_by,
published_at, screening_questions (JSONB).
job_requirements: job_id, required_skills (JSONB [{name, weight}]), preferred_skills
(JSONB), min_experience, max_experience, education_level, certifications (JSONB),
weights_override (JSONB).
job_team: job_id, user_id, team_role (recruiter | interviewer | manager).
pipeline_stages: org_id, name, order, type (applied | screening | interview | offer | hired |
rejected | custom), is_default.
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 10 of 27

candidates (SD): org_id, first_name, last_name, email (unique per org), phone,
current_location, current_company, current_title, total_experience_years, current_ctc,
expected_ctc, notice_period_days, linkedin_url, portfolio_url, source, tags (text[]),
is_talent_pool, anonymized_at, consent_given_at, consent_version.
applications: candidate_id, job_id (unique together), stage_id, status (active | rejected |
withdrawn | hired), reference_no, rejection_reason, cover_letter, answers (JSONB),
applied_at, stage_entered_at, assigned_recruiter_id, is_shortlisted, overall_rating.
documents: candidate_id, application_id?, type (cv | cover_letter | offer | other),
file_name, mime_type, size, storage_key, checksum, is_primary, virus_scan_status.
parsed_profiles: document_id, candidate_id, parse_status (pending | processing | done |
failed), parser_version, raw_text, data (JSONB: skills[], education[], experience[],
certifications[], links[], summary), total_experience_years, confidence (JSONB),
corrected_data (JSONB), error.
ats_checks: document_id, score, checks (JSONB [{id, label, passed, weight, detail,
suggestion}]), engine_version.
match_results: application_id, overall_score, breakdown (JSONB {skills, experience,
education, title, location}), matched_skills[], missing_required[], missing_preferred[],
extra_skills[], explanation (JSONB), engine_version, inputs_hash, computed_at.
interviews: application_id, round_name, type (phone | technical | managerial | hr), mode
(video | onsite), scheduled_at, duration_min, meeting_link, location, status, created_by.
interview_panel: interview_id, user_id, feedback_submitted_at.
scorecard_templates: org_id, name, competencies (JSONB).
scorecards: interview_id, interviewer_id, ratings (JSONB), comments, recommendation,
submitted_at.
offers: application_id, designation, ctc_breakdown (JSONB), joining_date, expires_at,
status, approval_chain (JSONB), document_id?, sent_at, responded_at.
email_templates: org_id, key, subject, body_html, variables (text[]), trigger_stage_id?.
email_logs: candidate_id, application_id?, template_key, to, subject, body, status, sent_by,
sent_at.
notes: candidate_id, application_id?, author_id, body, mentions (uuid[]).
notifications: user_id, type, payload (JSONB), read_at.
activity_logs: candidate_id?, application_id?, actor_id, action, metadata (JSONB),
occurred_at.
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 11 of 27

audit_logs (append-only): actor_id, action, entity_type, entity_id, ip, user_agent, diff
(JSONB), occurred_at.
consent_records: candidate_id, purpose, version, granted_at, ip, withdrawn_at.
Key indexes: applications(job_id, stage_id), applications(candidate_id),
candidates(org_id, email), match_results(application_id), GIN on candidates.tags and
parsed_profiles.data, trigram index on candidate names, pgvector column embedding  on
parsed_profiles and jobs (added in the semantic-matching phase).
8. CV Intelligence Engine
Lives in apps/api/app/cv_engine/  as a pure Python package: extract.py , parser.py ,
skills.py , ats_check.py , matcher.py , explain.py . Executed by a Celery task
process_document(document_id) .
Pipeline
1. Validate: MIME and magic-byte check, size limit 5 MB, malware scan (ClamAV), page
count limit.
2. Extract text: PDF via pdfplumber, falling back to PyMuPDF; DOCX via python-docx; if
extracted text is under 200 characters, run Tesseract OCR and flag ocr_used .
3. Parse: section segmentation by headings, regex for email/phone/URLs/dates, spaCy
NER for names, orgs and locations, skill extraction against a taxonomy (synonym map
such as "JS" = "JavaScript", "k8s" = "Kubernetes"), experience date-range parsing to
compute total years (merging overlaps).
4. Normalize: canonical skill names, ISO dates, title normalization.
5. ATS check: run the checklist below on the file structure and parsed result.
6. Match: for each application on this candidate, compute the JD match.
7. Persist: write parsed_profiles , ats_checks , match_results ; update candidate
fields that are empty; emit an activity-log entry and a notification.
Parser adapter. Define CVParser  with parse(text, file) -> ParsedProfile . Ship
RuleBasedParser  first; later add AffinaParser , LLMParser  behind the same interface,
selected by config. If an LLM is used, validate its output against the Pydantic schema,
never send data to a provider without a privacy and DPA review, and log the parser
version.
8.1 ATS-friendliness checklist (score 0–100)
There is no universal ATS standard, so this is a documented heuristic. Each check has a
weight; the score is the weighted sum of passed checks.
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 12 of 27

Bands: 80–100 Good (green), 60–79 Needs improvement (amber), below 60 Poor (red).
Store the checks as JSON [{id, label, passed, weight, detail, suggestion}] .
8.2 JD match scoring (score 0–100)
Default weights (configurable per organization and overridable per job):
ID Check Weight Fail suggestion
A1 Text is extractable (not image-only
PDF)
15 Export as a text-based PDF or
DOCX
A2 Standard file type (PDF/DOCX) and
under 5 MB
5 Use PDF or DOCX
A3 Contact info parsed (name, email,
phone)
10 Put contact details in the body, not
the header/footer
A4 Standard section headings found
(Experience, Education, Skills)
15 Use conventional headings
A5 No multi-column or table layout
detected
10 Use a single-column layout
A6 No text boxes, images holding text,
or key info in headers/footers
8 Move content into the main body
A7 Dates consistently formatted and
parseable
7 Use "MMM YYYY – MMM YYYY"
A8 Work history has title, company and
dates per role
10 List title, company, dates on
separate clear lines
A9 Skills section present with
recognizable skills
7 Add a dedicated Skills section
A10 Reasonable length (1–4 pages) 5 Trim or condense
A11 No unusual characters, excessive
graphics, icons as bullets
4 Use standard bullets and fonts
A12 Parse completeness (share of
expected fields extracted)
4 Simplify the layout
Component Weight How computed
Required skills 40 matched required skills / total required (weighted
by skill weight); synonym-aware
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 13 of 27

overall = sum(component_score * weight) / 100 . Renormalize weights if a
component has no data (for example no preferred skills defined).
Hard filters (flags, not rejections): a missing mandatory requirement (for example a
mandatory certification or work authorization) shows a red flag chip but never auto-
rejects.
Progression: v1 keyword + synonym + TF-IDF; v2 adds sentence-transformer embeddings
(pgvector) for semantic skill and role similarity; v3 optional LLM to write the narrative
explanation (not to decide the score).
Explanation payload (stored in match_results.explanation ):
{
  "summary": "Strong match on backend skills; lacks Kubernetes and has 1.5 
years less experience than required.",
  "strengths": ["6 of 7 required skills", "Relevant fintech domain"],
  "concerns": ["No Kubernetes", "Notice period 90 days"],
  "component_scores": {"skills": 82, "experience": 65, "education": 100, 
"title": 74, "location": 90},
  "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
  "missing_required": ["Kubernetes"],
  "missing_preferred": ["Terraform"],
  "extra_skills": ["Go", "Kafka"],
  "score_version": "match-1.0"
}
Fairness and governance. Never use name, gender, age, photo, nationality or address as
features. Offer a blind-review toggle. Log engine version and input hash. Display "Score is
advisory; a recruiter makes the decision". Plan an annual bias review of score distributions
across groups where legally permitted.
Component Weight How computed
Preferred skills 10 matched preferred / total preferred
Experience 20 100 if within [min, max]; linear penalty below min;
mild penalty above max; also relevant-role-years
via title similarity
Title / domain relevance 10 similarity between candidate titles and job title
(TF-IDF now, embeddings later)
Education and
certifications
10 level meets requirement; certifications matched
Location / notice period 10 work-mode compatibility; notice period vs. target
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 14 of 27

Quality testing. Build a golden set of 50–100 CVs with hand-labeled fields; track parser
precision/recall per field in CI; fail the build if accuracy drops below thresholds.
9. API Specification (REST, /api/v1 )
All responses JSON; errors use { "error": { "code", "message", "details" } } ; list
endpoints accept page , page_size , sort , q  and filters, and return { items, total,
page, page_size } . Auth via Authorization: Bearer <JWT>  or an httpOnly cookie.
OpenAPI is auto-generated at /docs .
Module Endpoints
Auth POST /auth/login , /auth/refresh ,
/auth/logout , /auth/forgot-password ,
/auth/reset-password , GET /auth/me
Users GET/POST /users , GET/PATCH/DELETE
/users/{id} , PATCH /users/{id}/role
Org setup /departments , /locations , /pipeline-stages ,
/email-templates , /scorecard-templates
(standard CRUD)
Requisitions GET/POST /requisitions , PATCH
/requisitions/{id} , POST
/requisitions/{id}/approve , /reject ,
/convert-to-job
Jobs GET/POST /jobs , GET/PATCH/DELETE /jobs/{id} ,
POST /jobs/{id}/publish , /close , /clone , PUT
/jobs/{id}/requirements , PUT
/jobs/{id}/team , POST /jobs/extract-skills
Public careers GET /public/jobs , GET /public/jobs/{slug} ,
POST /public/jobs/{slug}/apply  (multipart,
CAPTCHA token)
Candidates GET/POST /candidates , GET/PATCH
/candidates/{id} , POST
/candidates/{id}/anonymize , GET
/candidates/{id}/export , POST
/candidates/bulk
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 15 of 27

Module Endpoints
Applications GET /applications , GET /applications/{id} ,
PATCH /applications/{id}/stage , POST
/applications/{id}/reject , /shortlist ,
/withdraw , POST /applications/bulk-action
Kanban GET /jobs/{id}/board  (stages with application
cards and counts)
Documents POST /candidates/{id}/documents , GET
/documents/{id}/download-url  (signed,
expiring), DELETE /documents/{id}
CV analysis GET /applications/{id}/analysis  (parsed
profile, ATS check, match), POST
/documents/{id}/reprocess , PATCH /parsed-
profiles/{id}  (corrections), POST
/jobs/{id}/rescore
Notes and timeline GET/POST /candidates/{id}/notes , GET
/candidates/{id}/timeline
Interviews GET/POST /interviews , PATCH
/interviews/{id} , POST
/interviews/{id}/cancel , GET
/interviews/mine , POST
/interviews/{id}/scorecard , GET
/applications/{id}/scorecards
Offers GET/POST /offers , PATCH /offers/{id} , POST
/offers/{id}/submit , /approve , /send ,
/accept , /decline
Email POST /emails/send , GET
/candidates/{id}/emails , POST
/emails/preview
Notifications GET /notifications , PATCH
/notifications/{id}/read , POST
/notifications/read-all
Analytics GET /analytics/overview , /funnel , /sources ,
/time-to-hire , /recruiters , GET
/analytics/export
Search GET /search?q=  (candidates and jobs)
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 16 of 27

Conventions: UUID ids; UTC ISO-8601 timestamps; idempotent PATCH; optimistic stage
moves on the board with server reconciliation; rate limits of 5 applications per IP per hour
on the public apply endpoint and 100 requests per minute per user elsewhere.
10. UI / UX Specification
Look and feel. Clean, calm enterprise style similar to Workday, Greenhouse and Lever: lots
of whitespace, subtle borders, restrained color, clear hierarchy.
Design tokens
Font: Inter (UI), JetBrains Mono (IDs/code). Radius 8 px for cards and 6 px for inputs; 4 px
spacing grid; soft shadows only on popovers and the dragged card.
Portal layout. Collapsible left sidebar (Dashboard, Jobs, Candidates, Interviews, Offers,
Analytics, Talent Pool, Settings), top bar with global search (Ctrl/Cmd+K), notification
bell, theme toggle and user menu; breadcrumbs and page title with primary action at top
right.
Screens
Module Endpoints
Admin GET /audit-logs , GET /consents , POST
/retention/run
Candidate portal POST /portal/magic-link , GET
/portal/applications , POST
/portal/applications/{id}/withdraw
Token Light Dark
Primary Indigo 600 #4F46E5 Indigo 400
Background #F8FAFC #0B1220
Surface (cards) #FFFFFF #111A2E
Border #E2E8F0 #1E293B
Text #0F172A  / muted #64748B #E2E8F0  / #94A3B8
Success / Warning / Danger #16A34A  / #D97706  / #DC2626 lighter tints
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 17 of 27

# Screen Key contents
1 Login Email/password, SSO button, forgot password
2 Dashboard KPI cards, applications trend, funnel, source donut,
today's interviews, tasks, recent applicants
3 Jobs list Table with status chips, applicants count, filters,
create job button
4 Job create/edit Stepper: Basics, Description, Requirements (skill
chips with weights), Team, Pipeline, Review and
Publish
5 Job detail Tabs: Pipeline (Kanban), Applicants (table), Details,
Team, Analytics
6 Kanban board Stage columns with counts, candidate cards
(avatar, name, title, score ring, days in stage, tags),
drag-and-drop, quick filters
7 Candidate drawer Header with score ring and stage dropdown;
summary, top skills, quick actions (shortlist, reject,
email, schedule)
8 Candidate profile Tabs: Overview, CV (PDF viewer beside parsed
data), Match Analysis, Timeline, Interviews, Notes,
Emails, Documents, Privacy
9 Match Analysis tab Overall score ring; component bars; matched skills
(green chips), missing required (red), missing
preferred (amber), extra skills (gray); strengths
and concerns; ATS-friendliness card with checklist
and fix suggestions; score version and disclaimer
10 Candidates list Global table with filters, saved views, bulk actions,
compare
11 Compare 2–4 candidates in columns across scores, skills,
experience, ratings
12 Interviews Calendar and list; my-interviews for interviewers;
scorecard form
13 Offers Table and offer editor with approval stepper
14 Analytics Funnel, time-to-hire, source effectiveness,
recruiter leaderboard, date range filter, export
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 18 of 27

Component and interaction standards
Reusable: DataTable  (server-side sort, filter, pagination, column chooser),
KanbanBoard , ScoreRing , SkillChips , StatusBadge , FileDropzone , PdfViewer ,
Timeline , EmptyState , ConfirmDialog , CommandPalette , StatCard .
Every page has loading skeletons, empty states with a call to action, and friendly error
states with retry.
Forms: inline validation, autosave drafts for long forms (job editor), unsaved-changes
warning.
Score color mapping: 80+ green, 60–79 amber, under 60 red; always paired with the
number and an icon so color is never the only signal.
Toasts for success, and undo on stage moves and rejections where possible.
Keyboard shortcuts: /  focus search, j/k  move between candidates, s  shortlist, r
reject (with confirmation).
Accessibility: visible focus rings, ARIA roles on the Kanban (with keyboard move
alternative), contrast 4.5:1 minimum.
11. Cursor Playbook
11.1 Setup before you prompt
1. Create the repo and folders from Part 6. Save this document as docs/SPEC.md
(export Markdown from this doc). Also split Parts 3, 7, 8, 9, 10 into
docs/requirements.md , docs/data-model.md , docs/cv-engine.md , docs/api.md ,
docs/ui.md  so agents can @ -reference only what they need.
2. Add the rules files below to .cursor/rules/ .
3. Work in small vertical slices, one branch per slice, one agent task per prompt. Review
diffs, run tests, commit, then continue. Never ask one agent to "build the whole
portal".
# Screen Key contents
15 Settings Users and roles, departments, pipeline stages,
email templates, scoring weights, scorecard
templates, retention, audit log
16 Careers site Hero with search, filter sidebar, job cards, job
detail, multi-step apply form with CV drop zone
and progress, success page
17 Candidate portal Magic-link login, application status tracker
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 19 of 27

4. Use Plan mode first for each slice: ask the agent to propose the file list and approach,
approve it, then let it implement.
11.2 .cursor/rules/project.mdc  (always apply)
You are building an enterprise HR Recruitment Portal (ATS). Source of truth: 
@docs/SPEC.md
and the split docs in /docs. Do not invent features; reference requirement 
IDs (e.g. CV-05).
Stack: Next.js 14 App Router + TypeScript + Tailwind + shadcn/ui + TanStack 
Query +
React Hook Form + Zod (apps/web); FastAPI + SQLAlchemy 2 + Alembic + Pydantic 
v2 +
Celery/Redis + PostgreSQL (apps/api).
General rules:
- TypeScript strict mode. No `any`. Python fully type-hinted; Ruff + mypy 
clean.
- Backend layering: router -> service -> model. No business logic in routers.
- Every endpoint: Pydantic request/response schemas, auth dependency, RBAC 
check,
  record-level access check, and an audit/activity log entry for mutations.
- Never put secrets in code; use environment variables and .env.example.
- Every migration through Alembic. Never edit the DB by hand.
- Write tests with each feature: pytest for services/routers, Playwright for 
critical flows.
- The CV engine must stay a pure Python package (no FastAPI imports).
- AI/match scores are advisory: never auto-reject or auto-advance candidates.
- Never use name, gender, age, photo, or nationality as a scoring feature.
- Handle PII carefully: no PII in logs, signed URLs for files, consent 
recorded.
- Small, focused commits; explain assumptions in the PR description.
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 20 of 27

11.3 .cursor/rules/frontend.mdc  (globs: apps/web/** )
- Use shadcn/ui primitives and the design tokens in @docs/ui.md (indigo 
primary, Inter).
- Server state with TanStack Query; no data fetching in useEffect. Typed API 
client in lib/api.
- Forms: React Hook Form + Zod schema shared with API types.
- Every page has loading skeleton, empty state, and error state.
- Accessibility: labels, focus rings, keyboard support, contrast 4.5:1.
- Score colors: >=80 green, 60-79 amber, <60 red, always with number + icon.
- Components are small, reusable, and live in components/{ui,feature}.
- Support light and dark mode via CSS variables.
11.4 .cursor/rules/backend.mdc  (globs: apps/api/** )
- Async SQLAlchemy sessions via dependency; repository helpers for queries.
- Pagination, sorting and filtering via a shared helper; always index filter 
columns.
- Uploads: validate MIME + magic bytes, size limit, store to S3/MinIO, signed 
URLs only.
- Long work (parse, score, email) goes to Celery; endpoints return quickly.
- Errors use the standard error envelope in @docs/api.md.
- Use a request-id middleware and structured logging.
11.5 Agent roles (use separate Cursor chats / background agents)
Run the Backend and Frontend agents in parallel once the API contract (Part 9) and
OpenAPI spec exist; generate the TypeScript client from openapi.json  so both sides
stay in sync.
Agent Owns Context to attach
Architect Repo scaffold, Docker Compose, config, CI Parts 6, 4
Backend Models, migrations, routers, services, tests Parts 3, 7, 9
CV Engine cv_engine  package and Celery tasks Part 8, golden CV set
Frontend Pages, components, API client Parts 10, 9
QA / Security Tests, Playwright, security review, seed data Parts 4, 5
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 21 of 27

11.6 Copy-paste prompts, in build order
Each prompt assumes the rules files and docs are already in the repo. Start every prompt
with: "Read @docs/SPEC.md. Plan first, list the files you will create, wait for my approval,
then implement."
Prompt 1: Scaffold (Architect)
Create the monorepo per Part 6: apps/web  (Next.js 14, TS, Tailwind, shadcn/ui,
TanStack Query) and apps/api  (FastAPI, SQLAlchemy 2, Alembic, Pydantic v2,
Celery, Redis). Add docker-compose.yml  with Postgres 16 (pgvector image), Redis,
MinIO, the API, a Celery worker, and the web app. Add .env.example , Makefile
( make up , make migrate , make test , make seed ), health endpoint /health , pre-
commit (ruff, mypy, eslint, prettier), and a GitHub Actions workflow running lint and
tests. Everything must start with docker compose up .
Prompt 2: Auth and RBAC (Backend)
Implement AUTH-01, 02, 03, 06 and ORG-02. Models: organizations, users. JWT
access (15 min) and refresh (7 days, httpOnly cookie), argon2 hashing, login lockout
after 5 failures, password reset tokens, a require_roles(...)  dependency, and a
record-level access helper. Add a seed script that creates one org and one user per
role. Include pytest tests for login, refresh, role enforcement and lockout.
Prompt 3: Data model and migrations (Backend)
Implement every table in Part 7 as SQLAlchemy 2 models with an initial Alembic
migration. Include enums, FKs, unique constraints, indexes, soft delete mixin, and
timestamps mixin. Add a seed for default pipeline stages, email templates,
departments and 3 sample jobs with requirements. Do not write routers yet.
Prompt 4: App shell and design system (Frontend)
Build the portal shell per Part 10: collapsible sidebar, top bar with global search
placeholder, notification bell, theme toggle and user menu; login page; protected
routes with role-based nav. Create design tokens, and reusable DataTable ,
StatCard , StatusBadge , EmptyState , ConfirmDialog , ScoreRing , SkillChips .
Use mock data. Add a /dev/components  page showing all of them in light and dark
mode.
Prompt 5: Jobs module (Backend then Frontend)
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 22 of 27

Backend: JOB-01 to JOB-06 and ORG-01 endpoints from Part 9 with filters,
pagination, publish and close, requirements, team, and tests. Frontend: Jobs list and
the 6-step job create/edit stepper with skill chips and weights, plus Job detail shell.
Generate the TS API client from OpenAPI and use it.
Prompt 6: Careers site and apply (Backend then Frontend)
Implement APPLY-01 to 05 and APPLY-07. Public endpoints for listing, detail and apply
(multipart). Validate and store the CV in MinIO, create or reuse the Candidate by
email, create the Application at the first stage, record consent, enqueue a
process_document  task (stub for now), and send a confirmation email via a
templated mail service (console/MailHog in dev). Frontend: SEO-friendly public
careers pages and a multi-step apply form with drag-and-drop CV upload, validation,
CAPTCHA placeholder and a success page. Add rate limiting.
Prompt 7: Candidates and pipeline (Backend then Frontend)
Implement CAND-01 to 05, 09 and PIPE-01 to 02. Backend: candidates list with all
filters, application stage change with activity log and rejection reason, notes,
timeline, signed document download URLs. Frontend: Kanban board with dnd-kit
(optimistic moves), table view toggle, candidate drawer, and the candidate profile
with tabs (Overview, CV with PDF viewer, Timeline, Notes). Leave the Match Analysis
tab with a placeholder.
Prompt 8: CV engine, extraction and parsing (CV Engine)
Implement cv_engine  per Part 8 steps 1–4 as a pure Python package: extract.py
(pdfplumber, PyMuPDF fallback, python-docx, Tesseract OCR fallback), parser.py
( CVParser  interface plus RuleBasedParser  with section segmentation, regex,
spaCy NER, experience-years computation with overlap merging), and skills.py
(taxonomy of at least 500 skills with synonyms in a JSON file). Output the Pydantic
ParsedProfile . Write unit tests and a script that evaluates field precision/recall on
the CVs in tests/golden/ .
Prompt 9: ATS check and matcher (CV Engine)
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 23 of 27

Implement ats_check.py  with checks A1–A12 and weights from Part 8.1 returning
score, checks and suggestions; implement matcher.py  with the weighted
components in Part 8.2, renormalization, hard-filter flags, and explain.py  producing
the explanation JSON. Wire the Celery task process_document  to run extract, parse,
ats_check and match, persist parsed_profiles , ats_checks , match_results ,
update status, retries with backoff, and log failures. Add the endpoints GET
/applications/{id}/analysis , POST /documents/{id}/reprocess , POST
/jobs/{id}/rescore . Tests for each component.
Prompt 10: Match Analysis UI (Frontend)
Build the Match Analysis tab and the list/Kanban score badges per Part 10 screen 9:
score ring, component bars, matched/missing/extra skill chips, strengths and
concerns, ATS checklist card with suggestions, processing/failed states with retry,
advisory disclaimer, and score version. Add score and skill filters to the candidate list.
Add parsed-data correction (CV-08) with automatic re-score.
Prompt 11: Email, notifications, dashboard (Backend then Frontend)
Implement COMM-01 to 03, PIPE-03 (stage-triggered templates), and DASH-01 to 02
with analytics endpoints and Recharts dashboard (KPI cards, trend, funnel, sources,
today's interviews). Email composer on the candidate profile with template variables
and preview; in-app notifications with a bell dropdown.
Prompt 12: Interviews and scorecards
Implement INT-01 to 04 and INT-06: schedule interviews with panel, ICS invite email,
my-interviews page for interviewers (record-level access), scorecard form built from
templates, hidden-until-submitted feedback rule, and an aggregated summary on the
candidate profile.
Prompt 13: Offers and requisitions
Implement REQ-01 to 03 and OFFER-01 to 03, 05: requisition approval workflow,
convert to job, offer editor with approval chain, offer letter PDF generation from a
template, and hire flow that decrements openings and auto-closes the job.
Prompt 14: Compliance, audit, hardening (QA / Security)
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 24 of 27

Implement ADM-01 to 04: append-only audit log middleware, candidate data export,
anonymize/erase flow, retention job, consent records, global Ctrl+K search. Then do a
security review against OWASP Top 10: dependency audit, headers (CSP, HSTS),
CORS, input validation, file-upload hardening, rate limits, and secrets. Produce
docs/security-review.md  listing findings and fixes.
Prompt 15: Tests and polish (QA)
Add Playwright end-to-end tests for: candidate applies, recruiter sees scored
candidate, drag to stage, reject with reason, interviewer submits scorecard, offer
approved. Add a load test script for candidate list and apply endpoints. Fix
accessibility issues found with axe. Update README with setup and architecture
notes.
11.7 Tips for working effectively with the agents
Keep each prompt scoped to 1–2 modules and name requirement IDs.
After each slice run make test  and the app yourself; do not accept code you have
not run.
Ask agents to explain non-obvious decisions in comments and ADRs ( docs/adr/ ).
When an agent drifts, point it back to the doc: "Re-read @docs/api.md section X and
align."
Commit the generated OpenAPI file; regenerate the TS client in CI and fail on drift.
Keep a docs/DECISIONS.md  with answers to the open questions below, and update
the spec when they change.
12. Delivery Roadmap
Sprint (1 week each for a
solo dev with agents)
Slice Prompts Demo outcome
1 Scaffold, auth,
data model
1–3 Login works for all roles; DB
and Docker up
2 App shell, jobs 4–5 Create and publish a job from
the portal
3 Careers site and
apply
6 A candidate applies with a CV;
confirmation email arrives
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 25 of 27

Fast demo path for your senior (about 3 weeks): Prompts 1–7 and 8–10 with a trimmed
scope: auth, jobs, careers apply, Kanban, CV parsing, ATS check, match analysis. This
covers the core of your assignment and is the best thing to show first.
13. Risks and Mitigations
Sprint (1 week each for a
solo dev with agents)
Slice Prompts Demo outcome
4 Candidates and
Kanban
7 Recruiter reviews applicants
and drags through stages
5 CV engine 8–9 CV parsed; ATS score and JD
match computed
6 Match UI 10 Full "wow" demo: apply, parse,
score, explain
7 Email, dashboard 11 KPIs, charts, templated emails
8 Interviews 12 Scheduling and scorecards
9 Offers and
requisitions
13 End-to-end hire
10 Compliance,
security, tests
14–15 Pilot-ready build
Risk Mitigation
CV parsing accuracy is poor on messy
layouts
Golden test set, parser adapter allowing a
commercial parser or LLM, recruiter correction
UI
Biased or unexplained scoring Advisory-only scores, no sensitive features,
explanation and versioning, periodic audits
PII leakage Signed URLs, no PII in logs, encryption, RBAC
plus record-level access, audit logs
Malicious uploads MIME/magic-byte checks, ClamAV, size limits,
sandboxed parsing worker
Agent-generated code drifts or has bugs Small slices, strict rules files, tests per slice,
code review of every diff
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 26 of 27

14. Open Questions to Confirm With Your Senior
1. Single company (internal HR) or multi-tenant for multiple client companies?
2. Expected applicants per month and number of concurrent recruiters?
3. Is there an existing HRIS, email system, or SSO provider to integrate with?
4. Which countries and legal regimes apply (GDPR, DPDP Act, others)?
5. Build the parser in-house or buy a commercial parsing API? Is sending CV data to
external AI providers allowed?
6. Where will it be hosted (cloud provider, on-premise)?
7. Branding: logo, colors, careers site domain?
8. Which interview and offer steps are mandatory in your company's process?
Default assumptions used in this document if unanswered: single company, up to 5,000
applications per month, cloud-hosted, English only, in-house rule-based parser with an
adapter for a commercial one, email/password auth with SSO later.
15. Glossary
ATS: Applicant Tracking System. Requisition: an approved request to hire. JD: job
description. Pipeline: ordered stages a candidate moves through. Scorecard: structured
interviewer feedback form. Silver medalist: strong candidate not hired, kept in the talent
pool. RBAC: role-based access control. DPDP: India's Digital Personal Data Protection Act.
Blind screening: hiding identity details to reduce bias. CTC: cost to company (annual
compensation).
Risk Mitigation
Scope creep MoSCoW priorities; MVP is all M items; track
extras in a backlog
Legal compliance unclear Confirm GDPR / DPDP / local labor-law
requirements with legal before go-live
HR Recruitment Portal (ATS) — Speciﬁcation Pack
Page 27 of 27

