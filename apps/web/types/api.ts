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

/** Standard error envelope returned by the API (docs/SPEC.md Part 9). */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
