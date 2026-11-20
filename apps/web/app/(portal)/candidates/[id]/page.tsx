"use client";

import { FileQuestion } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";

import { PdfViewer } from "@/components/candidates/pdf-viewer";
import { ProfileOverview } from "@/components/candidates/profile-overview";
import { StageBadge } from "@/components/candidates/stage-badge";
import { Timeline } from "@/components/candidates/timeline";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { ScoreRing } from "@/components/score-ring";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApplication, useApplications } from "@/hooks/use-applications";
import { useCandidateTimeline } from "@/hooks/use-candidates";
import { ApiError } from "@/lib/api";
import { candidateDisplayName } from "@/lib/labels";

function CandidateProfileContent() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const appFromQuery = searchParams.get("app");

  const list = useApplications({
    page: 1,
    page_size: 20,
    sort: "-applied_at",
    candidate_id: id,
  });

  const applicationId = useMemo(() => {
    if (appFromQuery) return appFromQuery;
    return list.data?.items[0]?.id ?? null;
  }, [appFromQuery, list.data]);

  const detail = useApplication(applicationId);
  const timeline = useCandidateTimeline(id);

  if (!applicationId && list.isPending) {
    return <ProfileSkeleton />;
  }

  if (!applicationId && !list.isPending) {
    return (
      <div className="space-y-6">
        <Breadcrumbs
          items={[{ label: "Candidates", href: "/candidates" }, { label: "Not found" }]}
        />
        <EmptyState
          icon={FileQuestion}
          title="Candidate not found"
          description="No accessible application was found for this candidate."
          action={
            <Button asChild variant="outline">
              <Link href="/candidates">Back to candidates</Link>
            </Button>
          }
        />
      </div>
    );
  }

  if (detail.isPending) return <ProfileSkeleton />;

  if (detail.isError || !detail.data) {
    const notFound = detail.error instanceof ApiError && detail.error.status === 404;
    return (
      <div className="space-y-6">
        <Breadcrumbs
          items={[{ label: "Candidates", href: "/candidates" }, { label: "Not found" }]}
        />
        {notFound ? (
          <EmptyState
            icon={FileQuestion}
            title="Candidate not found"
            description="It may have been removed, or you may not have access."
            action={
              <Button asChild variant="outline">
                <Link href="/candidates">Back to candidates</Link>
              </Button>
            }
          />
        ) : (
          <ErrorState
            error={detail.error}
            title="Could not load candidate"
            onRetry={() => void detail.refetch()}
          />
        )}
      </div>
    );
  }

  const data = detail.data;
  const name = candidateDisplayName(data.candidate.first_name, data.candidate.last_name);
  const primaryCv =
    data.documents.find((d) => d.is_primary && d.type === "cv") ??
    data.documents.find((d) => d.type === "cv") ??
    null;

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Breadcrumbs items={[{ label: "Candidates", href: "/candidates" }, { label: name }]} />
        <div className="flex flex-wrap items-start gap-4">
          <ScoreRing score={data.match_result?.overall_score ?? null} size="md" />
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">{name}</h1>
              <StageBadge name={data.stage.name} type={data.stage.type} />
            </div>
            <p className="text-sm text-muted-foreground">
              {data.candidate.current_title ?? "No title"}
              {data.candidate.current_company ? ` · ${data.candidate.current_company}` : ""}
              {" · "}
              {data.job.name}
            </p>
            <p className="font-mono text-xs text-muted-foreground">{data.reference_no}</p>
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
          <ProfileOverview detail={data} />
        </TabsContent>
        <TabsContent value="cv" className="pt-4">
          <PdfViewer documentId={primaryCv?.id ?? null} fileName={primaryCv?.file_name} />
        </TabsContent>
        <TabsContent value="timeline" className="pt-4">
          <Timeline
            events={timeline.data}
            isLoading={timeline.isPending}
            error={timeline.error}
            onRetry={() => void timeline.refetch()}
          />
        </TabsContent>
        <TabsContent value="match" className="pt-4">
          <EmptyState
            icon={FileQuestion}
            title="Match analysis coming soon"
            description="Scores and skill gaps will appear here once the CV engine and matcher are enabled. Scores are advisory only."
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading candidate">
      <Skeleton className="h-4 w-40" />
      <Skeleton className="h-10 w-80" />
      <Skeleton className="h-10 w-56" />
      <Skeleton className="h-96 w-full" />
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
