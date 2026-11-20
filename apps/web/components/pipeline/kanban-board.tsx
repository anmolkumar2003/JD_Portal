"use client";

import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useMemo, useState } from "react";

import { RejectDialog } from "@/components/candidates/reject-dialog";
import { KanbanColumn } from "@/components/pipeline/kanban-column";
import { ScoreRing } from "@/components/score-ring";
import { useMoveApplicationStage } from "@/hooks/use-pipeline";
import { ApiError } from "@/lib/api";
import { candidateDisplayName } from "@/lib/labels";
import type { Board, BoardCard, PipelineStage } from "@/types/api";

interface KanbanBoardProps {
  jobId: string;
  board: Board;
  onOpenApplication: (applicationId: string) => void;
}

export function KanbanBoard({ jobId, board, onOpenApplication }: KanbanBoardProps) {
  const move = useMoveApplicationStage(jobId);
  const [activeCard, setActiveCard] = useState<BoardCard | null>(null);
  const [rejectTarget, setRejectTarget] = useState<{
    applicationId: string;
    stageId: string;
    name: string;
  } | null>(null);

  const stages = useMemo(() => board.stages.map((col) => col.stage), [board.stages]);
  const cardIndex = useMemo(() => {
    const map = new Map<string, { card: BoardCard; stageId: string }>();
    for (const col of board.stages) {
      for (const card of col.cards) {
        map.set(card.id, { card, stageId: col.stage.id });
      }
    }
    return map;
  }, [board.stages]);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  const requestMove = (applicationId: string, stage: PipelineStage) => {
    const current = cardIndex.get(applicationId);
    if (!current || current.stageId === stage.id) return;
    if (stage.type === "rejected") {
      setRejectTarget({
        applicationId,
        stageId: stage.id,
        name: candidateDisplayName(current.card.first_name, current.card.last_name),
      });
      return;
    }
    move.mutate({ id: applicationId, body: { stage_id: stage.id } });
  };

  const onDragStart = (event: DragStartEvent) => {
    const found = cardIndex.get(String(event.active.id));
    setActiveCard(found?.card ?? null);
  };

  const onDragEnd = (event: DragEndEvent) => {
    setActiveCard(null);
    const { active, over } = event;
    if (!over) return;
    const applicationId = String(active.id);
    const current = cardIndex.get(applicationId);
    if (!current) return;

    let toStageId = String(over.id);
    if (cardIndex.has(toStageId)) {
      toStageId = cardIndex.get(toStageId)?.stageId ?? toStageId;
    }
    const stage = stages.find((s) => s.id === toStageId);
    if (!stage || stage.id === current.stageId) return;
    requestMove(applicationId, stage);
  };

  return (
    <div className="space-y-3">
      {move.isError && (
        <p role="alert" className="text-sm text-destructive">
          {move.error instanceof ApiError
            ? move.error.message
            : "Stage move failed and was rolled back."}
        </p>
      )}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
      >
        <div
          className="flex gap-3 overflow-x-auto pb-2"
          role="list"
          aria-label="Pipeline stages"
        >
          {board.stages.map((column) => (
            <KanbanColumn
              key={column.stage.id}
              stage={column.stage}
              count={column.count}
              cards={column.cards}
              allStages={stages}
              onOpen={onOpenApplication}
              onMoveTo={requestMove}
              disabled={move.isPending}
            />
          ))}
        </div>
        <DragOverlay>
          {activeCard ? (
            <div className="w-72 rounded-md border bg-card p-3 shadow-lg">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium">
                  {candidateDisplayName(activeCard.first_name, activeCard.last_name)}
                </p>
                <ScoreRing score={activeCard.overall_score} />
              </div>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      <RejectDialog
        open={Boolean(rejectTarget)}
        onOpenChange={(open) => {
          if (!open) setRejectTarget(null);
        }}
        candidateName={rejectTarget?.name ?? ""}
        isPending={move.isPending}
        onConfirm={(reason) => {
          if (!rejectTarget) return;
          move.mutate(
            {
              id: rejectTarget.applicationId,
              body: { stage_id: rejectTarget.stageId, rejection_reason: reason },
            },
            { onSuccess: () => setRejectTarget(null) },
          );
        }}
      />
    </div>
  );
}
