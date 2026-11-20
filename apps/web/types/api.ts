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
