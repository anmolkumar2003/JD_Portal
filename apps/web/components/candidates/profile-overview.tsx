"use client";

import { SkillChips } from "@/components/skill-chips";
import { SOURCE_LABELS, formatDate, formatExperience } from "@/lib/labels";
import type { ApplicationDetail, Skill } from "@/types/api";

function skillsFromProfile(detail: ApplicationDetail): Skill[] {
  const raw = detail.parsed_profile?.data?.skills;
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => {
      if (typeof item === "string") return { name: item, weight: 1 };
      if (item && typeof item === "object" && "name" in item) {
        const name = String((item as Skill).name);
        const weight = Number((item as Skill).weight) || 1;
        return { name, weight };
      }
      return null;
    })
    .filter((s): s is Skill => s !== null);
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-sm">{value}</dd>
    </div>
  );
}

export function ProfileOverview({ detail }: { detail: ApplicationDetail }) {
  const c = detail.candidate;
  const skills = skillsFromProfile(detail);

  return (
    <div className="space-y-6">
      <dl className="grid gap-4 sm:grid-cols-2">
        <Field label="Email" value={c.email} />
        <Field label="Phone" value={c.phone ?? "—"} />
        <Field label="Current title" value={c.current_title ?? "—"} />
        <Field label="Company" value={c.current_company ?? "—"} />
        <Field label="Location" value={c.current_location ?? "—"} />
        <Field
          label="Experience"
          value={c.total_experience_years ? formatExperience(c.total_experience_years, null) : "—"}
        />
        <Field label="Source" value={SOURCE_LABELS[c.source]} />
        <Field label="Applied" value={formatDate(detail.applied_at)} />
        <Field label="Reference" value={detail.reference_no} />
        <Field label="Job" value={detail.job.name} />
        {c.linkedin_url && (
          <div className="sm:col-span-2">
            <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              LinkedIn
            </dt>
            <dd className="mt-1 text-sm">
              <a
                href={c.linkedin_url}
                target="_blank"
                rel="noreferrer"
                className="text-primary hover:underline"
              >
                {c.linkedin_url}
              </a>
            </dd>
          </div>
        )}
      </dl>
      <div>
        <h3 className="mb-2 text-sm font-medium">Skills</h3>
        <SkillChips skills={skills} showWeights={false} emptyLabel="No parsed skills yet." />
      </div>
      {detail.cover_letter && (
        <div>
          <h3 className="mb-2 text-sm font-medium">Cover letter</h3>
          <p className="whitespace-pre-wrap text-sm text-muted-foreground">{detail.cover_letter}</p>
        </div>
      )}
    </div>
  );
}
