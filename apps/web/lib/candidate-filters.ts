import type { ApplicationListParams, CandidateSource } from "@/types/api";

export interface CandidateFilterValues {
  q: string;
  job_id: string;
  stage_id: string;
  source: string;
  department_id: string;
  score_min: string;
  score_max: string;
  skill: string;
  tag: string;
  is_shortlisted: string;
  applied_from: string;
  applied_to: string;
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
  "tag",
  "is_shortlisted",
  "applied_from",
  "applied_to",
  "sort",
] as const;

export type CandidateFilterKey = (typeof CANDIDATE_FILTER_KEYS)[number];

export const DEFAULT_CANDIDATE_SORT = "-applied_at";

export const EMPTY_CANDIDATE_FILTERS: CandidateFilterValues = {
  q: "",
  job_id: "",
  stage_id: "",
  source: "",
  department_id: "",
  score_min: "",
  score_max: "",
  skill: "",
  tag: "",
  is_shortlisted: "",
  applied_from: "",
  applied_to: "",
  sort: DEFAULT_CANDIDATE_SORT,
};

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
    tag: get("tag") ?? "",
    is_shortlisted: get("is_shortlisted") ?? "",
    applied_from: get("applied_from") ?? "",
    applied_to: get("applied_to") ?? "",
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
    skill: filters.skill || undefined,
    tag: filters.tag || undefined,
    is_shortlisted: isShortlisted,
    applied_from: filters.applied_from || undefined,
    applied_to: filters.applied_to || undefined,
  };
}

/** Serialisable filter map for saved-filter API (excludes sort when default). */
export function filtersToSavedPayload(filters: CandidateFilterValues): Record<string, string> {
  const payload: Record<string, string> = {};
  for (const key of CANDIDATE_FILTER_KEYS) {
    const value = filters[key];
    if (!value) continue;
    if (key === "sort" && value === DEFAULT_CANDIDATE_SORT) continue;
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
