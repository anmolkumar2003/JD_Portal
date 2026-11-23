import type {
  ApiErrorBody,
  AnalysisOut,
  ApplicationDetail,
  ApplicationListItem,
  ApplicationListParams,
  ApplyResult,
  BulkActionInput,
  BulkActionResult,
  BoardOut,
  CandidateOut,
  CandidatePatchInput,
  CandidateTagsOut,
  CvParseOut,
  DuplicateCheckOut,
  ManualCandidateResult,
  ChangePasswordInput,
  Department,
  DocumentOut,
  DownloadUrl,
  HealthResponse,
  Job,
  JobCreateInput,
  JobFieldsInput,
  JobListItem,
  JobListParams,
  Location,
  LocationInput,
  LoginRequest,
  NoteCreateInput,
  NoteOut,
  OrgSettings,
  Page,
  ParsedProfileOut,
  ParsedProfilePatchInput,
  PublicConfig,
  PublicJob,
  PublicJobFilters,
  PublicJobListItem,
  PublicJobListParams,
  RequirementsInput,
  ShortlistOut,
  StagePatchInput,
  StageRef,
  TimelineEntry,
  TokenResponse,
  User,
  UserCreateInput,
  UserPatchInput,
  UserRef,
  UserWithTemporaryPassword,
  EmailTemplateOut,
  EmailPreviewIn,
  EmailPreviewOut,
  EmailSendIn,
  EmailLogOut,
  NotificationOut,
  InterviewRatingOut,
  InterviewRatingIn,
  FinalScoreOut,
  ScoringWeights,
  SavedFilterIn,
  SavedFilterOut,
  SearchResult,
} from "@/types/api";

// Empty means same origin: next.config.mjs (dev) or Caddy (production) forwards /api/v1 to the API.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

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
    changePassword: async (body: ChangePasswordInput): Promise<TokenResponse> => {
      const session = await request<TokenResponse>("/api/v1/auth/change-password", {
        method: "POST",
        body,
      });
      setAccessToken(session.access_token);
      return session;
    },
    forgotPassword: (email: string) =>
      request<{ message: string }>("/api/v1/auth/forgot-password", {
        method: "POST",
        body: { email },
        skipAuthRetry: true,
      }),
    resetPassword: (token: string, newPassword: string) =>
      request<{ message: string }>("/api/v1/auth/reset-password", {
        method: "POST",
        body: { token, new_password: newPassword },
        skipAuthRetry: true,
      }),
  },
  config: () => request<PublicConfig>("/api/v1/config", { skipAuthRetry: true }),
  org: {
    departments: (includeInactive = false) =>
      request<Department[]>(
        withQuery("/api/v1/departments", { include_inactive: includeInactive || undefined }),
      ),
    createDepartment: (name: string) =>
      request<Department>("/api/v1/departments", { method: "POST", body: { name } }),
    updateDepartment: (id: string, body: { name?: string; is_active?: boolean }) =>
      request<Department>(`/api/v1/departments/${encodeURIComponent(id)}`, {
        method: "PATCH",
        body,
      }),
    locations: (includeInactive = false) =>
      request<Location[]>(
        withQuery("/api/v1/locations", { include_inactive: includeInactive || undefined }),
      ),
    createLocation: (body: LocationInput) =>
      request<Location>("/api/v1/locations", { method: "POST", body }),
    updateLocation: (id: string, body: Partial<LocationInput> & { is_active?: boolean }) =>
      request<Location>(`/api/v1/locations/${encodeURIComponent(id)}`, { method: "PATCH", body }),
    settings: () => request<OrgSettings>("/api/v1/org/settings"),
    updateSettings: (body: { name: string }) =>
      request<OrgSettings>("/api/v1/org/settings", { method: "PATCH", body }),
    uploadLogo: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return request<OrgSettings>("/api/v1/org/logo", { method: "PUT", body: form });
    },
    removeLogo: () => request<OrgSettings>("/api/v1/org/logo", { method: "DELETE" }),
    scoringWeights: () => request<ScoringWeights>("/api/v1/org/scoring-weights"),
    updateScoringWeights: (body: ScoringWeights) =>
      request<ScoringWeights>("/api/v1/org/scoring-weights", { method: "PUT", body }),
  },
  emails: {
    listTemplates: () => request<EmailTemplateOut[]>("/api/v1/email-templates"),
    preview: (body: EmailPreviewIn) =>
      request<EmailPreviewOut>("/api/v1/emails/preview", { method: "POST", body }),
    send: (body: EmailSendIn) =>
      request<EmailLogOut>("/api/v1/emails/send", { method: "POST", body }),
    listForCandidate: (candidateId: string) =>
      request<EmailLogOut[]>(`/api/v1/candidates/${encodeURIComponent(candidateId)}/emails`),
  },
  jobs: {
    list: (params: JobListParams = {}) =>
      request<Page<JobListItem>>(withQuery("/api/v1/jobs", params)),
    get: (id: string) => request<Job>(jobPath(id)),
    board: (id: string) => request<BoardOut>(jobPath(id, "/board")),
    create: (body: JobCreateInput) => request<Job>("/api/v1/jobs", { method: "POST", body }),
    update: (id: string, body: Partial<JobFieldsInput>) =>
      request<Job>(jobPath(id), { method: "PATCH", body }),
    replaceRequirements: (id: string, body: RequirementsInput) =>
      request<Job>(jobPath(id, "/requirements"), { method: "PUT", body }),
    publish: (id: string) => request<Job>(jobPath(id, "/publish"), { method: "POST" }),
    close: (id: string) => request<Job>(jobPath(id, "/close"), { method: "POST" }),
  },
  applications: {
    list: (params: ApplicationListParams = {}) =>
      request<Page<ApplicationListItem>>(withQuery("/api/v1/applications", params)),
    get: (id: string) =>
      request<ApplicationDetail>(`/api/v1/applications/${encodeURIComponent(id)}`),
    analysis: (id: string) =>
      request<AnalysisOut>(`/api/v1/applications/${encodeURIComponent(id)}/analysis`),
    stages: () => request<StageRef[]>("/api/v1/applications/stages"),
    moveStage: (id: string, body: StagePatchInput) =>
      request<ApplicationDetail>(`/api/v1/applications/${encodeURIComponent(id)}/stage`, {
        method: "PATCH",
        body,
      }),
    shortlist: (id: string, shortlisted?: boolean) =>
      request<ShortlistOut>(`/api/v1/applications/${encodeURIComponent(id)}/shortlist`, {
        method: "POST",
        body: shortlisted === undefined ? undefined : { shortlisted },
      }),
    bulkAction: (body: BulkActionInput) =>
      request<BulkActionResult>("/api/v1/applications/bulk-action", { method: "POST", body }),
    listRatings: (applicationId: string) =>
      request<InterviewRatingOut[]>(
        `/api/v1/applications/${encodeURIComponent(applicationId)}/ratings`,
      ),
    createRating: (applicationId: string, body: InterviewRatingIn) =>
      request<InterviewRatingOut>(
        `/api/v1/applications/${encodeURIComponent(applicationId)}/ratings`,
        { method: "POST", body },
      ),
    finalScore: (applicationId: string) =>
      request<FinalScoreOut>(
        `/api/v1/applications/${encodeURIComponent(applicationId)}/final-score`,
      ),
  },
  ratings: {
    update: (id: string, body: InterviewRatingIn) =>
      request<InterviewRatingOut>(`/api/v1/ratings/${encodeURIComponent(id)}`, {
        method: "PATCH",
        body,
      }),
    delete: (id: string) =>
      request<null>(`/api/v1/ratings/${encodeURIComponent(id)}`, { method: "DELETE" }),
  },
  candidates: {
    parseCv: (file: File) => {
      const form = new FormData();
      form.append("cv", file);
      return request<CvParseOut>("/api/v1/candidates/parse-cv", { method: "POST", body: form });
    },
    duplicates: (params: { email?: string; phone?: string }) =>
      request<DuplicateCheckOut>(withQuery("/api/v1/candidates/duplicates", params)),
    create: (form: FormData) =>
      request<ManualCandidateResult>("/api/v1/candidates", { method: "POST", body: form }),
    update: (id: string, body: CandidatePatchInput) =>
      request<CandidateOut>(`/api/v1/candidates/${encodeURIComponent(id)}`, {
        method: "PATCH",
        body,
      }),
    uploadDocument: (id: string, form: FormData) =>
      request<DocumentOut>(`/api/v1/candidates/${encodeURIComponent(id)}/documents`, {
        method: "POST",
        body: form,
      }),
    timeline: (id: string) =>
      request<TimelineEntry[]>(`/api/v1/candidates/${encodeURIComponent(id)}/timeline`),
    notes: (id: string) => request<NoteOut[]>(`/api/v1/candidates/${encodeURIComponent(id)}/notes`),
    createNote: (id: string, body: NoteCreateInput) =>
      request<NoteOut>(`/api/v1/candidates/${encodeURIComponent(id)}/notes`, {
        method: "POST",
        body,
      }),
    setTags: (id: string, tags: string[]) =>
      request<CandidateTagsOut>(`/api/v1/candidates/${encodeURIComponent(id)}`, {
        method: "PATCH",
        body: { tags },
      }),
  },
  users: {
    lookup: () => request<UserRef[]>("/api/v1/users/lookup"),
    list: () => request<Page<User>>(withQuery("/api/v1/users", { page_size: 100 })),
    create: (body: UserCreateInput) =>
      request<UserWithTemporaryPassword>("/api/v1/users", { method: "POST", body }),
    update: (id: string, body: UserPatchInput) =>
      request<User>(`/api/v1/users/${encodeURIComponent(id)}`, { method: "PATCH", body }),
    resetPassword: (id: string) =>
      request<UserWithTemporaryPassword>(`/api/v1/users/${encodeURIComponent(id)}/reset-password`, {
        method: "POST",
      }),
  },
  documents: {
    downloadUrl: (id: string) =>
      request<DownloadUrl>(`/api/v1/documents/${encodeURIComponent(id)}/download-url`),
    reprocess: (id: string) =>
      request<{ document_id: string; status: string }>(
        `/api/v1/documents/${encodeURIComponent(id)}/reprocess`,
        { method: "POST" },
      ),
  },
  parsedProfiles: {
    patch: (id: string, body: ParsedProfilePatchInput) =>
      request<ParsedProfileOut>(`/api/v1/parsed-profiles/${encodeURIComponent(id)}`, {
        method: "PATCH",
        body,
      }),
  },
  analytics: {
    overview: () => request<Record<string, number | object>>("/api/v1/analytics/overview"),
    funnel: () =>
      request<{ stage: string; type: string; count: number }[]>("/api/v1/analytics/funnel"),
    sources: () => request<{ source: string; count: number }[]>("/api/v1/analytics/sources"),
    overTime: (days = 30) =>
      request<{ date: string; count: number }[]>(
        withQuery("/api/v1/analytics/applications-over-time", { days }),
      ),
  },
  search: (q: string) => request<SearchResult>(withQuery("/api/v1/search", { q })),
  savedFilters: {
    list: () => request<SavedFilterOut[]>("/api/v1/saved-filters"),
    create: (body: SavedFilterIn) =>
      request<SavedFilterOut>("/api/v1/saved-filters", { method: "POST", body }),
    update: (id: string, body: SavedFilterIn) =>
      request<SavedFilterOut>(`/api/v1/saved-filters/${encodeURIComponent(id)}`, {
        method: "PUT",
        body,
      }),
    delete: (id: string) =>
      request<null>(`/api/v1/saved-filters/${encodeURIComponent(id)}`, { method: "DELETE" }),
  },
  notifications: {
    list: (unreadOnly = false) =>
      request<NotificationOut[]>(withQuery("/api/v1/notifications", { unread_only: unreadOnly })),
    markRead: (id: string) =>
      request<NotificationOut>(`/api/v1/notifications/${encodeURIComponent(id)}/read`, {
        method: "PATCH",
      }),
    markAllRead: () =>
      request<{ updated: number }>("/api/v1/notifications/read-all", { method: "POST" }),
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
