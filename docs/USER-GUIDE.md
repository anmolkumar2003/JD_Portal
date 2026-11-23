# HR Portal — user guide

This guide is for **HR administrators, recruiters, and hiring managers** using the internal portal. Candidates do not sign in unless you later enable the optional public careers module.

## Sign in and account security

1. Open your organization URL (e.g. `https://portal.example.com/login`).
2. Sign in with the email and password from your administrator.
3. If you were given a temporary password, you are prompted to choose a new one on first sign-in.
4. Use **Forgot password** on the login page if you need a reset link by email.

![Login screen](screenshots/login.png)  
*Placeholder — add `docs/screenshots/login.png` after go-live.*

Administrators create additional users under **Settings → Users** (roles: `hr_admin`, `super_admin`, `recruiter`).

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
2. Fill profile fields; salary fields support currency and per-annum/per-month.
3. Drop one or more CVs (PDF or DOCX, max 5 MB). Parsed fields show a **from CV** badge when autofill ran.
4. Fix duplicate email/phone warnings before saving.
5. Drafts autosave in your browser until you submit.

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

![Candidate profile](screenshots/candidate-profile.png)

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

- Super admins can export or anonymize a candidate record for compliance requests (when those APIs are enabled).
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