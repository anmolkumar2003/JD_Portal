import { withQuery } from "@/lib/api";
import type {
  Page,
  PublicJob,
  PublicJobFilters,
  PublicJobListItem,
  PublicJobListParams,
} from "@/types/api";

// In Docker the Next.js server reaches the API by service name, not via the host port.
const SERVER_API_URL =
  process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

/** GET a public endpoint during server rendering. Resolves to null on 404. */
async function serverGet<T>(path: string): Promise<T | null> {
  const response = await fetch(`${SERVER_API_URL}${path}`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`API request failed with status ${response.status}`);
  return (await response.json()) as T;
}

export const serverApi = {
  listPublicJobs: async (params: PublicJobListParams) =>
    (await serverGet<Page<PublicJobListItem>>(withQuery("/api/v1/public/jobs", params))) ?? {
      items: [],
      total: 0,
      page: 1,
      page_size: params.page_size ?? 20,
    },
  publicJobFilters: async () =>
    (await serverGet<PublicJobFilters>("/api/v1/public/jobs/filters")) ?? {
      departments: [],
      locations: [],
    },
  getPublicJob: (slug: string) =>
    serverGet<PublicJob>(`/api/v1/public/jobs/${encodeURIComponent(slug)}`),
};
