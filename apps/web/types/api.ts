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

/** Standard error envelope returned by the API (docs/SPEC.md Part 9). */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
