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
