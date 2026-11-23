import type {
  ApplicationStatus,
  CandidateSource,
  EmploymentType,
  InterviewRecommendation,
  JobStatus,
  Role,
  StageType,
  TeamRole,
  WorkMode,
} from "@/types/api";

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

export const STAGE_TYPE_LABELS: Record<StageType, string> = {
  applied: "Applied",
  screening: "Screening",
  interview: "Interview",
  offer: "Offer",
  hired: "Hired",
  rejected: "Rejected",
  custom: "Custom",
};

export const RECOMMENDATION_LABELS: Record<InterviewRecommendation, string> = {
  strong_no: "Strong no",
  no: "No",
  mixed: "Mixed",
  yes: "Yes",
  strong_yes: "Strong yes",
};

export const CANDIDATE_SOURCE_LABELS: Record<CandidateSource, string> = {
  career_site: "Career site",
  referral: "Referral",
  linkedin: "LinkedIn",
  agency: "Agency",
  manual: "Manual",
};

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  active: "Active",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  hired: "Hired",
};

export function daysInStage(stageEnteredAt: string): number {
  const ms = Date.now() - new Date(stageEnteredAt).getTime();
  return Math.max(0, Math.floor(ms / (1000 * 60 * 60 * 24)));
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

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
