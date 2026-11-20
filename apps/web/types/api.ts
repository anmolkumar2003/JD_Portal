export type ComponentState = "ok" | "down";

export interface ComponentStatus {
  status: ComponentState;
  latency_ms: number | null;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  checks: {
    api: ComponentStatus;
    database: ComponentStatus;
    redis: ComponentStatus;
  };
}

export type Role = "super_admin" | "hr_admin" | "recruiter" | "hiring_manager" | "interviewer";

export interface User {
  id: string;
  org_id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// --- Org lookups ------------------------------------------------------------------------------

export interface Department {
  id: string;
  name: string;
}

export interface Location {
  id: string;
  name: string;
  city: string | null;
  country: string | null;
}

// --- Jobs (SPEC 3.4) --------------------------------------------------------------------------

export type JobStatus = "draft" | "open" | "on_hold" | "closed" | "filled";
export type WorkMode = "onsite" | "hybrid" | "remote";
export type EmploymentType = "full_time" | "part_time" | "contract" | "internship";
export type TeamRole = "recruiter" | "interviewer" | "manager";

export interface NamedRef {
  id: string;
  name: string;
}

export interface Skill {
  name: string;
  weight: number;
}

/** Decimal fields arrive as strings (e.g. "3.0") to keep precision. */
export interface JobRequirements {
  required_skills: Skill[];
  preferred_skills: Skill[];
  min_experience: string | null;
  max_experience: string | null;
  education_level: string | null;
}

export interface TeamMember {
  user_id: string;
  full_name: string;
  email: string;
  role: Role;
  team_role: TeamRole;
}

export interface JobListItem {
  id: string;
  title: string;
  slug: string;
  status: JobStatus;
  department: NamedRef | null;
  location: NamedRef | null;
  work_mode: WorkMode;
  employment_type: EmploymentType;
  openings: number;
  applicants_count: number;
  published_at: string | null;
  closes_at: string | null;
  created_at: string;
}

export interface Job extends JobListItem {
  level: string | null;
  description: string;
  responsibilities: string | null;
  qualifications: string | null;
  salary_min: string | null;
  salary_max: string | null;
  salary_currency: string | null;
  updated_at: string;
  hiring_manager: NamedRef | null;
  requirements: JobRequirements | null;
  team: TeamMember[];
}

export interface RequirementsInput {
  required_skills: Skill[];
  preferred_skills: Skill[];
  min_experience: number | null;
  max_experience: number | null;
  education_level: string | null;
}

export interface JobFieldsInput {
  title: string;
  department_id: string | null;
  location_id: string | null;
  work_mode: WorkMode;
  employment_type: EmploymentType;
  level: string | null;
  description: string;
  responsibilities: string | null;
  qualifications: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  openings: number;
  closes_at: string | null;
}

export interface JobCreateInput extends JobFieldsInput {
  requirements: RequirementsInput;
}

export type JobSortField = "title" | "status" | "created_at" | "closes_at" | "applicants_count";

export interface JobListParams {
  page?: number;
  page_size?: number;
  sort?: string;
  status?: JobStatus;
  department_id?: string;
  location_id?: string;
  q?: string;
}

export interface PublicJobListItem {
  slug: string;
  title: string;
  department: NamedRef | null;
  location: NamedRef | null;
  work_mode: WorkMode;
  employment_type: EmploymentType;
  level: string | null;
  published_at: string | null;
  closes_at: string | null;
}

export interface PublicJob extends PublicJobListItem {
  description: string;
  responsibilities: string | null;
  qualifications: string | null;
  openings: number;
  required_skills: string[];
  preferred_skills: string[];
  min_experience: string | null;
  education_level: string | null;
}

export interface PublicJobFilters {
  departments: NamedRef[];
  locations: NamedRef[];
}

export interface ApplyResult {
  reference_no: string;
  job_title: string;
}

export interface PublicJobListParams {
  page?: number;
  page_size?: number;
  q?: string;
  department_id?: string;
  location_id?: string;
}

/** Standard error envelope returned by the API (docs/SPEC.md Part 9). */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

// --- Candidates & pipeline (CAND / PIPE) ------------------------------------------------------

export type StageType =
  "applied" | "screening" | "interview" | "offer" | "hired" | "rejected" | "custom";

export type CandidateSource = "career_site" | "referral" | "linkedin" | "agency" | "manual";

export type ApplicationStatus = "active" | "rejected" | "withdrawn" | "hired";

export type ParseStatus = "pending" | "processing" | "done" | "failed";

export interface PipelineStage {
  id: string;
  name: string;
  order: number;
  type: StageType;
  is_default: boolean;
}

export interface CandidateSummary {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  current_location: string | null;
  current_company: string | null;
  current_title: string | null;
  total_experience_years: string | null;
  expected_ctc: string | null;
  notice_period_days: number | null;
  linkedin_url: string | null;
  source: CandidateSource;
  tags: string[];
}

export interface ApplicationListItem {
  id: string;
  reference_no: string;
  status: ApplicationStatus;
  applied_at: string;
  stage_entered_at: string;
  stage: PipelineStage;
  job: NamedRef;
  candidate: CandidateSummary;
  overall_score: number | null;
  source: CandidateSource;
}

export interface ApplicationListParams {
  page?: number;
  page_size?: number;
  sort?: string;
  job_id?: string;
  stage_id?: string;
  candidate_id?: string;
  q?: string;
  source?: CandidateSource;
  applied_from?: string;
  applied_to?: string;
}

export interface DocumentMeta {
  id: string;
  type: "cv" | "cover_letter" | "offer" | "other";
  file_name: string;
  mime_type: string;
  size: number;
  is_primary: boolean;
}

export interface ParsedProfile {
  id: string;
  parse_status: ParseStatus;
  data: {
    skills?: string[] | Skill[];
    summary?: string;
    [key: string]: unknown;
  };
  total_experience_years: string | null;
  error: string | null;
}

export interface MatchResult {
  id: string;
  overall_score: number;
  breakdown: Record<string, unknown>;
  matched_skills: string[];
  missing_required: string[];
  missing_preferred: string[];
  extra_skills: string[];
  explanation: Record<string, unknown>;
  engine_version: string;
  computed_at: string;
}

export interface ApplicationDetail {
  id: string;
  reference_no: string;
  status: ApplicationStatus;
  applied_at: string;
  stage_entered_at: string;
  rejection_reason: string | null;
  cover_letter: string | null;
  stage: PipelineStage;
  job: NamedRef;
  candidate: CandidateSummary;
  documents: DocumentMeta[];
  parsed_profile: ParsedProfile | null;
  match_result: MatchResult | null;
}

export interface StageChangeInput {
  stage_id: string;
  rejection_reason?: string;
}

export interface BoardCard {
  id: string;
  candidate_id: string;
  first_name: string;
  last_name: string;
  current_title: string | null;
  stage_entered_at: string;
  overall_score: number | null;
  reference_no: string;
}

export interface BoardColumn {
  stage: PipelineStage;
  count: number;
  cards: BoardCard[];
}

export interface Board {
  job_id: string;
  stages: BoardColumn[];
}

export interface TimelineActor {
  id: string;
  full_name: string;
}

export interface TimelineEvent {
  id: string;
  action: string;
  occurred_at: string;
  application_id: string | null;
  actor: TimelineActor | null;
  meta: Record<string, unknown>;
}

export interface DownloadUrl {
  url: string;
  expires_in: number;
  file_name: string;
}
