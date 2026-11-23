"use client";

import { useDraggable, useDroppable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { MoreHorizontal } from "lucide-react";

import { ScoreRing } from "@/components/score-ring";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { DaysInStageBadge } from "@/components/days-in-stage-badge";
import { cn } from "@/lib/utils";
import type { BoardCard, StageRef } from "@/types/api";

interface PipelineCardProps {
  card: BoardCard;
  stages: StageRef[];
  currentStageId: string;
  canEdit: boolean;
  onOpen: (applicationId: string) => void;
  onMoveTo: (applicationId: string, stageId: string) => void;
  disabled?: boolean;
}

export function PipelineCard({
  card,
  stages,
  currentStageId,
  canEdit,
  onOpen,
  onMoveTo,
  disabled,
}: PipelineCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef: setDragRef,
    transform,
    isDragging,
  } = useDraggable({
    id: card.id,
    disabled: !canEdit || disabled,
    data: { stageId: currentStageId },
  });
  const { setNodeRef: setDropRef, isOver } = useDroppable({
    id: `card:${card.id}`,
    data: { stageId: currentStageId },
  });

  const setNodeRef = (node: HTMLElement | null) => {
    setDragRef(node);
    setDropRef(node);
  };

  const style = transform
    ? { transform: CSS.Translate.toString(transform), opacity: isDragging ? 0.4 : 1 }
    : undefined;

  const otherStages = stages.filter((s) => s.id !== currentStageId);

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={cn(
        "rounded-md border bg-card p-3 shadow-sm",
        isDragging && "ring-2 ring-ring",
        isOver && "ring-2 ring-primary/30",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <button
          type="button"
          className={cn(
            "min-w-0 flex-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            canEdit && "cursor-grab active:cursor-grabbing",
          )}
          onClick={() => onOpen(card.id)}
          {...(canEdit ? { ...attributes, ...listeners } : {})}
        >
          <p className="truncate font-medium">
            {card.first_name} {card.last_name}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {card.current_title ?? "No current title"}
          </p>
        </button>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <ScoreRing score={card.overall_score} size={32} />
          <span className="text-[10px] tabular-nums text-muted-foreground">
            {card.overall_rating != null
              ? `Int ${Number(card.overall_rating).toFixed(1)}/5`
              : "Int —"}
          </span>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        <DaysInStageBadge stageEnteredAt={card.stage_entered_at} />
        {canEdit && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                aria-label={`Move ${card.first_name} ${card.last_name}`}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {otherStages.map((stage) => (
                <DropdownMenuItem key={stage.id} onSelect={() => onMoveTo(card.id, stage.id)}>
                  Move to {stage.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </article>
  );
}
