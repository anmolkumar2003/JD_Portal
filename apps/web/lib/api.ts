import type {
  ApiErrorBody,
  ApplyResult,
  Department,
  HealthResponse,
  Job,
  JobCreateInput,
  JobFieldsInput,
  JobListItem,
  JobListParams,
  Location,
  LoginRequest,
  Page,
  PublicJob,
  PublicJobFilters,
  PublicJobListItem,
  PublicJobListParams,
  RequirementsInput,
  TokenResponse,
  User,
} from "@/types/api";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details?: unknown,
    readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Non-2xx statuses whose body should be parsed as a normal response. */
  acceptStatuses?: readonly number[];
  /** Do not try to refresh the session and retry on 401 (used by the auth endpoints). */
  skipAuthRetry?: boolean;
}

// The access token lives in memory only; the refresh token is an httpOnly cookie set by the API.
let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

function isErrorBody(value: unknown): value is ApiErrorBody {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as ApiErrorBody).error?.message === "string"
  );
}

type SendOptions = Omit<RequestOptions, "acceptStatuses" | "skipAuthRetry">;

async function send(path: string, { body, headers, ...init }: SendOptions): Promise<Response> {
  // FormData goes as-is so the browser sets the multipart boundary header itself.
  const isForm = body instanceof FormData;
  try {
    return await fetch(`${API_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...(body !== undefined && !isForm ? { "Content-Type": "application/json" } : {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...headers,
      },
      body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    throw new ApiError(0, "network_error", "Could not reach the API", cause);
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { acceptStatuses = [], skipAuthRetry = false, ...sendOptions } = options;
  let response = await send(path, sendOptions);

  if (response.status === 401 && !skipAuthRetry && accessToken) {
    const session = await refreshSession();
    if (session) {
      response = await send(path, sendOptions);
    }
  }

  const requestId = response.headers.get("X-Request-ID") ?? undefined;
  const data: unknown = await response.json().catch(() => null);

  if (response.ok || acceptStatuses.includes(response.status)) {
    return data as T;
  }
  if (isErrorBody(data)) {
    throw new ApiError(
      response.status,
      data.error.code,
      data.error.message,
      data.error.details,
      requestId,
    );
  }
  throw new ApiError(response.status, "http_error", response.statusText, data, requestId);
}

// Refresh tokens rotate on use, so concurrent callers must share one in-flight refresh.
let refreshInFlight: Promise<TokenResponse | null> | null = null;

/** Exchange the refresh cookie for a new access token. Resolves to null if there is no session. */
export function refreshSession(): Promise<TokenResponse | null> {
  refreshInFlight ??= request<TokenResponse>("/api/v1/auth/refresh", {
    method: "POST",
    skipAuthRetry: true,
  })
    .then((session) => {
      setAccessToken(session.access_token);
      return session;
    })
    .catch((error: unknown) => {
      setAccessToken(null);
      if (error instanceof ApiError && error.status === 401) return null;
      throw error;
    })
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

type QueryValue = string | number | undefined | null;

export function withQuery(path: string, params: object): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params) as [string, QueryValue][]) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

const jobPath = (id: string, suffix = "") => `/api/v1/jobs/${encodeURIComponent(id)}${suffix}`;

export const api = {
  health: () => request<HealthResponse>("/health", { acceptStatuses: [503] }),
  auth: {
    login: async (body: LoginRequest): Promise<TokenResponse> => {
      const session = await request<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body,
        skipAuthRetry: true,
      });
      setAccessToken(session.access_token);
      return session;
    },
    logout: async (): Promise<void> => {
      try {
        await request<null>("/api/v1/auth/logout", { method: "POST", skipAuthRetry: true });
      } finally {
        setAccessToken(null);
      }
    },
    me: () => request<User>("/api/v1/auth/me"),
  },
  org: {
    departments: () => request<Department[]>("/api/v1/departments"),
    locations: () => request<Location[]>("/api/v1/locations"),
  },
  jobs: {
    list: (params: JobListParams = {}) =>
      request<Page<JobListItem>>(withQuery("/api/v1/jobs", params)),
    get: (id: string) => request<Job>(jobPath(id)),
    create: (body: JobCreateInput) => request<Job>("/api/v1/jobs", { method: "POST", body }),
    update: (id: string, body: Partial<JobFieldsInput>) =>
      request<Job>(jobPath(id), { method: "PATCH", body }),
    replaceRequirements: (id: string, body: RequirementsInput) =>
      request<Job>(jobPath(id, "/requirements"), { method: "PUT", body }),
    publish: (id: string) => request<Job>(jobPath(id, "/publish"), { method: "POST" }),
    close: (id: string) => request<Job>(jobPath(id, "/close"), { method: "POST" }),
  },
  publicJobs: {
    list: (params: PublicJobListParams = {}) =>
      request<Page<PublicJobListItem>>(withQuery("/api/v1/public/jobs", params)),
    get: (slug: string) => request<PublicJob>(`/api/v1/public/jobs/${encodeURIComponent(slug)}`),
    filters: () => request<PublicJobFilters>("/api/v1/public/jobs/filters"),
    apply: (slug: string, form: FormData) =>
      request<ApplyResult>(`/api/v1/public/jobs/${encodeURIComponent(slug)}/apply`, {
        method: "POST",
        body: form,
        skipAuthRetry: true,
      }),
  },
};

export const publicJobUrl = (slug: string) =>
  `${API_URL}/api/v1/public/jobs/${encodeURIComponent(slug)}`;
