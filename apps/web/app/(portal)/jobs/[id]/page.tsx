"use client";

import { ExternalLink, FileQuestion, Loader2, Pencil, Send, XCircle } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { PipelineBoard } from "@/components/candidates/pipeline-board";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { JobDetails } from "@/components/jobs/job-details";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/hooks/use-auth";
import { useCloseJob, useJob, usePublishJob } from "@/hooks/use-jobs";
import { ApiError, publicJobUrl } from "@/lib/api";
import { canManageJobs } from "@/lib/permissions";

function JobDetailSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading job">
      <Skeleton className="h-4 w-40" />
      <Skeleton className="h-9 w-80" />
      <Skeleton className="h-10 w-56" />
      <div className="grid gap-6 lg:grid-cols-3">
        <Skeleton className="h-96 lg:col-span-2" />
        <Skeleton className="h-96" />
      </div>
    </div>
  );
}

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const job = useJob(id);
  const publish = usePublishJob();
  const close = useCloseJob();

  if (job.isPending) return <JobDetailSkeleton />;

  if (job.isError) {
    const notFound = job.error instanceof ApiError && job.error.status === 404;
    return (
      <div className="space-y-6">
        <Breadcrumbs items={[{ label: "Jobs", href: "/jobs" }, { label: "Not found" }]} />
        {notFound ? (
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
        )}
      </div>
    );
  }

  const data = job.data;
  const canEdit = canManageJobs(user?.role);
  const canPublish = canEdit && (data.status === "draft" || data.status === "on_hold");
  const canClose = canEdit && data.status !== "closed" && data.status !== "filled";
  const actionError = publish.error ?? close.error;
  const busy = publish.isPending || close.isPending;

  const onClose = () => {
    if (window.confirm(`Close "${data.title}"? It will no longer accept applications.`)) {
      publish.reset();
      close.mutate(data.id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Breadcrumbs items={[{ label: "Jobs", href: "/jobs" }, { label: data.title }]} />
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">{data.title}</h1>
              <StatusBadge status={data.status} />
            </div>
            <p className="font-mono text-xs text-muted-foreground">{data.slug}</p>
            {data.status === "open" && (
              <a
                href={publicJobUrl(data.slug)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
              >
                View public listing
                <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              </a>
            )}
          </div>
          {canEdit && (
            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline">
                <Link href={`/jobs/${data.id}/edit`}>
                  <Pencil aria-hidden />
                  Edit
                </Link>
              </Button>
              {canClose && (
                <Button variant="outline" onClick={onClose} disabled={busy}>
                  {close.isPending ? (
                    <Loader2 className="animate-spin" aria-hidden />
                  ) : (
                    <XCircle aria-hidden />
                  )}
                  Close job
                </Button>
              )}
              {canPublish && (
                <Button
                  onClick={() => {
                    close.reset();
                    publish.mutate(data.id);
                  }}
                  disabled={busy}
                >
                  {publish.isPending ? (
                    <Loader2 className="animate-spin" aria-hidden />
                  ) : (
                    <Send aria-hidden />
                  )}
                  Publish
                </Button>
              )}
            </div>
          )}
        </div>
        {actionError && (
          <p
            role="alert"
            className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
          >
            {actionError instanceof ApiError
              ? actionError.message
              : "The action failed. Please try again."}
          </p>
        )}
      </div>

      <Tabs defaultValue="details">
        <TabsList>
          <TabsTrigger value="details">Details</TabsTrigger>
          <TabsTrigger value="pipeline">Pipeline ({data.applicants_count})</TabsTrigger>
        </TabsList>
        <TabsContent value="details" className="pt-4">
          <JobDetails job={data} />
        </TabsContent>
        <TabsContent value="pipeline" className="pt-4">
          <PipelineBoard jobId={data.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
