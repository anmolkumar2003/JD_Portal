# HR Portal — user guide

This guide is for **HR administrators, recruiters, and hiring managers** using the internal portal. Candidates do not sign in unless you later enable the optional public careers module.

## Sign in and account security

1. Open your organization URL (e.g. `https://portal.example.com/login`).
2. Sign in with the email and password from your administrator.
3. If you were given a temporary password, you are prompted to choose a new one on first sign-in.
4. Use **Forgot password** on the login page if you need a reset link by email.

![Login screen](screenshots/login.png)  
*Placeholder — add `docs/screenshots/login.png` after go-live.*

Administrators create additional users under **Settings → Users**. The portal is HR-only: new accounts are **HR Admin** or **Super Admin**. To remove an account entirely, ask your technical team to run `make remove-user EMAIL=…` (it is audited and never removes the last active admin).

## Navigation

The left sidebar includes:

- **Dashboard** — overview metrics (when charts are enabled in your build).
- **Jobs** — open roles and pipelines.
- **Candidates** — search, filters, and bulk actions.
- **Settings** — organization name, departments, users, scoring weights, and optional modules.

Use **Cmd/Ctrl+K** for the command palette (quick jump to jobs, candidates, settings).

![Portal layout](screenshots/portal-layout.png)

## Jobs

### List and filters

Open **Jobs** to see active and draft roles. Use filter chips to narrow by status or department.

![Jobs list](screenshots/jobs-list.png)

### Create or edit a job

1. Click **Create job** (or open an existing job → **Edit**).
2. Complete basics (title, department, location, salary band).
3. Add description and **required/preferred skills** with weights.
4. Assign recruiters and publish when ready.

![Job editor](screenshots/job-editor.png)

### Pipeline (Kanban)

Each job has a **Pipeline** tab: drag cards between stages (Applied, Screening, Interview, Offer, Hired, Rejected). Stage moves can trigger email templates configured by your admin.

![Kanban board](screenshots/kanban.png)

## Candidates

### Search and saved filters

On **Candidates**, use the search bar and filter popover (skills, score, department, tags, dates). Name a filter set and save it for reuse; shared filters appear for your team.

![Candidate filters](screenshots/candidate-filters.png)

### Add candidate manually

1. **Candidates → Add candidate**.
2. Drop one or more CVs (PDF or DOCX, max 5 MB). Files go to a temporary draft area (not a candidate record) and are parsed for preview. Parsed fields show a **from CV** badge when autofill ran.
3. Review and edit the form. Required fields (marked with *): first name, last name, email, phone, and job. Department comes from the job. **Save** stays disabled until every required field is valid.
4. Fix duplicate email/phone warnings (open the existing candidate, attach the CV there, or cancel) before saving.
5. On save, draft files move to permanent storage, the candidate and application are created, and parsing / ATS / match scoring are queued. Cancel or leaving the page deletes unused draft files (you get an unsaved-changes warning). Expired drafts are removed after 24 hours.
6. With multiple CVs, use the review table: incomplete rows cannot be saved with **Save all**; use **Save complete rows** to save only valid ones.

![Add candidate form](screenshots/add-candidate.png)

### Candidate profile

Open a candidate to see tabs:

| Tab | Purpose |
| --- | ------- |
| **Overview** | Summary, tags, budget badge, quick actions |
| **CV** | Viewer plus parsed-data corrections |
| **Match analysis** | Advisory scores vs the job description (not a hiring decision) |
| **Notes** | @mention colleagues |
| **Interviews** | Simple ratings where enabled |

Use **Move to** or **Reject** with an optional reason. **Email** opens the composer with templates.

**HR administrators** (`hr_admin`, `super_admin`) can open the **Actions** menu (top right of the profile, next to Download PDF summary) to **Anonymize** (scrub personal details, keep applications and documents) or **Delete candidate** (permanent). Delete asks you to type the candidate’s full name, lists what will be removed, and cannot be undone. The same roles can **Delete** from the bulk toolbar (type `DELETE` to confirm). Recruiters and other roles never see these controls. Deletion is audited with row counts only — never name, email, or phone.

**HR administrators** can also **Download PDF summary** from the profile header (or from the bulk toolbar for several candidates at once — one PDF each, as a ZIP). A short dialog chooses whether to include contact details (on by default), salary details (off), and HR notes (off). The PDF is one to two A4 pages with organization branding, scores, interview ratings, and a note that scores are advisory. Files are generated on the fly and not stored on the server; the export is written to the audit log without personal data.

![Candidate profile](screenshots/candidate-profile.png)

### Export Excel

On **Candidates**, administrators use **Export Excel** to download the current search and filters (or only the checked rows), up to 5,000 applications. Beyond that limit the portal asks you to narrow the filters. The workbook has a frozen header row, filters, and a second sheet with the generated date and which filters were used. Formula-looking values are escaped so spreadsheets do not execute them.

### Compare

Select two to four candidates and open **Compare** for side-by-side scores and skills.

![Compare candidates](screenshots/compare.png)

## Scoring

Match and interview scores are **advisory**. Adjust weights under **Settings → Scoring** (default 50% match / 50% interview rating). The final score panel on each profile reflects those weights.

![Scoring settings](screenshots/scoring-settings.png)

## Settings (administrators)

- **Organization** — display name and logo (`ORG_NAME` fallback until set).
- **Departments** — maintain the department list used on jobs and candidates.
- **Users** — create accounts, reset passwords, change roles, deactivate users.
- **Feature modules** — optional careers site, interviews, offers, requisitions, and audit UI are controlled by server configuration; contact your technical owner to enable.

![Settings users](screenshots/settings-users.png)

## Privacy and data handling

- `hr_admin` and `super_admin` can export, anonymize, or permanently delete a candidate. Permanent delete removes applications, documents, scores, notes, interviews, emails, notifications and related files; audit logs keep who deleted and counts only (no personal data).
- Draft CV uploads before save never create a candidate; unused draft files expire after 24 hours.
- PDF summaries and Excel list exports are limited to `hr_admin` and `super_admin`, audited (who exported, how many rows — no emails or notes in the audit payload), and streamed for download only (not kept on the server).
- Uploaded CVs may be virus-scanned in production; infected files are rejected at upload.
- Rejected-candidate retention (automatic anonymization after N days) is configured by your technical team and is off by default.

## Getting help

- **Password issues** — use forgot password or ask an `hr_admin` to reset your account under Settings → Users.
- **Missing jobs or candidates** — recruiters only see jobs they are assigned to; `hr_admin` sees the full org.
- **Technical incidents** — share the time of the issue and any **Request ID** from the browser network tab with your platform team.

## Screenshot checklist

Add PNG captures under `docs/screenshots/` for:

- `login.png`
- `portal-layout.png`
- `jobs-list.png`
- `job-editor.png`
- `kanban.png`
- `candidate-filters.png`
- `add-candidate.png`
- `candidate-profile.png`
- `compare.png`
- `scoring-settings.png`
- `settings-users.png`