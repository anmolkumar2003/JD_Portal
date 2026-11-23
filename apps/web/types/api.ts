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

/** Roles an admin can give in Settings > Users. */
export type AssignableRole = "super_admin" | "hr_admin" | "recruiter";

export interface User {
  id: string;
  org_id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface UserCreateInput {
  email: string;
  full_name: string;
  role: AssignableRole;
}

export interface UserPatchInput {
  email?: string;
  full_name?: string;
  role?: AssignableRole;
  is_active?: boolean;
}

export interface UserWithTemporaryPassword {
  user: User;
  temporary_password: string;
}

export interface ChangePasswordInput {
  current_password: string;
  new_password: string;
}

export type FeatureFlag = "public_careers" | "interviews" | "offers" | "requisitions" | "audit_ui";

/** Unauthenticated bootstrap: branding and which optional modules are switched on. */
export interface PublicConfig {
  org_name: string;
  logo_data_url: string | null;
  features: Record<FeatureFlag, boolean>;
}

export interface OrgSettings {
  name: string;
  logo_data_url: string | null;
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
  is_active: boolean;
}

export interface Location {
  id: string;
  name: string;
  city: string | null;
  country: string | null;
  is_active: boolean;
}

export interface LocationInput {
  name: string;
  city?: string | null;
  country?: string | null;
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

// --- Applications / pipeline (CAND / PIPE) ----------------------------------------------------

export type StageType =
  "applied" | "screening" | "interview" | "offer" | "hired" | "rejected" | "custom";

export type ApplicationStatus = "active" | "rejected" | "withdrawn" | "hired";

export type CandidateSource = "career_site" | "referral" | "linkedin" | "agency" | "manual";

export type DocumentType = "cv" | "cover_letter" | "offer" | "other";

export type ParseStatus = "pending" | "processing" | "done" | "failed";

export interface StageRef {
  id: string;
  name: string;
  type: StageType;
  order: number;
}

export interface ApplicationListItem {
  id: string;
  reference_no: string;
  status: ApplicationStatus;
  candidate_id: string;
  first_name: string;
  last_name: string;
  email: string;
  current_title: string | null;
  current_company: string | null;
  source: CandidateSource;
  job: NamedRef;
  stage: StageRef;
  overall_score: number | null;
  is_shortlisted: boolean;
  tags: string[];
  applied_at: string;
  stage_entered_at: string;
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
  score_min?: number;
  score_max?: number;
  skill?: string;
}

export interface DocumentOut {
  id: string;
  type: DocumentType;
  file_name: string;
  mime_type: string;
  size: number;
  is_primary: boolean;
}

export interface ParsedProfileOut {
  id?: string | null;
  document_id?: string | null;
  parse_status: ParseStatus;
  data: Record<string, unknown>;
  corrected_data?: Record<string, unknown> | null;
  total_experience_years: string | null;
  confidence: Record<string, unknown>;
  error: string | null;
  parser_version?: string | null;
}

export interface AtsCheckItem {
  id: string;
  label: string;
  passed: boolean;
  weight: number;
  detail: string;
  suggestion: string;
}

export interface AtsCheckOut {
  score: number;
  checks: AtsCheckItem[];
  engine_version: string;
  band?: string | null;
}

export interface MatchResultOut {
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

export interface AnalysisOut {
  application_id: string;
  document_id: string | null;
  parsed_profile: ParsedProfileOut | null;
  ats_check: AtsCheckOut | null;
  match_result: MatchResultOut | null;
  disclaimer: string;
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

export interface ApplicationDetail {
  id: string;
  reference_no: string;
  status: ApplicationStatus;
  rejection_reason: string | null;
  cover_letter: string | null;
  applied_at: string;
  stage_entered_at: string;
  is_shortlisted: boolean;
  candidate: CandidateSummary;
  job: NamedRef;
  stage: StageRef;
  documents: DocumentOut[];
  parsed_profile: ParsedProfileOut | null;
  match_result: MatchResultOut | null;
}

export interface StagePatchInput {
  stage_id: string;
  reason?: string | null;
}

export interface BoardCard {
  id: string;
  candidate_id: string;
  first_name: string;
  last_name: string;
  current_title: string | null;
  overall_score: number | null;
  stage_entered_at: string;
  applied_at: string;
  reference_no: string;
}

export interface BoardColumn {
  stage: StageRef;
  count: number;
  cards: BoardCard[];
}

export interface BoardOut {
  job_id: string;
  job_title: string;
  stages: BoardColumn[];
}

export interface TimelineEntry {
  id: string;
  action: string;
  occurred_at: string;
  actor_name: string | null;
  application_id: string | null;
  meta: Record<string, unknown>;
}

export interface DownloadUrl {
  url: string;
  expires_in: number;
  file_name: string;
}

// --- Notes, tags, shortlist, bulk actions (CAND-05, CAND-06) ------------------------------------

export interface UserRef {
  id: string;
  full_name: string;
  role: Role;
}

export interface NoteOut {
  id: string;
  candidate_id: string;
  application_id: string | null;
  author: UserRef | null;
  body: string;
  mentions: UserRef[];
  created_at: string;
}

export interface NoteCreateInput {
  body: string;
  mentions: string[];
  application_id?: string | null;
}

export interface CandidateTagsOut {
  id: string;
  tags: string[];
}

export interface ShortlistOut {
  application_id: string;
  is_shortlisted: boolean;
}

export type BulkActionType = "move_stage" | "reject" | "tag";

export interface BulkPayload {
  stage_id?: string;
  reason?: string;
  add_tags?: string[];
  remove_tags?: string[];
}

export interface BulkActionInput {
  action: BulkActionType;
  ids: string[];
  payload: BulkPayload;
}

export interface BulkFailure {
  id: string;
  code: string;
  message: string;
}

export interface BulkActionResult {
  action: BulkActionType;
  succeeded: string[];
  failed: BulkFailure[];
}

export interface ParsedProfilePatchInput {
  data: Record<string, unknown>;
  total_experience_years?: number | null;
}
