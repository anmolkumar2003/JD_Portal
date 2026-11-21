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
