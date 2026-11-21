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
