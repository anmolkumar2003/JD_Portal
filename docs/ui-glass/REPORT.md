# Modern Glass UI — `ui/glass` review report

**Branch:** `ui/glass` (not merged)  
**Scope:** Visual / layout polish only — no API, route, permission, or behaviour changes.

## Commits (numbered steps)

1. `2b97665` — design system tokens + Tailwind  
2. `ffcc6a1` — shared components  
3. `801b385` — portal layout shell  
4. `86bafbf` — existing screens  
5. `75fd009` — a11y / performance polish  
6. (this report + verification)

## Design system

- Light: pale blue → lavender fixed mesh; primary indigo `#4F46E5` → violet `#7C3AED`
- Dark: deep navy → indigo mesh; glass at ~8–12% white
- `.glass` (blur 16px, saturate 140%): sidebar, top bar, dashboard KPI cards, dialogs, drawers, command palette, bulk bar, auth cards
- `.glass-strong` (no blur): tables, forms, Kanban columns, CV viewer, Match surfaces, settings content
- Fallbacks: `@supports not (backdrop-filter)`, `prefers-reduced-transparency`, `prefers-reduced-motion`
- Inter via existing `--font-inter` stack; tabular nums utility; 4px grid; 20px cards / 12px controls / pill radii

## Screens restyled (existing routes only)

| Screen | Notes |
|--------|--------|
| Login / Forgot / Reset / Change password | Glass auth card on mesh |
| Portal shell | Grouped Recruitment / Admin nav, ⌘K search pill, glass sidebar/top bar, mobile drawer |
| Dashboard | Glass KPI cards, charts on strong cards, theme chart colors |
| Jobs list / detail / Pipeline / edit / new | PageHeader, glass-strong table, Kanban snap + Move-to |
| Candidates list / new / detail / compare | PageHeader, filters, bulk glass bar |
| Settings (account, org, scoring, users, departments) | Glass pill nav + strong content panel |
| Careers public (feature-gated) | Glass header/job cards when enabled |
| 404 / global error | New glass error/not-found pages |

## Skipped (not in this codebase)

- Two-factor setup / verification / backup codes (no existing pages)
- Session-expired dedicated page (handled by login redirect)
- Email templates settings UI
- Full notifications list page (dropdown only)
- Dedicated 403 / 500 route pages (global `error.tsx` covers runtime failures)
- New KPIs requiring new API fields (shortlisted count, avg match, department donut, needs-attention table) — kept existing analytics endpoints
- Job create “stepper” UX rewrite — existing form sections only restyled via shared controls
- Compact/comfortable table density toggle & column chooser — not previously present; not added (behaviour change)
- axe automated scan & Playwright 4× CPU throttle — not run in this session; recommend on review
- Full before/after screenshot matrix at all 5 viewports × light/dark — use `make test-e2e-screenshots` with output redirected to `docs/ui-glass/` when E2E stack is up

## Compromises

- **Blur:** capped at **16px** (within 16–20) for scroll/Kanban smoothness; glass-strong has **no** blur on data surfaces
- **Dashboard widgets:** visual polish on existing Recharts; custom SVG funnel/bubbles / sparkline KPI extras deferred to avoid inventing data
- **Careers:** still 404 when `public_careers` feature flag is off (unchanged behaviour)

## Verification run locally

- `npm run lint` — pass  
- `npm run typecheck` — pass  
- pytest / Playwright full suite — **not run** here (Docker e2e + disk); please run `make test-api` and `make test-e2e` on review

## What to check by hand

1. Light + dark on Dashboard, Jobs, Candidates, Pipeline, Candidate profile, Settings  
2. Mobile 390px: drawer nav, table scroll, Kanban snap + Move-to menu (keyboard)  
3. ⌘K / search pill opens command palette  
4. Dialogs / reject / PDF export still function  
5. Contrast of muted text on glass in both themes  
6. Rebuild prod `web` from this branch only after you merge/approve  

## Screenshot placeholders

Save captures under `docs/ui-glass/` as:

`{viewport}-{theme}-{slug}.png`  
Viewports: `390x844`, `844x390`, `820x1180`, `1280x800`, `1920x1080`  
Themes: `light`, `dark`  
Suggested slugs: `login`, `dashboard`, `jobs`, `pipeline`, `candidates`, `candidate-detail`, `settings-users`
