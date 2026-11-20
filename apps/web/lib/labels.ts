import type { EmploymentType, JobStatus, Role, TeamRole, WorkMode } from "@/types/api";

export const ROLE_LABELS: Record<Role, string> = {
  super_admin: "Super Admin",
  hr_admin: "HR Admin",
  recruiter: "Recruiter",
  hiring_manager: "Hiring Manager",
  interviewer: "Interviewer",
};

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  draft: "Draft",
  open: "Open",
  on_hold: "On hold",
  closed: "Closed",
  filled: "Filled",
};

export const WORK_MODE_LABELS: Record<WorkMode, string> = {
  onsite: "On-site",
  hybrid: "Hybrid",
  remote: "Remote",
};

export const EMPLOYMENT_TYPE_LABELS: Record<EmploymentType, string> = {
  full_time: "Full-time",
  part_time: "Part-time",
  contract: "Contract",
  internship: "Internship",
};

export const TEAM_ROLE_LABELS: Record<TeamRole, string> = {
  recruiter: "Recruiter",
  interviewer: "Interviewer",
  manager: "Hiring manager",
};

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatSalary(
  min: string | null,
  max: string | null,
  currency: string | null,
): string {
  if (!min && !max) return "—";
  const format = (v: string) =>
    Number(v).toLocaleString(undefined, {
      style: currency ? "currency" : "decimal",
      currency: currency ?? undefined,
      maximumFractionDigits: 0,
    });
  if (min && max) return `${format(min)} – ${format(max)}`;
  return min ? `From ${format(min)}` : `Up to ${format(max as string)}`;
}

export function formatExperience(min: string | null, max: string | null): string {
  const n = (v: string) => Number(v).toString();
  if (min && max) return `${n(min)}–${n(max)} years`;
  if (min) return `${n(min)}+ years`;
  if (max) return `Up to ${n(max)} years`;
  return "—";
}
