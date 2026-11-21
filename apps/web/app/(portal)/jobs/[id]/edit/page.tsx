"use client";

import { FileQuestion, Lock } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { JobForm } from "@/components/jobs/job-form";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { useJob } from "@/hooks/use-jobs";
import { ApiError } from "@/lib/api";
import { canManageJobs } from "@/lib/permissions";

export default function EditJobPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const job = useJob(id);

  const crumbs = [
    { label: "Jobs", href: "/jobs" },
    ...(job.data ? [{ label: job.data.title, href: `/jobs/${id}` }] : []),
    { label: "Edit" },
  ];

  let body;
  if (!canManageJobs(user?.role)) {
    body = (
      <EmptyState
        icon={Lock}
        title="You can't edit jobs"
        description="Only recruiters and HR admins can edit jobs."
      />
    );
  } else if (job.isPending) {
    body = (
      <div className="space-y-6" aria-busy="true" aria-label="Loading job">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  } else if (job.isError) {
    body =
      job.error instanceof ApiError && job.error.status === 404 ? (
        <EmptyState
          icon={FileQuestion}
          title="Job not found"
          description="It may have been deleted, or you may not have access to it."
          action={
            <Button asChild variant="outline">
              <Link href="/jobs">Back to jobs</Link>
            </Button>
          }
        />
      ) : (
        <ErrorState
          error={job.error}
          title="Could not load job"
          onRetry={() => void job.refetch()}
        />
      );
  } else {
    body = <JobForm key={job.data.id} job={job.data} />;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Breadcrumbs items={crumbs} />
        <h1 className="text-2xl font-semibold tracking-tight">Edit job</h1>
      </div>
      {body}
    </div>
  );
}
