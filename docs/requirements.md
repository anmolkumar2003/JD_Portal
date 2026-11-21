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
