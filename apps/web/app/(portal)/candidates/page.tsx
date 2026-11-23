"use client";

import { Plus, SearchX } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useMemo, useState } from "react";

import { CandidateDrawer } from "@/components/candidates/candidate-drawer";
import {
  CandidateFilters,
  type CandidateFilterValues,
} from "@/components/candidates/candidate-filters";
import { BulkActionsBar } from "@/components/candidates/bulk-actions-bar";
import { CandidatesTable } from "@/components/candidates/candidates-table";
import { EmptyState } from "@/components/empty-state";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useApplications } from "@/hooks/use-applications";
import { useAuth } from "@/hooks/use-auth";
import {
  CANDIDATE_FILTER_KEYS,
  candidateFiltersFromSearchParams,
  DEFAULT_CANDIDATE_SORT,
  EMPTY_CANDIDATE_FILTERS,
  toApplicationListParams,
} from "@/lib/candidate-filters";
import { canManageJobs } from "@/lib/permissions";

const PAGE_SIZE = 20;

function CandidatesPageContent() {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters: CandidateFilterValues = candidateFiltersFromSearchParams((key) =>
    searchParams.get(key),
  );
  const page = Math.max(1, Number(searchParams.get("page")) || 1);
  const sort = filters.sort || DEFAULT_CANDIDATE_SORT;
  const drawerId = searchParams.get("application");

  const params = useMemo(() => toApplicationListParams(filters, page, PAGE_SIZE), [filters, page]);

  const query = useApplications(params);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());

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
        for (const key of CANDIDATE_FILTER_KEYS) {
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

  const hasActiveFilters = CANDIDATE_FILTER_KEYS.some((key) => {
    const value = filters[key];
    if (key === "sort") return Boolean(value && value !== DEFAULT_CANDIDATE_SORT);
    return Boolean(value);
  });

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
          action={
            <Button variant="outline" onClick={() => onFiltersChange(EMPTY_CANDIDATE_FILTERS)}>
              Clear all filters
            </Button>
          }
        />
      ) : (
        <CandidatesTable
          rows={query.data?.items ?? []}
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
          selectedIds={canManageJobs(user?.role) ? selectedIds : undefined}
          onToggleRow={
            canManageJobs(user?.role)
              ? (id) =>
                  setSelectedIds((prev) => {
                    const next = new Set(prev);
                    if (next.has(id)) next.delete(id);
                    else next.add(id);
                    return next;
                  })
              : undefined
          }
          onToggleAll={
            canManageJobs(user?.role)
              ? (ids, select) =>
                  setSelectedIds((prev) => {
                    const next = new Set(prev);
                    for (const id of ids) {
                      if (select) next.add(id);
                      else next.delete(id);
                    }
                    return next;
                  })
              : undefined
          }
        />
      )}

      {canManageJobs(user?.role) && (
        <BulkActionsBar
          selectedIds={[...selectedIds]}
          rows={query.data?.items ?? []}
          onClear={() => setSelectedIds(new Set())}
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
