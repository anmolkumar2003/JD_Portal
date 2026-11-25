"use client";

import { FileQuestion } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { toast } from "sonner";

import { ActivityTimeline } from "@/components/candidates/activity-timeline";
import { AnonymizeCandidateDialog } from "@/components/candidates/anonymize-candidate-dialog";
import { CandidateOverview } from "@/components/candidates/candidate-overview";
import { CandidateProfileHeader } from "@/components/candidates/candidate-profile-header";
import { CvViewer } from "@/components/candidates/cv-viewer";
import { DeleteCandidateDialog } from "@/components/candidates/delete-candidate-dialog";
import { EmailComposer } from "@/components/candidates/email-composer";
import { InterviewRatings } from "@/components/candidates/interview-ratings";
import { MatchAnalysis } from "@/components/candidates/match-analysis";
import { NotesPanel } from "@/components/candidates/notes-panel";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApplication, useApplications } from "@/hooks/use-applications";
import { useAuth } from "@/hooks/use-auth";
import { useAnonymizeCandidate, useDeleteCandidate } from "@/hooks/use-candidates";
import { ApiError } from "@/lib/api";
import { canManageJobs } from "@/lib/permissions";

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
  const router = useRouter();
  const searchParams = useSearchParams();
  const applicationParam = searchParams.get("application");
  const { user } = useAuth();
  const canEmail = canManageJobs(user?.role);
  const deleteCandidate = useDeleteCandidate();
  const anonymizeCandidate = useAnonymizeCandidate();
  const [emailOpen, setEmailOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [anonymizeOpen, setAnonymizeOpen] = useState(false);

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
  const openEmail = canEmail ? () => setEmailOpen(true) : undefined;

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Candidates", href: "/candidates" }, { label: name }]} />

      <CandidateProfileHeader
        application={data}
        onEmail={openEmail}
        onDeleteRequest={() => setDeleteOpen(true)}
        onAnonymizeRequest={() => setAnonymizeOpen(true)}
      />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="cv">CV</TabsTrigger>
          <TabsTrigger value="match">Match Analysis</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="notes">Notes</TabsTrigger>
          <TabsTrigger value="interviews">Interviews</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="pt-4">
          <CandidateOverview application={data} onEmail={openEmail} />
        </TabsContent>
        <TabsContent value="cv" className="pt-4">
          <CvViewer documents={data.documents} applicationId={data.id} />
        </TabsContent>
        <TabsContent value="match" className="pt-4">
          <MatchAnalysis applicationId={data.id} />
        </TabsContent>
        <TabsContent value="notes" className="pt-4">
          <NotesPanel application={data} onEmail={openEmail} />
        </TabsContent>
        <TabsContent value="interviews" className="pt-4">
          <InterviewRatings applicationId={data.id} />
        </TabsContent>
        <TabsContent value="timeline" className="pt-4">
          <ActivityTimeline candidateId={data.candidate.id} />
        </TabsContent>
      </Tabs>

      {canEmail && (
        <EmailComposer application={data} open={emailOpen} onOpenChange={setEmailOpen} />
      )}

      <DeleteCandidateDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        mode="single"
        candidateName={name}
        busy={deleteCandidate.isPending}
        onConfirm={() => {
          deleteCandidate.mutate(data.candidate.id, {
            onSuccess: () => {
              toast.success("Candidate permanently deleted");
              setDeleteOpen(false);
              router.push("/candidates");
            },
            onError: (e) =>
              toast.error(e instanceof ApiError ? e.message : "Could not delete candidate"),
          });
        }}
      />

      <AnonymizeCandidateDialog
        open={anonymizeOpen}
        onOpenChange={setAnonymizeOpen}
        candidateName={name}
        busy={anonymizeCandidate.isPending}
        onConfirm={() => {
          anonymizeCandidate.mutate(data.candidate.id, {
            onSuccess: () => {
              toast.success("Candidate anonymized");
              setAnonymizeOpen(false);
              void detail.refetch();
            },
            onError: (e) =>
              toast.error(e instanceof ApiError ? e.message : "Could not anonymize candidate"),
          });
        }}
      />
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
