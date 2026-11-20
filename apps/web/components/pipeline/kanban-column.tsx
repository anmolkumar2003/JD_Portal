"use client";

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";

import { ApplicationCard } from "@/components/pipeline/application-card";
import { cn } from "@/lib/utils";
import type { BoardCard, PipelineStage } from "@/types/api";

interface KanbanColumnProps {
  stage: PipelineStage;
  count: number;
  cards: BoardCard[];
  allStages: PipelineStage[];
  onOpen: (applicationId: string) => void;
  onMoveTo: (applicationId: string, stage: PipelineStage) => void;
  disabled?: boolean;
}

export function KanbanColumn({
  stage,
  count,
  cards,
  allStages,
  onOpen,
  onMoveTo,
  disabled,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: stage.id });

  return (
    <section
      className={cn(
        "flex w-72 shrink-0 flex-col rounded-lg border bg-muted/30",
        isOver && "ring-2 ring-primary/40",
      )}
      aria-label={`${stage.name}, ${count} candidates`}
    >
      <header className="flex items-center justify-between border-b px-3 py-2">
        <h3 className="text-sm font-semibold">{stage.name}</h3>
        <span className="rounded-full bg-background px-2 py-0.5 text-xs tabular-nums text-muted-foreground">
          {count}
        </span>
      </header>
      <div ref={setNodeRef} className="flex min-h-[12rem] flex-1 flex-col gap-2 p-2">
        <SortableContext items={cards.map((c) => c.id)} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <ApplicationCard
              key={card.id}
              card={card}
              stageId={stage.id}
              stages={allStages}
              onOpen={onOpen}
              onMoveTo={onMoveTo}
              disabled={disabled}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-muted-foreground">No candidates</p>
        )}
      </div>
    </section>
  );
}
