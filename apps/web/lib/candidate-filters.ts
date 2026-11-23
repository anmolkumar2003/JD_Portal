import type {
  ApplicationListParams,
  ApplicationStatus,
  CandidateSource,
  SalaryUnit,
} from "@/types/api";

export interface CandidateFilterValues {
  q: string;
  job_id: string;
  stage_id: string;
  source: string;
  department_id: string;
  score_min: string;
  score_max: string;
  skill: string;
  /** Comma-separated skill names for multi-select. */
  skills: string;
  skills_mode: string;
  tag: string;
  is_shortlisted: string;
  applied_from: string;
  applied_to: string;
  location: string;
  experience_min: string;
  experience_max: string;
  notice_min_days: string;
  notice_max_days: string;
  expected_ctc_min: string;
  expected_ctc_max: string;
  expected_ctc_currency: string;
  expected_ctc_unit: string;
  ats_score_min: string;
  ats_score_max: string;
  rating_min: string;
  rating_max: string;
  status: string;
  sort: string;
}

export const CANDIDATE_FILTER_KEYS = [
  "q",
  "job_id",
  "stage_id",
  "source",
  "department_id",
  "score_min",
  "score_max",
  "skill",
  "skills",
  "skills_mode",
  "tag",
  "is_shortlisted",
  "applied_from",
  "applied_to",
  "location",
  "experience_min",
  "experience_max",
  "notice_min_days",
  "notice_max_days",
  "expected_ctc_min",
  "expected_ctc_max",
  "expected_ctc_currency",
  "expected_ctc_unit",
  "ats_score_min",
  "ats_score_max",
  "rating_min",
  "rating_max",
  "status",
  "sort",
] as const;

export type CandidateFilterKey = (typeof CANDIDATE_FILTER_KEYS)[number];

export const DEFAULT_CANDIDATE_SORT = "-applied_at";
export const DEFAULT_SKILLS_MODE = "any";

export const EMPTY_CANDIDATE_FILTERS: CandidateFilterValues = {
  q: "",
  job_id: "",
  stage_id: "",
  source: "",
  department_id: "",
  score_min: "",
  score_max: "",
  skill: "",
  skills: "",
  skills_mode: DEFAULT_SKILLS_MODE,
  tag: "",
  is_shortlisted: "",
  applied_from: "",
  applied_to: "",
  location: "",
  experience_min: "",
  experience_max: "",
  notice_min_days: "",
  notice_max_days: "",
  expected_ctc_min: "",
  expected_ctc_max: "",
  expected_ctc_currency: "",
  expected_ctc_unit: "",
  ats_score_min: "",
  ats_score_max: "",
  rating_min: "",
  rating_max: "",
  status: "",
  sort: DEFAULT_CANDIDATE_SORT,
};

export function parseSkillsList(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function candidateFiltersFromSearchParams(
  get: (key: string) => string | null,
): CandidateFilterValues {
  return {
    q: get("q") ?? "",
    job_id: get("job_id") ?? "",
    stage_id: get("stage_id") ?? "",
    source: get("source") ?? "",
    department_id: get("department_id") ?? "",
    score_min: get("score_min") ?? "",
    score_max: get("score_max") ?? "",
    skill: get("skill") ?? "",
    skills: get("skills") ?? "",
    skills_mode: get("skills_mode") ?? DEFAULT_SKILLS_MODE,
    tag: get("tag") ?? "",
    is_shortlisted: get("is_shortlisted") ?? "",
    applied_from: get("applied_from") ?? "",
    applied_to: get("applied_to") ?? "",
    location: get("location") ?? "",
    experience_min: get("experience_min") ?? "",
    experience_max: get("experience_max") ?? "",
    notice_min_days: get("notice_min_days") ?? "",
    notice_max_days: get("notice_max_days") ?? "",
    expected_ctc_min: get("expected_ctc_min") ?? "",
    expected_ctc_max: get("expected_ctc_max") ?? "",
    expected_ctc_currency: get("expected_ctc_currency") ?? "",
    expected_ctc_unit: get("expected_ctc_unit") ?? "",
    ats_score_min: get("ats_score_min") ?? "",
    ats_score_max: get("ats_score_max") ?? "",
    rating_min: get("rating_min") ?? "",
    rating_max: get("rating_max") ?? "",
    status: get("status") ?? "",
    sort: get("sort") ?? DEFAULT_CANDIDATE_SORT,
  };
}

export function toApplicationListParams(
  filters: CandidateFilterValues,
  page: number,
  pageSize: number,
): ApplicationListParams {
  const sort = filters.sort || DEFAULT_CANDIDATE_SORT;
  let isShortlisted: boolean | undefined;
  if (filters.is_shortlisted === "1") isShortlisted = true;
  else if (filters.is_shortlisted === "0") isShortlisted = false;

  const skills = parseSkillsList(filters.skills);
  const skillsMode =
    filters.skills_mode === "all" || filters.skills_mode === "any"
      ? filters.skills_mode
      : DEFAULT_SKILLS_MODE;

  return {
    page,
    page_size: pageSize,
    sort,
    q: filters.q || undefined,
    job_id: filters.job_id || undefined,
    stage_id: filters.stage_id || undefined,
    source: (filters.source || undefined) as CandidateSource | undefined,
    department_id: filters.department_id || undefined,
    score_min: filters.score_min ? Number(filters.score_min) : undefined,
    score_max: filters.score_max ? Number(filters.score_max) : undefined,
    skill: skills.length === 0 ? filters.skill || undefined : undefined,
    skills: skills.length > 0 ? skills : undefined,
    skills_mode: skills.length > 0 ? skillsMode : undefined,
    tag: filters.tag || undefined,
    is_shortlisted: isShortlisted,
    applied_from: filters.applied_from || undefined,
    applied_to: filters.applied_to || undefined,
    location: filters.location || undefined,
    experience_min: filters.experience_min ? Number(filters.experience_min) : undefined,
    experience_max: filters.experience_max ? Number(filters.experience_max) : undefined,
    notice_min_days: filters.notice_min_days ? Number(filters.notice_min_days) : undefined,
    notice_max_days: filters.notice_max_days ? Number(filters.notice_max_days) : undefined,
    expected_ctc_min: filters.expected_ctc_min ? Number(filters.expected_ctc_min) : undefined,
    expected_ctc_max: filters.expected_ctc_max ? Number(filters.expected_ctc_max) : undefined,
    expected_ctc_currency: filters.expected_ctc_currency || undefined,
    expected_ctc_unit: (filters.expected_ctc_unit || undefined) as SalaryUnit | undefined,
    ats_score_min: filters.ats_score_min ? Number(filters.ats_score_min) : undefined,
    ats_score_max: filters.ats_score_max ? Number(filters.ats_score_max) : undefined,
    rating_min: filters.rating_min ? Number(filters.rating_min) : undefined,
    rating_max: filters.rating_max ? Number(filters.rating_max) : undefined,
    status: (filters.status || undefined) as ApplicationStatus | undefined,
  };
}

/** Serialisable filter map for saved-filter API (excludes sort when default). */
export function filtersToSavedPayload(filters: CandidateFilterValues): Record<string, string> {
  const payload: Record<string, string> = {};
  for (const key of CANDIDATE_FILTER_KEYS) {
    const value = filters[key];
    if (!value) continue;
    if (key === "sort" && value === DEFAULT_CANDIDATE_SORT) continue;
    if (key === "skills_mode" && value === DEFAULT_SKILLS_MODE && !filters.skills) continue;
    payload[key] = value;
  }
  return payload;
}

export function savedPayloadToCandidateFilters(
  payload: Record<string, unknown>,
): Partial<CandidateFilterValues> {
  const changes: Partial<CandidateFilterValues> = {};
  for (const key of CANDIDATE_FILTER_KEYS) {
    const raw = payload[key];
    if (raw === undefined || raw === null) continue;
    const value = String(raw);
    if (value) changes[key] = value;
  }
  return changes;
}
