"use client";

import {
  ExternalLink,
  FileQuestion,
  LayoutGrid,
  List,
  Loader2,
  Pencil,
  Send,
  Users,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { CandidateDrawer } from "@/components/candidates/candidate-drawer";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { JobDetails } from "@/components/jobs/job-details";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { KanbanBoard } from "@/components/pipeline/kanban-board";
import { PipelineTable } from "@/components/pipeline/pipeline-table";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/hooks/use-auth";
import { useApplications } from "@/hooks/use-applications";
import { useCloseJob, useJob, usePublishJob } from "@/hooks/use-jobs";
import { useJobBoard, useMoveApplicationStage } from "@/hooks/use-pipeline";
import { ApiError, publicJobUrl } from "@/lib/api";
import { canManageJobs } from "@/lib/permissions";
import type { PipelineStage } from "@/types/api";

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

function PipelineTab({ jobId }: { jobId: string }) {
  const board = useJobBoard(jobId);
  const move = useMoveApplicationStage(jobId);
  const [view, setView] = useState<"board" | "table">("board");
  const [drawerId, setDrawerId] = useState<string | null>(null);

  const onMoveTo = (applicationId: string, stage: PipelineStage) => {
    // Rejection requires a reason dialog — open the drawer which hosts it.
    if (stage.type === "rejected") {
      setDrawerId(applicationId);
      return;
    }
    move.mutate({ id: applicationId, body: { stage_id: stage.id } });
  };

  if (board.isPending) {
    return <Skeleton className="h-96 w-full" aria-label="Loading pipeline" />;
  }
  if (board.isError || !board.data) {
    return (
      <ErrorState
        error={board.error}
        title="Could not load pipeline"
        onRetry={() => void board.refetch()}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          Drag cards between stages, or use Move to on each card.
        </p>
        <div className="flex gap-1 rounded-md border p-1">
          <Button
            type="button"
            size="sm"
            variant={view === "board" ? "secondary" : "ghost"}
            onClick={() => setView("board")}
            aria-pressed={view === "board"}
          >
            <LayoutGrid aria-hidden />
            Board
          </Button>
          <Button
            type="button"
            size="sm"
            variant={view === "table" ? "secondary" : "ghost"}
            onClick={() => setView("table")}
            aria-pressed={view === "table"}
          >
            <List aria-hidden />
            Table
          </Button>
        </div>
      </div>

      {view === "board" ? (
        <KanbanBoard
          jobId={jobId}
          board={board.data}
          onOpenApplication={setDrawerId}
        />
      ) : (
        <PipelineTable
          board={board.data}
          onOpenApplication={setDrawerId}
          onMoveTo={onMoveTo}
          disabled={move.isPending}
        />
      )}

      {move.isError && view === "table" && (
        <p role="alert" className="text-sm text-destructive">
          {move.error instanceof ApiError ? move.error.message : "Could not move candidate."}
        </p>
      )}

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

function ApplicantsTab({ jobId }: { jobId: string }) {
  const apps = useApplications({
    job_id: jobId,
    page: 1,
    page_size: 50,
    sort: "-applied_at",
  });
  const [drawerId, setDrawerId] = useState<string | null>(null);

  if (apps.isPending) return <Skeleton className="h-48 w-full" />;
  if (apps.isError) {
    return (
      <ErrorState
        error={apps.error}
        title="Could not load applicants"
        onRetry={() => void apps.refetch()}
      />
    );
  }
  if (!apps.data || apps.data.total === 0) {
    return (
      <EmptyState
        icon={Users}
        title="No applicants yet"
        description="Applications will appear here as candidates apply."
      />
    );
  }

  return (
    <div className="space-y-2">
      <ul className="divide-y rounded-lg border">
        {apps.data.items.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-muted/50"
              onClick={() => setDrawerId(item.id)}
            >
              <span>
                <span className="font-medium">
                  {item.candidate.first_name} {item.candidate.last_name}
                </span>
                <span className="ml-2 text-sm text-muted-foreground">{item.stage.name}</span>
              </span>
              <span className="font-mono text-xs text-muted-foreground">{item.reference_no}</span>
            </button>
          </li>
        ))}
      </ul>
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
  const defaultTab = data.status === "open" || data.applicants_count > 0 ? "pipeline" : "details";

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

      <Tabs defaultValue={defaultTab}>
        <TabsList>
          <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
          <TabsTrigger value="applicants">Applicants ({data.applicants_count})</TabsTrigger>
          <TabsTrigger value="details">Details</TabsTrigger>
        </TabsList>
        <TabsContent value="pipeline" className="pt-4">
          <PipelineTab jobId={data.id} />
        </TabsContent>
        <TabsContent value="applicants" className="pt-4">
          <ApplicantsTab jobId={data.id} />
        </TabsContent>
        <TabsContent value="details" className="pt-4">
          <JobDetails job={data} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
