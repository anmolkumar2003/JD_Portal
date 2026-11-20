"use client";

import { SearchX, Users } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useMemo, useState } from "react";

import {
  CandidateFilters,
  type CandidateFilterValues,
} from "@/components/candidates/candidate-filters";
import { CandidateDrawer } from "@/components/candidates/candidate-drawer";
import { StageBadge } from "@/components/candidates/stage-badge";
import { DataTable, type Column } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { ScoreRing } from "@/components/score-ring";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useApplications } from "@/hooks/use-applications";
import { SOURCE_LABELS, candidateDisplayName, formatDate } from "@/lib/labels";
import type { ApplicationListItem, ApplicationListParams, CandidateSource } from "@/types/api";

const PAGE_SIZE = 20;
const DEFAULT_SORT = "-applied_at";
const FILTER_KEYS = ["q", "job_id", "stage_id", "source", "applied_from", "applied_to"] as const;

const COLUMNS: Column<ApplicationListItem>[] = [
  {
    id: "name",
    header: "Candidate",
    sortKey: "candidate_name",
    cell: (row) => (
      <div className="min-w-[160px]">
        <Link
          href={`/candidates/${row.candidate.id}?app=${row.id}`}
          className="font-medium hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {candidateDisplayName(row.candidate.first_name, row.candidate.last_name)}
        </Link>
        <p className="text-xs text-muted-foreground">{row.candidate.email}</p>
      </div>
    ),
  },
  {
    id: "job",
    header: "Job",
    cell: (row) => row.job.name,
  },
  {
    id: "stage",
    header: "Stage",
    cell: (row) => <StageBadge name={row.stage.name} type={row.stage.type} />,
  },
  {
    id: "score",
    header: "Score",
    sortKey: "overall_score",
    cell: (row) => <ScoreRing score={row.overall_score} />,
  },
  {
    id: "source",
    header: "Source",
    cell: (row) => SOURCE_LABELS[row.source],
  },
  {
    id: "applied",
    header: "Applied",
    sortKey: "applied_at",
    cell: (row) => <span className="whitespace-nowrap">{formatDate(row.applied_at)}</span>,
  },
];

function CandidatesPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [drawerId, setDrawerId] = useState<string | null>(null);

  const filters: CandidateFilterValues = useMemo(
    () => ({
      q: searchParams.get("q") ?? "",
      job_id: searchParams.get("job_id") ?? "",
      stage_id: searchParams.get("stage_id") ?? "",
      source: searchParams.get("source") ?? "",
      applied_from: searchParams.get("applied_from") ?? "",
      applied_to: searchParams.get("applied_to") ?? "",
    }),
    [searchParams],
  );
  const page = Math.max(1, Number(searchParams.get("page")) || 1);
  const sort = searchParams.get("sort") ?? DEFAULT_SORT;

  const params: ApplicationListParams = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      sort,
      q: filters.q || undefined,
      job_id: filters.job_id || undefined,
      stage_id: filters.stage_id || undefined,
      source: (filters.source || undefined) as CandidateSource | undefined,
      applied_from: filters.applied_from
        ? new Date(`${filters.applied_from}T00:00:00.000Z`).toISOString()
        : undefined,
      applied_to: filters.applied_to
        ? new Date(`${filters.applied_to}T23:59:59.999Z`).toISOString()
        : undefined,
    }),
    [page, sort, filters],
  );

  const applications = useApplications(params);

  const updateParams = useCallback(
    (changes: Record<string, string | number | undefined>) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(changes)) {
        if (value === undefined || value === "") next.delete(key);
        else next.set(key, String(value));
      }
      const query = next.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [router, pathname, searchParams],
  );

  const onFilterChange = useCallback(
    (changes: Partial<CandidateFilterValues>) => updateParams({ ...changes, page: undefined }),
    [updateParams],
  );

  const hasFilters = FILTER_KEYS.some((key) => filters[key]);

  const empty = hasFilters ? (
    <EmptyState
      icon={SearchX}
      title="No candidates match your filters"
      description="Try a different search or clear the filters."
      action={
        <Button
          variant="outline"
          onClick={() =>
            onFilterChange({
              q: "",
              job_id: "",
              stage_id: "",
              source: "",
              applied_from: "",
              applied_to: "",
            })
          }
        >
          Clear filters
        </Button>
      }
    />
  ) : (
    <EmptyState
      icon={Users}
      title="No candidates yet"
      description="Candidates appear here once people apply through the careers site."
    />
  );

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Breadcrumbs items={[{ label: "Candidates" }]} />
        <h1 className="text-2xl font-semibold tracking-tight">Candidates</h1>
      </div>

      <CandidateFilters value={filters} onChange={onFilterChange} />

      <DataTable
        caption="Candidates"
        columns={COLUMNS}
        rows={applications.data?.items}
        getRowId={(row) => row.id}
        isLoading={applications.isPending}
        error={applications.error}
        onRetry={() => void applications.refetch()}
        empty={empty}
        sort={sort}
        onSortChange={(value) => updateParams({ sort: value, page: undefined })}
        onRowClick={(row) => setDrawerId(row.id)}
        pagination={
          applications.data
            ? {
                page,
                pageSize: PAGE_SIZE,
                total: applications.data.total,
                onPageChange: (next) => updateParams({ page: next }),
              }
            : undefined
        }
      />

      <CandidateDrawer
        applicationId={drawerId}
        open={Boolean(drawerId)}
        onOpenChange={(open) => {
          if (!open) setDrawerId(null);
        }}
      />
    </div>
  );
}

function CandidatesSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading candidates">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-72 w-full" />
    </div>
  );
}

export default function CandidatesPage() {
  return (
    <Suspense fallback={<CandidatesSkeleton />}>
      <CandidatesPageContent />
    </Suspense>
  );
}
