"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { MoveToMenu } from "@/components/pipeline/move-to-menu";
import { ScoreRing } from "@/components/score-ring";
import { candidateDisplayName, daysInStage } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { BoardCard, PipelineStage } from "@/types/api";

interface ApplicationCardProps {
  card: BoardCard;
  stageId: string;
  stages: PipelineStage[];
  onOpen: (applicationId: string) => void;
  onMoveTo: (applicationId: string, stage: PipelineStage) => void;
  disabled?: boolean;
}

export function ApplicationCard({
  card,
  stageId,
  stages,
  onOpen,
  onMoveTo,
  disabled,
}: ApplicationCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: card.id,
    data: { stageId },
    disabled,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const days = daysInStage(card.stage_entered_at);

  return (
    <article
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={cn(
        "cursor-grab rounded-md border bg-card p-3 shadow-sm active:cursor-grabbing",
        isDragging && "opacity-60 ring-2 ring-ring",
      )}
      onClick={() => onOpen(card.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(card.id);
        }
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">
            {candidateDisplayName(card.first_name, card.last_name)}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {card.current_title ?? "No title"}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <ScoreRing score={card.overall_score} />
          <MoveToMenu
            stages={stages}
            currentStageId={stageId}
            disabled={disabled}
            onSelect={(stage) => onMoveTo(card.id, stage)}
          />
        </div>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        {days === 0 ? "Today" : `${days}d in stage`}
      </p>
    </article>
  );
}
