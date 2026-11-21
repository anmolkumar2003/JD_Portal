import type { ReactNode } from "react";

import { SkillChips } from "@/components/skill-chips";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  EMPLOYMENT_TYPE_LABELS,
  TEAM_ROLE_LABELS,
  WORK_MODE_LABELS,
  formatDate,
  formatExperience,
  formatSalary,
} from "@/lib/labels";
import type { Job } from "@/types/api";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}

function Prose({ text, fallback }: { text: string | null; fallback: string }) {
  if (!text?.trim()) return <p className="text-sm text-muted-foreground">{fallback}</p>;
  return <p className="whitespace-pre-line text-sm leading-relaxed">{text}</p>;
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm">{value || "—"}</dd>
    </div>
  );
}

export function JobDetails({ job }: { job: Job }) {
  const req = job.requirements;

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <Card>
          <CardContent className="space-y-6 pt-6">
            <Section title="Description">
              <Prose text={job.description} fallback="No description yet." />
            </Section>
            <Section title="Responsibilities">
              <Prose text={job.responsibilities} fallback="Not specified." />
            </Section>
            <Section title="Qualifications">
              <Prose text={job.qualifications} fallback="Not specified." />
            </Section>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Requirements</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <Section title="Required skills">
              <SkillChips skills={req?.required_skills ?? []} emptyLabel="No required skills." />
            </Section>
            <Section title="Preferred skills">
              <SkillChips
                skills={req?.preferred_skills ?? []}
                tone="preferred"
                emptyLabel="No preferred skills."
              />
            </Section>
            <dl className="grid gap-4 sm:grid-cols-2">
              <Fact
                label="Experience"
                value={formatExperience(req?.min_experience ?? null, req?.max_experience ?? null)}
              />
              <Fact label="Education" value={req?.education_level} />
            </dl>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-4">
              <Fact label="Department" value={job.department?.name} />
              <Fact label="Location" value={job.location?.name} />
              <Fact
                label="Work"
                value={`${WORK_MODE_LABELS[job.work_mode]} · ${EMPLOYMENT_TYPE_LABELS[job.employment_type]}`}
              />
              <Fact label="Level" value={job.level} />
              <Fact label="Openings" value={job.openings} />
              <Fact
                label="Salary"
                value={formatSalary(job.salary_min, job.salary_max, job.salary_currency)}
              />
              <Fact label="Published" value={formatDate(job.published_at)} />
              <Fact label="Closes" value={formatDate(job.closes_at)} />
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Hiring team</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Fact label="Hiring manager" value={job.hiring_manager?.name} />
            {job.team.length > 0 ? (
              <ul className="space-y-2">
                {job.team.map((member) => (
                  <li
                    key={`${member.user_id}-${member.team_role}`}
                    className="flex items-center justify-between gap-2 text-sm"
                  >
                    <span className="truncate">{member.full_name}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {TEAM_ROLE_LABELS[member.team_role]}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No team members assigned.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
