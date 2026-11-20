"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { RejectDialog } from "@/components/candidates/reject-dialog";
import { StageBadge } from "@/components/candidates/stage-badge";
import { ErrorState } from "@/components/error-state";
import { ScoreRing } from "@/components/score-ring";
import { SkillChips } from "@/components/skill-chips";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useApplication, useChangeStage } from "@/hooks/use-applications";
import { usePipelineStages } from "@/hooks/use-lookups";
import { ApiError } from "@/lib/api";
import { SOURCE_LABELS, candidateDisplayName } from "@/lib/labels";
import type { Skill } from "@/types/api";

interface CandidateDrawerProps {
  applicationId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CandidateDrawer({ applicationId, open, onOpenChange }: CandidateDrawerProps) {
  const detail = useApplication(open ? applicationId : null);
  const stages = usePipelineStages();
  const changeStage = useChangeStage();
  const [rejectOpen, setRejectOpen] = useState(false);

  const rejectedStage = useMemo(
    () => stages.data?.find((s) => s.type === "rejected"),
    [stages.data],
  );

  const skills: Skill[] = useMemo(() => {
    const raw = detail.data?.parsed_profile?.data?.skills;
    if (!Array.isArray(raw)) return [];
    return raw
      .map((item) => {
        if (typeof item === "string") return { name: item, weight: 1 };
        if (item && typeof item === "object" && "name" in item) {
          return { name: String(item.name), weight: Number(item.weight) || 1 };
        }
        return null;
      })
      .filter((s): s is Skill => s !== null);
  }, [detail.data]);

  const onStageSelect = (stageId: string) => {
    if (!detail.data || stageId === detail.data.stage.id) return;
    const stage = stages.data?.find((s) => s.id === stageId);
    if (stage?.type === "rejected") {
      setRejectOpen(true);
      return;
    }
    changeStage.mutate({ id: detail.data.id, body: { stage_id: stageId } });
  };

  const name = detail.data
    ? candidateDisplayName(detail.data.candidate.first_name, detail.data.candidate.last_name)
    : "Candidate";

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="flex flex-col overflow-y-auto sm:max-w-md">
          {detail.isPending && (
            <div className="space-y-4" aria-busy="true">
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-24 w-full" />
            </div>
          )}
          {detail.isError && (
            <ErrorState
              error={detail.error}
              title="Could not load candidate"
              onRetry={() => void detail.refetch()}
            />
          )}
          {detail.data && (
            <>
              <SheetHeader>
                <div className="flex items-start gap-3 pr-6">
                  <ScoreRing score={detail.data.match_result?.overall_score ?? null} size="md" />
                  <div className="min-w-0 space-y-1">
                    <SheetTitle>{name}</SheetTitle>
                    <SheetDescription>
                      {detail.data.candidate.current_title ?? "No title"}
                      {detail.data.candidate.current_company
                        ? ` · ${detail.data.candidate.current_company}`
                        : ""}
                    </SheetDescription>
                    <StageBadge name={detail.data.stage.name} type={detail.data.stage.type} />
                  </div>
                </div>
              </SheetHeader>

              <div className="mt-6 space-y-4">
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-muted-foreground">Email</dt>
                    <dd className="truncate">{detail.data.candidate.email}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Source</dt>
                    <dd>{SOURCE_LABELS[detail.data.candidate.source]}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Job</dt>
                    <dd>{detail.data.job.name}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Reference</dt>
                    <dd className="font-mono text-xs">{detail.data.reference_no}</dd>
                  </div>
                </dl>

                <div>
                  <h3 className="mb-2 text-sm font-medium">Skills</h3>
                  <SkillChips
                    skills={skills}
                    showWeights={false}
                    emptyLabel="No parsed skills yet."
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="drawer-stage">Stage</Label>
                  <Select
                    id="drawer-stage"
                    value={detail.data.stage.id}
                    onChange={(e) => onStageSelect(e.target.value)}
                    disabled={changeStage.isPending || !stages.data}
                  >
                    {(stages.data ?? [detail.data.stage]).map((stage) => (
                      <option key={stage.id} value={stage.id}>
                        {stage.name}
                      </option>
                    ))}
                  </Select>
                </div>

                {changeStage.isError && (
                  <p role="alert" className="text-sm text-destructive">
                    {changeStage.error instanceof ApiError
                      ? changeStage.error.message
                      : "Could not update stage."}
                  </p>
                )}

                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="destructive"
                    disabled={!rejectedStage || changeStage.isPending}
                    onClick={() => setRejectOpen(true)}
                  >
                    Reject
                  </Button>
                  <Button asChild variant="outline">
                    <Link href={`/candidates/${detail.data.candidate.id}?app=${detail.data.id}`}>
                      Open profile
                    </Link>
                  </Button>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {detail.data && rejectedStage && (
        <RejectDialog
          open={rejectOpen}
          onOpenChange={setRejectOpen}
          candidateName={name}
          isPending={changeStage.isPending}
          onConfirm={(reason) => {
            changeStage.mutate(
              {
                id: detail.data.id,
                body: { stage_id: rejectedStage.id, rejection_reason: reason },
              },
              { onSuccess: () => setRejectOpen(false) },
            );
          }}
        />
      )}
    </>
  );
}
