"use client";

import { ChevronDown, FileDown, Loader2, Mail, MoreHorizontal, Star, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import { CandidateTagsEditor } from "@/components/candidates/candidate-tags-editor";
import { FinalScorePanel } from "@/components/candidates/final-score-panel";
import { PdfExportDialog } from "@/components/candidates/pdf-export-dialog";
import { RejectDialog } from "@/components/candidates/reject-dialog";
import { ScoreMetric } from "@/components/candidates/score-metric";
import { StageBadge } from "@/components/stage-badge";
import { BudgetBadge } from "@/components/candidates/budget-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  useApplicationFinalScore,
  useMoveStage,
  usePipelineStages,
  useShortlist,
} from "@/hooks/use-applications";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import { canMoveStages, isAdmin } from "@/lib/permissions";
import type { ApplicationDetail } from "@/types/api";

interface CandidateProfileHeaderProps {
  application: ApplicationDetail;
  onEmail?: () => void;
  /** Opens the permanent-delete confirmation (admin only). */
  onDeleteRequest?: () => void;
}

export function CandidateProfileHeader({
  application,
  onEmail,
  onDeleteRequest,
}: CandidateProfileHeaderProps) {
  const { user } = useAuth();
  const canEdit = canMoveStages(user?.role);
  const canExport = isAdmin(user?.role);
  const canDelete = isAdmin(user?.role);
  const stages = usePipelineStages();
  const moveStage = useMoveStage();
  const shortlist = useShortlist();
  const finalScore = useApplicationFinalScore(application.id);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [pdfOpen, setPdfOpen] = useState(false);

  const name = `${application.candidate.first_name} ${application.candidate.last_name}`;

  const rejectedStage = useMemo(
    () => (stages.data ?? []).find((s) => s.type === "rejected"),
    [stages.data],
  );

  const otherStages = useMemo(
    () => (stages.data ?? []).filter((s) => s.id !== application.stage.id && s.type !== "rejected"),
    [stages.data, application.stage.id],
  );

  const onMoveTo = (stageId: string) => {
    moveStage.mutate({
      applicationId: application.id,
      body: { stage_id: stageId },
      jobId: application.job.id,
    });
  };

  const onReject = (reason: string) => {
    if (!rejectedStage) return;
    moveStage.mutate(
      {
        applicationId: application.id,
        body: { stage_id: rejectedStage.id, reason },
        jobId: application.job.id,
      },
      { onSuccess: () => setRejectOpen(false) },
    );
  };

  const fs = finalScore.data;
  const interviewLabel =
    fs?.interview_avg !== null && fs?.interview_avg !== undefined
      ? `${fs.interview_avg} / 5`
      : null;

  return (
    <div className="space-y-4" data-component="candidate-profile-header">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">{name}</h1>
            <StageBadge stage={application.stage} />
            <BudgetBadge status={application.budget_status} />
            <button
              type="button"
              className={cn(
                "rounded p-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                application.is_shortlisted
                  ? "text-warning"
                  : "text-muted-foreground hover:text-foreground",
              )}
              aria-label={application.is_shortlisted ? "Remove from shortlist" : "Add to shortlist"}
              disabled={!canEdit || shortlist.isPending}
              onClick={() =>
                shortlist.mutate({
                  applicationId: application.id,
                  shortlisted: !application.is_shortlisted,
                })
              }
            >
              <Star
                className={cn("h-5 w-5", application.is_shortlisted && "fill-current")}
                aria-hidden
              />
            </button>
          </div>
          <p className="text-sm text-muted-foreground">
            {application.candidate.current_title ?? "No current title"} · {application.job.name}
          </p>
          <CandidateTagsEditor application={application} />
        </div>

        <div className="flex flex-col items-end gap-3">
          <div className="flex flex-wrap items-center justify-end gap-2">
            {canEdit && (
              <>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" disabled={moveStage.isPending}>
                      Move to
                      <ChevronDown className="ml-1 h-4 w-4" aria-hidden />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {otherStages.map((stage) => (
                      <DropdownMenuItem key={stage.id} onSelect={() => onMoveTo(stage.id)}>
                        {stage.name}
                      </DropdownMenuItem>
                    ))}
                    {otherStages.length === 0 && (
                      <DropdownMenuItem disabled>No other stages</DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
                {rejectedStage && application.stage.type !== "rejected" && (
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    disabled={moveStage.isPending}
                    onClick={() => setRejectOpen(true)}
                  >
                    Reject
                  </Button>
                )}
                {onEmail && (
                  <Button type="button" variant="outline" size="sm" onClick={onEmail}>
                    <Mail className="mr-1 h-4 w-4" aria-hidden />
                    Email
                  </Button>
                )}
              </>
            )}
            {canExport && (
              <Button type="button" variant="outline" size="sm" onClick={() => setPdfOpen(true)}>
                <FileDown className="mr-1 h-4 w-4" aria-hidden />
                Download PDF summary
              </Button>
            )}
            {canDelete && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    aria-label="Candidate actions"
                    data-testid="candidate-actions-menu"
                  >
                    <MoreHorizontal className="h-4 w-4" aria-hidden />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    className="text-destructive focus:bg-destructive/10 focus:text-destructive"
                    data-testid="delete-candidate-action"
                    onSelect={() => onDeleteRequest?.()}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                    Delete candidate
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
            {moveStage.isPending && (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden />
            )}
          </div>

          <div className="flex flex-wrap justify-end gap-2" aria-label="Advisory scores">
            <ScoreMetric
              label="Match"
              percentScore={fs?.match_score ?? application.match_result?.overall_score ?? null}
            />
            <ScoreMetric label="ATS" percentScore={fs?.ats_score ?? null} />
            <ScoreMetric label="Interview avg" scaleValue={interviewLabel} />
          </div>
        </div>
      </div>

      <FinalScorePanel applicationId={application.id} />

      <RejectDialog
        open={rejectOpen}
        onOpenChange={setRejectOpen}
        candidateName={name}
        busy={moveStage.isPending}
        onConfirm={onReject}
      />
      <PdfExportDialog
        open={pdfOpen}
        onOpenChange={setPdfOpen}
        applicationIds={[application.id]}
      />
    </div>
  );
}
