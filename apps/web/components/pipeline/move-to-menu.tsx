"use client";

import { MoreVertical } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { PipelineStage } from "@/types/api";

interface MoveToMenuProps {
  stages: PipelineStage[];
  currentStageId: string;
  disabled?: boolean;
  onSelect: (stage: PipelineStage) => void;
}

export function MoveToMenu({ stages, currentStageId, disabled, onSelect }: MoveToMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          aria-label="Move to stage"
          disabled={disabled}
          onClick={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
        >
          <MoreVertical className="h-4 w-4" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
        <DropdownMenuLabel>Move to</DropdownMenuLabel>
        {stages.map((stage) => (
          <DropdownMenuItem
            key={stage.id}
            disabled={stage.id === currentStageId}
            onSelect={() => onSelect(stage)}
          >
            {stage.name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
