"use client";

import { Briefcase, Plus, SearchX } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useMemo } from "react";

import { DataTable, type Column } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { JobFilters, type JobFilterValues } from "@/components/jobs/job-filters";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { useJobs } from "@/hooks/use-jobs";
import { EMPLOYMENT_TYPE_LABELS, WORK_MODE_LABELS, formatDate } from "@/lib/labels";
import { canManageJobs } from "@/lib/permissions";
import type { JobListItem, JobListParams, JobStatus } from "@/types/api";

const PAGE_SIZE = 20;
const DEFAULT_SORT = "-created_at";
const FILTER_KEYS = ["q", "status", "department_id", "location_id"] as const;

const COLUMNS: Column<JobListItem>[] = [
  {
    id: "title",
    header: "Title",
    sortKey: "title",
    cell: (job) => (
      <div className="min-w-[180px]">
        <Link
          href={`/jobs/${job.id}`}
          className="font-medium hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {job.title}
        </Link>
        <p className="font-mono text-xs text-muted-foreground">{job.slug}</p>
      </div>
    ),
  },
  {
    id: "status",
    header: "Status",
    sortKey: "status",
    cell: (job) => <StatusBadge status={job.status} />,
  },
  { id: "department", header: "Department", cell: (job) => job.department?.name ?? "—" },
  {
    id: "location",
    header: "Location",
    cell: (job) => (
      <div>
        <p>{job.location?.name ?? "—"}</p>
        <p className="text-xs text-muted-foreground">
          {WORK_MODE_LABELS[job.work_mode]} · {EMPLOYMENT_TYPE_LABELS[job.employment_type]}
        </p>
      </div>
    ),
  },
  {
    id: "applicants",
    header: "Applicants",
    sortKey: "applicants_count",
    className: "text-right",
    cell: (job) => <span className="tabular-nums">{job.applicants_count}</span>,
  },
  {
    id: "created",
    header: "Created",
    sortKey: "created_at",
    cell: (job) => <span className="whitespace-nowrap">{formatDate(job.created_at)}</span>,
  },
];

function JobsPageContent() {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters: JobFilterValues = {
    q: searchParams.get("q") ?? "",
    status: searchParams.get("status") ?? "",
    department_id: searchParams.get("department_id") ?? "",
    location_id: searchParams.get("location_id") ?? "",
  };
  const page = Math.max(1, Number(searchParams.get("page")) || 1);
  const sort = searchParams.get("sort") ?? DEFAULT_SORT;

  const params: JobListParams = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      sort,
      q: filters.q || undefined,
      status: (filters.status || undefined) as JobStatus | undefined,
      department_id: filters.department_id || undefined,
      location_id: filters.location_id || undefined,
    }),
    [page, sort, filters.q, filters.status, filters.department_id, filters.location_id],
  );
  const jobs = useJobs(params);

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
    (changes: Partial<JobFilterValues>) => updateParams({ ...changes, page: undefined }),
    [updateParams],
  );

  const canEdit = canManageJobs(user?.role);
  const hasFilters = FILTER_KEYS.some((key) => filters[key]);

  const empty = hasFilters ? (
    <EmptyState
      icon={SearchX}
      title="No jobs match your filters"
      description="Try a different search or clear the filters."
      action={
        <Button
          variant="outline"
          onClick={() => onFilterChange({ q: "", status: "", department_id: "", location_id: "" })}
        >
          Clear filters
        </Button>
      }
    />
  ) : (
    <EmptyState
      icon={Briefcase}
      title="No jobs yet"
      description={
        canEdit
          ? "Create your first job to start receiving applications."
          : "Jobs you are assigned to will appear here."
      }
      action={
        canEdit ? (
          <Button asChild>
            <Link href="/jobs/new">
              <Plus aria-hidden />
              Create job
            </Link>
          </Button>
        ) : undefined
      }
    />
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <Breadcrumbs items={[{ label: "Jobs" }]} />
          <h1 className="text-2xl font-semibold tracking-tight">Jobs</h1>
        </div>
        {canEdit && (
          <Button asChild>
            <Link href="/jobs/new">
              <Plus aria-hidden />
              Create job
            </Link>
          </Button>
        )}
      </div>

      <JobFilters value={filters} onChange={onFilterChange} />

      <DataTable
        caption="Jobs"
        columns={COLUMNS}
        rows={jobs.data?.items}
        getRowId={(job) => job.id}
        isLoading={jobs.isPending}
        error={jobs.error}
        onRetry={() => void jobs.refetch()}
        empty={empty}
        sort={sort}
        onSortChange={(value) => updateParams({ sort: value, page: undefined })}
        onRowClick={(job) => router.push(`/jobs/${job.id}`)}
        pagination={
          jobs.data
            ? {
                page,
                pageSize: PAGE_SIZE,
                total: jobs.data.total,
                onPageChange: (next) => updateParams({ page: next }),
              }
            : undefined
        }
      />
    </div>
  );
}

function JobsPageSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading jobs">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-72 w-full" />
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense fallback={<JobsPageSkeleton />}>
      <JobsPageContent />
    </Suspense>
  );
}
