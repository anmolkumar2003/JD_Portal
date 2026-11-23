"use client";

import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { LayoutGrid, List, Users } from "lucide-react";
import { useMemo, useState } from "react";

import { CandidateDrawer } from "@/components/candidates/candidate-drawer";
import { PipelineCard } from "@/components/candidates/pipeline-card";
import { PipelineTable } from "@/components/candidates/pipeline-table";
import { RejectDialog } from "@/components/candidates/reject-dialog";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useJobBoard, useMoveStage } from "@/hooks/use-applications";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";
import { canMoveStages } from "@/lib/permissions";
import type { BoardCard, StageRef } from "@/types/api";

interface PipelineBoardProps {
  jobId: string;
}

function StageColumn({
  stage,
  cards,
  stages,
  canEdit,
  busy,
  onOpen,
  onMoveTo,
}: {
  stage: StageRef;
  cards: BoardCard[];
  stages: StageRef[];
  canEdit: boolean;
  busy: boolean;
  onOpen: (id: string) => void;
  onMoveTo: (applicationId: string, stageId: string) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: stage.id,
    data: { stageId: stage.id },
  });

  return (
    <section
      ref={setNodeRef}
      className={`glass flex w-72 shrink-0 flex-col rounded-xl transition-shadow ${
        isOver ? "ring-2 ring-primary/40 shadow-glow-sm" : ""
      }`}
      aria-label={`${stage.name}, ${cards.length} candidates`}
    >
      <header className="flex items-center justify-between border-b border-border/50 px-3 py-2.5">
        <h3 className="text-sm font-semibold">{stage.name}</h3>
        <span className="rounded-full bg-gradient-brand-soft px-2.5 py-0.5 text-xs font-medium tabular-nums text-primary ring-1 ring-primary/15">
          {cards.length}
        </span>
      </header>
      <div className="flex max-h-[32rem] flex-col gap-2 overflow-y-auto p-2">
        {cards.map((card) => (
          <PipelineCard
            key={card.id}
            card={card}
            stages={stages}
            currentStageId={stage.id}
            canEdit={canEdit}
            disabled={busy}
            onOpen={onOpen}
            onMoveTo={onMoveTo}
          />
        ))}
        {cards.length === 0 && (
          <p className="px-1 py-6 text-center text-xs text-muted-foreground">No candidates</p>
        )}
      </div>
    </section>
  );
}

export function PipelineBoard({ jobId }: PipelineBoardProps) {
  const { user } = useAuth();
  const canEdit = canMoveStages(user?.role);
  const board = useJobBoard(jobId);
  const moveStage = useMoveStage();
  const [view, setView] = useState<"kanban" | "table">("kanban");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [drawerId, setDrawerId] = useState<string | null>(null);
  const [rejectTarget, setRejectTarget] = useState<{
    applicationId: string;
    stageId: string;
    name: string;
  } | null>(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  const stages = useMemo(() => board.data?.stages.map((c) => c.stage) ?? [], [board.data]);
  const cardsById = useMemo(() => {
    const map = new Map<string, BoardCard>();
    for (const col of board.data?.stages ?? []) {
      for (const card of col.cards) map.set(card.id, card);
    }
    return map;
  }, [board.data]);

  const stageOf = (applicationId: string): string | undefined => {
    for (const col of board.data?.stages ?? []) {
      if (col.cards.some((c) => c.id === applicationId)) return col.stage.id;
    }
    return undefined;
  };

  const requestMove = (applicationId: string, stageId: string) => {
    const current = stageOf(applicationId);
    if (!current || current === stageId) return;
    const target = stages.find((s) => s.id === stageId);
    const card = cardsById.get(applicationId);
    if (target?.type === "rejected") {
      setRejectTarget({
        applicationId,
        stageId,
        name: card ? `${card.first_name} ${card.last_name}` : "candidate",
      });
      return;
    }
    moveStage.mutate({ applicationId, body: { stage_id: stageId }, jobId });
  };

  const onDragStart = (event: DragStartEvent) => {
    setActiveId(String(event.active.id));
  };

  const onDragEnd = (event: DragEndEvent) => {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;
    const applicationId = String(active.id);
    const overData = over.data.current as { stageId?: string } | undefined;
    const overId = String(over.id);
    const targetStageId =
      overData?.stageId ??
      (stages.some((s) => s.id === overId) ? overId : stageOf(overId.replace(/^card:/, "")));
    if (!targetStageId) return;
    requestMove(applicationId, targetStageId);
  };

  if (board.isPending) {
    return (
      <div className="flex gap-3 overflow-x-auto" aria-busy="true" aria-label="Loading pipeline">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-64 w-72 shrink-0" />
        ))}
      </div>
    );
  }

  if (board.isError) {
    return (
      <ErrorState
        error={board.error}
        title="Could not load pipeline"
        onRetry={() => void board.refetch()}
      />
    );
  }

  const data = board.data;
  if (!data) return null;

  const total = data.stages.reduce((sum, col) => sum + col.count, 0);
  const activeCard = activeId ? cardsById.get(activeId) : undefined;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {total} applicant{total === 1 ? "" : "s"} across {data.stages.length} stages
        </p>
        <div className="inline-flex rounded-md border p-0.5">
          <Button
            type="button"
            size="sm"
            variant={view === "kanban" ? "secondary" : "ghost"}
            onClick={() => setView("kanban")}
            aria-pressed={view === "kanban"}
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

      {moveStage.isError && (
        <p
          role="alert"
          className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
        >
          {moveStage.error instanceof ApiError
            ? moveStage.error.message
            : "Stage update failed and was rolled back."}
        </p>
      )}

      {view === "table" ? (
        <PipelineTable board={data} isLoading={false} error={null} onRowClick={setDrawerId} />
      ) : total === 0 ? (
        <EmptyState
          icon={Users}
          title="No applicants yet"
          description="Publish this job and share the careers link to start receiving applications."
        />
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={onDragStart}
          onDragEnd={onDragEnd}
          onDragCancel={() => setActiveId(null)}
        >
          <div className="flex gap-3 overflow-x-auto pb-2">
            {data.stages.map((col) => (
              <StageColumn
                key={col.stage.id}
                stage={col.stage}
                cards={col.cards}
                stages={stages}
                canEdit={canEdit}
                busy={moveStage.isPending}
                onOpen={setDrawerId}
                onMoveTo={requestMove}
              />
            ))}
          </div>
          <DragOverlay>
            {activeCard ? (
              <div className="glass-strong w-72 rounded-xl p-3 shadow-glow">
                <p className="font-medium">
                  {activeCard.first_name} {activeCard.last_name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {activeCard.current_title ?? "No current title"}
                </p>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      )}

      <CandidateDrawer
        applicationId={drawerId}
        open={Boolean(drawerId)}
        onOpenChange={(open) => {
          if (!open) setDrawerId(null);
        }}
        jobId={jobId}
      />

      <RejectDialog
        open={Boolean(rejectTarget)}
        onOpenChange={(open) => {
          if (!open) setRejectTarget(null);
        }}
        candidateName={rejectTarget?.name ?? "candidate"}
        busy={moveStage.isPending}
        onConfirm={(reason) => {
          if (!rejectTarget) return;
          moveStage.mutate(
            {
              applicationId: rejectTarget.applicationId,
              body: { stage_id: rejectTarget.stageId, reason },
              jobId,
            },
            { onSuccess: () => setRejectTarget(null) },
          );
        }}
      />
    </div>
  );
}
