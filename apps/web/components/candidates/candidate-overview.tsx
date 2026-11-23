"use client";

import { Mail, Pencil } from "lucide-react";
import { useState } from "react";

import { BudgetBadge } from "@/components/candidates/budget-badge";
import { CandidateEditDialog } from "@/components/candidates/candidate-edit-dialog";
import { SkillChips } from "@/components/skill-chips";
import { ScoreRing } from "@/components/score-ring";
import { StageBadge } from "@/components/stage-badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { CANDIDATE_SOURCE_LABELS, formatDate } from "@/lib/labels";
import { canManageJobs } from "@/lib/permissions";
import type { ApplicationDetail, Skill } from "@/types/api";

function skillsFromProfile(data: Record<string, unknown> | undefined): Skill[] {
  const raw = data?.skills;
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => {
      if (typeof item === "string") return { name: item, weight: 1 };
      if (item && typeof item === "object" && "name" in item) {
        const name = String((item as { name: unknown }).name);
        const weight =
          "weight" in item && typeof (item as { weight: unknown }).weight === "number"
            ? (item as { weight: number }).weight
            : 1;
        return { name, weight };
      }
      return null;
    })
    .filter((s): s is Skill => Boolean(s?.name));
}

function formatSalaryLine(
  label: string,
  salary:
    | { amount: string | null; currency: string; unit: string; negotiable: boolean }
    | null
    | undefined,
): string | null {
  if (!salary?.amount) return null;
  const unit = salary.unit === "pm" ? "/mo" : "/yr";
  const neg = salary.negotiable ? " (negotiable)" : "";
  return `${label}: ${Number(salary.amount).toLocaleString()} ${salary.currency}${unit}${neg}`;
}

interface CandidateOverviewProps {
  application: ApplicationDetail;
  onEmail?: () => void;
}

export function CandidateOverview({ application, onEmail }: CandidateOverviewProps) {
  const { user } = useAuth();
  const canEdit = canManageJobs(user?.role);
  const [editOpen, setEditOpen] = useState(false);
  const { candidate } = application;
  const skills = skillsFromProfile(application.parsed_profile?.data);

  const salaryLines = [
    formatSalaryLine("Current", candidate.current_salary),
    formatSalaryLine("Expected", candidate.expected_salary),
    formatSalaryLine("Offered", candidate.offered_salary),
  ].filter(Boolean);

  return (
    <div className="grid gap-8 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Summary
          </h2>
          <div className="flex flex-wrap gap-2">
            {onEmail && (
              <Button type="button" variant="outline" size="sm" onClick={onEmail}>
                <Mail className="mr-2 h-3.5 w-3.5" aria-hidden />
                Email
              </Button>
            )}
            {canEdit && (
              <Button type="button" variant="outline" size="sm" onClick={() => setEditOpen(true)}>
                <Pencil className="mr-2 h-3.5 w-3.5" aria-hidden />
                Edit
              </Button>
            )}
          </div>
        </div>
        <section className="space-y-3">
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs text-muted-foreground">Email</dt>
              <dd className="text-sm">{candidate.email}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Phone</dt>
              <dd className="text-sm">{candidate.phone ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Location</dt>
              <dd className="text-sm">{candidate.current_location ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Experience</dt>
              <dd className="text-sm">
                {candidate.total_experience_years
                  ? `${candidate.total_experience_years} years`
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Company</dt>
              <dd className="text-sm">{candidate.current_company ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Title</dt>
              <dd className="text-sm">{candidate.current_title ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Source</dt>
              <dd className="text-sm">{CANDIDATE_SOURCE_LABELS[candidate.source]}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">LinkedIn</dt>
              <dd className="text-sm">
                {candidate.linkedin_url ? (
                  <a
                    href={candidate.linkedin_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary hover:underline"
                  >
                    Profile
                  </a>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            {candidate.portfolio_url && (
              <div>
                <dt className="text-xs text-muted-foreground">Portfolio</dt>
                <dd className="text-sm">
                  <a
                    href={candidate.portfolio_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary hover:underline"
                  >
                    Link
                  </a>
                </dd>
              </div>
            )}
            {salaryLines.length > 0 && (
              <div className="sm:col-span-2">
                <dt className="text-xs text-muted-foreground">Compensation</dt>
                <dd className="space-y-1 text-sm">
                  {salaryLines.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </dd>
              </div>
            )}
          </dl>
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Skills
          </h2>
          <SkillChips
            skills={skills}
            emptyLabel={
              application.parsed_profile?.parse_status === "pending"
                ? "CV parsing in progress — skills will appear here."
                : "No parsed skills yet."
            }
          />
        </section>

        {application.cover_letter && (
          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Cover letter
            </h2>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {application.cover_letter}
            </p>
          </section>
        )}
      </div>

      <aside className="space-y-4 rounded-lg border p-4">
        <div className="flex items-center justify-between gap-3">
          <StageBadge stage={application.stage} />
          <ScoreRing score={application.match_result?.overall_score ?? null} />
        </div>
        <BudgetBadge status={application.budget_status} />
        <dl className="space-y-3 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Job</dt>
            <dd>{application.job.name}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Reference</dt>
            <dd className="font-mono text-xs">{application.reference_no}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Applied</dt>
            <dd>{formatDate(application.applied_at)}</dd>
          </div>
          {application.rejection_reason && (
            <div>
              <dt className="text-xs text-muted-foreground">Rejection reason</dt>
              <dd>{application.rejection_reason}</dd>
            </div>
          )}
        </dl>
      </aside>

      {canEdit && (
        <CandidateEditDialog application={application} open={editOpen} onOpenChange={setEditOpen} />
      )}
    </div>
  );
}
