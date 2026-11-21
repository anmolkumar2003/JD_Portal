"use client";

import { ExternalLink, Loader2 } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { RejectDialog } from "@/components/candidates/reject-dialog";
import { ScoreRing } from "@/components/score-ring";
import { StageBadge } from "@/components/stage-badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useApplication, useMoveStage, usePipelineStages } from "@/hooks/use-applications";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";
import { CANDIDATE_SOURCE_LABELS, formatDate } from "@/lib/labels";
import { canMoveStages } from "@/lib/permissions";

interface CandidateDrawerProps {
  applicationId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  jobId?: string;
}

export function CandidateDrawer({
  applicationId,
  open,
  onOpenChange,
  jobId,
}: CandidateDrawerProps) {
  const { user } = useAuth();
  const canEdit = canMoveStages(user?.role);
  const detail = useApplication(open ? applicationId : null);
  const stages = usePipelineStages();
  const moveStage = useMoveStage();
  const [rejectOpen, setRejectOpen] = useState(false);

  const rejectedStage = useMemo(
    () => (stages.data ?? []).find((s) => s.type === "rejected"),
    [stages.data],
  );

  const data = detail.data;
  const name = data ? `${data.candidate.first_name} ${data.candidate.last_name}` : "Candidate";

  const onStageChange = (stageId: string) => {
    if (!data || stageId === data.stage.id) return;
    const target = (stages.data ?? []).find((s) => s.id === stageId);
    if (target?.type === "rejected") {
      setRejectOpen(true);
      return;
    }
    moveStage.mutate({
      applicationId: data.id,
      body: { stage_id: stageId },
      jobId: jobId ?? data.job.id,
    });
  };

  const onReject = (reason: string) => {
    if (!data || !rejectedStage) return;
    moveStage.mutate(
      {
        applicationId: data.id,
        body: { stage_id: rejectedStage.id, reason },
        jobId: jobId ?? data.job.id,
      },
      {
        onSuccess: () => setRejectOpen(false),
      },
    );
  };

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="flex flex-col overflow-y-auto">
          {detail.isPending && (
            <div className="space-y-4" aria-busy="true">
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-4 w-64" />
              <Skeleton className="h-32 w-full" />
            </div>
          )}
          {detail.isError && (
            <p role="alert" className="text-sm text-destructive">
              {detail.error instanceof ApiError
                ? detail.error.message
                : "Could not load candidate."}
            </p>
          )}
          {data && (
            <>
              <SheetHeader>
                <SheetTitle>{name}</SheetTitle>
                <SheetDescription>
                  {data.candidate.current_title ?? "No current title"} · {data.job.name}
                </SheetDescription>
              </SheetHeader>

              <div className="mt-6 space-y-5 text-sm">
                <div className="flex flex-wrap items-center gap-3">
                  <StageBadge stage={data.stage} />
                  <ScoreRing score={data.match_result?.overall_score ?? null} />
                </div>

                <dl className="grid grid-cols-1 gap-3">
                  <div>
                    <dt className="text-muted-foreground">Email</dt>
                    <dd>{data.candidate.email}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Phone</dt>
                    <dd>{data.candidate.phone ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Source</dt>
                    <dd>{CANDIDATE_SOURCE_LABELS[data.candidate.source]}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Applied</dt>
                    <dd>{formatDate(data.applied_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Reference</dt>
                    <dd className="font-mono text-xs">{data.reference_no}</dd>
                  </div>
                </dl>

                {canEdit && (
                  <div className="space-y-2">
                    <Label htmlFor="drawer-stage">Stage</Label>
                    <Select
                      id="drawer-stage"
                      value={data.stage.id}
                      disabled={moveStage.isPending}
                      onChange={(e) => onStageChange(e.target.value)}
                    >
                      {(stages.data ?? [data.stage]).map((stage) => (
                        <option key={stage.id} value={stage.id}>
                          {stage.name}
                        </option>
                      ))}
                    </Select>
                  </div>
                )}

                {moveStage.isError && (
                  <p role="alert" className="text-sm text-destructive">
                    {moveStage.error instanceof ApiError
                      ? moveStage.error.message
                      : "Could not update stage."}
                  </p>
                )}
              </div>

              <SheetFooter className="mt-8 gap-2 sm:flex-col">
                {canEdit && rejectedStage && data.stage.type !== "rejected" && (
                  <Button
                    type="button"
                    variant="destructive"
                    disabled={moveStage.isPending}
                    onClick={() => setRejectOpen(true)}
                  >
                    {moveStage.isPending ? <Loader2 className="animate-spin" aria-hidden /> : null}
                    Reject
                  </Button>
                )}
                <Button asChild variant="outline">
                  <Link href={`/candidates/${data.candidate.id}?application=${data.id}`}>
                    Full profile
                    <ExternalLink aria-hidden />
                  </Link>
                </Button>
              </SheetFooter>
            </>
          )}
        </SheetContent>
      </Sheet>

      <RejectDialog
        open={rejectOpen}
        onOpenChange={setRejectOpen}
        candidateName={name}
        busy={moveStage.isPending}
        onConfirm={onReject}
      />
    </>
  );
}
