"use client";

import { FileQuestion } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";

import { ActivityTimeline } from "@/components/candidates/activity-timeline";
import { CandidateOverview } from "@/components/candidates/candidate-overview";
import { CvViewer } from "@/components/candidates/cv-viewer";
import { MatchAnalysis } from "@/components/candidates/match-analysis";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { BudgetBadge } from "@/components/candidates/budget-badge";
import { ScoreRing } from "@/components/score-ring";
import { StageBadge } from "@/components/stage-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApplication, useApplications } from "@/hooks/use-applications";
import { ApiError } from "@/lib/api";

function ProfileSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading candidate">
      <Skeleton className="h-4 w-40" />
      <Skeleton className="h-9 w-72" />
      <Skeleton className="h-10 w-96" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

function CandidateProfileContent() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const applicationParam = searchParams.get("application");

  const list = useApplications({
    candidate_id: id,
    page_size: 20,
    sort: "-applied_at",
  });

  const applicationId = useMemo(() => {
    if (applicationParam) return applicationParam;
    return list.data?.items[0]?.id ?? null;
  }, [applicationParam, list.data]);

  const detail = useApplication(applicationId);

  if (list.isPending || (applicationId && detail.isPending)) {
    return <ProfileSkeleton />;
  }

  if (list.isError) {
    return (
      <ErrorState
        error={list.error}
        title="Could not load candidate"
        onRetry={() => void list.refetch()}
      />
    );
  }

  if (
    !applicationId ||
    (detail.isError && detail.error instanceof ApiError && detail.error.status === 404)
  ) {
    return (
      <div className="space-y-6">
        <Breadcrumbs
          items={[{ label: "Candidates", href: "/candidates" }, { label: "Not found" }]}
        />
        <EmptyState
          icon={FileQuestion}
          title="Candidate not found"
          description="They may have been removed, or you may not have access to their applications."
          action={
            <Button asChild variant="outline">
              <Link href="/candidates">Back to candidates</Link>
            </Button>
          }
        />
      </div>
    );
  }

  if (detail.isError || !detail.data) {
    return (
      <ErrorState
        error={detail.error}
        title="Could not load application"
        onRetry={() => void detail.refetch()}
      />
    );
  }

  const data = detail.data;
  const name = `${data.candidate.first_name} ${data.candidate.last_name}`;

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Breadcrumbs items={[{ label: "Candidates", href: "/candidates" }, { label: name }]} />
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">{name}</h1>
              <StageBadge stage={data.stage} />
              <BudgetBadge status={data.budget_status} />
              <ScoreRing score={data.match_result?.overall_score ?? null} />
            </div>
            <p className="text-sm text-muted-foreground">
              {data.candidate.current_title ?? "No current title"} · {data.job.name}
            </p>
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="cv">CV</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="match">Match Analysis</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="pt-4">
          <CandidateOverview application={data} />
        </TabsContent>
        <TabsContent value="cv" className="pt-4">
          <CvViewer documents={data.documents} />
        </TabsContent>
        <TabsContent value="timeline" className="pt-4">
          <ActivityTimeline candidateId={data.candidate.id} />
        </TabsContent>
        <TabsContent value="match" className="pt-4">
          <MatchAnalysis applicationId={data.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function CandidateProfilePage() {
  return (
    <Suspense fallback={<ProfileSkeleton />}>
      <CandidateProfileContent />
    </Suspense>
  );
}
