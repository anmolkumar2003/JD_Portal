"use client";

import { Plus, SearchX } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useMemo } from "react";

import { CandidateDrawer } from "@/components/candidates/candidate-drawer";
import {
  CandidateFilters,
  type CandidateFilterValues,
} from "@/components/candidates/candidate-filters";
import { CandidatesTable } from "@/components/candidates/candidates-table";
import { EmptyState } from "@/components/empty-state";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useApplications } from "@/hooks/use-applications";
import { useAuth } from "@/hooks/use-auth";
import { canManageJobs } from "@/lib/permissions";
import type { ApplicationListParams, CandidateSource } from "@/types/api";

const PAGE_SIZE = 20;
const DEFAULT_SORT = "-applied_at";
const FILTER_KEYS = [
  "q",
  "job_id",
  "stage_id",
  "source",
  "score_min",
  "score_max",
  "skill",
  "sort",
] as const;

function CandidatesPageContent() {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters: CandidateFilterValues = {
    q: searchParams.get("q") ?? "",
    job_id: searchParams.get("job_id") ?? "",
    stage_id: searchParams.get("stage_id") ?? "",
    source: searchParams.get("source") ?? "",
    score_min: searchParams.get("score_min") ?? "",
    score_max: searchParams.get("score_max") ?? "",
    skill: searchParams.get("skill") ?? "",
    sort: searchParams.get("sort") ?? DEFAULT_SORT,
  };
  const page = Math.max(1, Number(searchParams.get("page")) || 1);
  const sort = filters.sort || DEFAULT_SORT;
  const drawerId = searchParams.get("application");

  const params: ApplicationListParams = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      sort,
      q: filters.q || undefined,
      job_id: filters.job_id || undefined,
      stage_id: filters.stage_id || undefined,
      source: (filters.source || undefined) as CandidateSource | undefined,
      score_min: filters.score_min ? Number(filters.score_min) : undefined,
      score_max: filters.score_max ? Number(filters.score_max) : undefined,
      skill: filters.skill || undefined,
    }),
    [
      page,
      sort,
      filters.q,
      filters.job_id,
      filters.stage_id,
      filters.source,
      filters.score_min,
      filters.score_max,
      filters.skill,
    ],
  );

  const query = useApplications(params);

  const replaceParams = useCallback(
    (mutate: (next: URLSearchParams) => void) => {
      const next = new URLSearchParams(searchParams.toString());
      mutate(next);
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname);
    },
    [pathname, router, searchParams],
  );

  const onFiltersChange = useCallback(
    (changes: Partial<CandidateFilterValues>) => {
      replaceParams((next) => {
        for (const key of FILTER_KEYS) {
          if (key in changes) {
            const value = changes[key];
            if (value) next.set(key, value);
            else next.delete(key);
          }
        }
        next.delete("page");
      });
    },
    [replaceParams],
  );

  const hasActiveFilters = FILTER_KEYS.some((key) => Boolean(filters[key]));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <Breadcrumbs items={[{ label: "Candidates" }]} />
          <h1 className="text-2xl font-semibold tracking-tight">Candidates</h1>
        </div>
        {canManageJobs(user?.role) && (
          <Button asChild>
            <Link href="/candidates/new">
              <Plus className="mr-2 h-4 w-4" aria-hidden />
              Add candidate
            </Link>
          </Button>
        )}
      </div>

      <CandidateFilters value={filters} onChange={onFiltersChange} />

      {query.isSuccess && query.data.total === 0 && hasActiveFilters ? (
        <EmptyState
          icon={SearchX}
          title="No matching candidates"
          description="Try clearing filters or broadening your search."
        />
      ) : (
        <CandidatesTable
          rows={query.data?.items}
          isLoading={query.isPending}
          error={query.error}
          onRetry={() => void query.refetch()}
          sort={sort}
          onSortChange={(nextSort) =>
            replaceParams((next) => {
              next.set("sort", nextSort);
              next.delete("page");
            })
          }
          page={page}
          pageSize={PAGE_SIZE}
          total={query.data?.total ?? 0}
          onPageChange={(nextPage) =>
            replaceParams((next) => {
              if (nextPage <= 1) next.delete("page");
              else next.set("page", String(nextPage));
            })
          }
          onRowClick={(row) =>
            replaceParams((next) => {
              next.set("application", row.id);
            })
          }
        />
      )}

      <CandidateDrawer
        applicationId={drawerId}
        open={Boolean(drawerId)}
        onOpenChange={(open) => {
          if (!open) {
            replaceParams((next) => {
              next.delete("application");
            });
          }
        }}
      />
    </div>
  );
}

export default function CandidatesPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6" aria-busy="true">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <CandidatesPageContent />
    </Suspense>
  );
}
