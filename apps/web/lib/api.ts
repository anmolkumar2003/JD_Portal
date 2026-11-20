import type { ApiErrorBody, HealthResponse } from "@/types/api";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
}

function isErrorBody(value: unknown): value is ApiErrorBody {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as ApiErrorBody).error?.message === "string"
  );
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, acceptStatuses = [], headers, ...init } = options;

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    throw new ApiError(0, "network_error", "Could not reach the API", cause);
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

export const api = {
  health: () => request<HealthResponse>("/health", { acceptStatuses: [503] }),
};
