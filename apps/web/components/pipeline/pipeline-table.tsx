"use client";

import { MoveToMenu } from "@/components/pipeline/move-to-menu";
import { ScoreRing } from "@/components/score-ring";
import { DataTable, type Column } from "@/components/data-table";
import { StageBadge } from "@/components/candidates/stage-badge";
import { EmptyState } from "@/components/empty-state";
import { candidateDisplayName, daysInStage } from "@/lib/labels";
import type { Board, BoardCard, PipelineStage } from "@/types/api";
import { Users } from "lucide-react";
import { useMemo } from "react";

interface Row extends BoardCard {
  stage: PipelineStage;
}

interface PipelineTableProps {
  board: Board;
  onOpenApplication: (applicationId: string) => void;
  onMoveTo: (applicationId: string, stage: PipelineStage) => void;
  disabled?: boolean;
}

export function PipelineTable({
  board,
  onOpenApplication,
  onMoveTo,
  disabled,
}: PipelineTableProps) {
  const stages = board.stages.map((c) => c.stage);
  const rows: Row[] = useMemo(
    () =>
      board.stages.flatMap((col) =>
        col.cards.map((card) => ({
          ...card,
          stage: col.stage,
        })),
      ),
    [board.stages],
  );

  const columns: Column<Row>[] = [
    {
      id: "name",
      header: "Candidate",
      cell: (row) => (
        <div>
          <p className="font-medium">{candidateDisplayName(row.first_name, row.last_name)}</p>
          <p className="text-xs text-muted-foreground">{row.current_title ?? "—"}</p>
        </div>
      ),
    },
    {
      id: "stage",
      header: "Stage",
      cell: (row) => <StageBadge name={row.stage.name} type={row.stage.type} />,
    },
    {
      id: "days",
      header: "Days in stage",
      cell: (row) => <span className="tabular-nums">{daysInStage(row.stage_entered_at)}</span>,
    },
    {
      id: "score",
      header: "Score",
      cell: (row) => <ScoreRing score={row.overall_score} />,
    },
    {
      id: "actions",
      header: "Move",
      cell: (row) => (
        <MoveToMenu
          stages={stages}
          currentStageId={row.stage.id}
          disabled={disabled}
          onSelect={(stage) => onMoveTo(row.id, stage)}
        />
      ),
    },
  ];

  return (
    <DataTable
      caption="Pipeline applicants"
      columns={columns}
      rows={rows}
      getRowId={(row) => row.id}
      isLoading={false}
      error={null}
      empty={
        <EmptyState
          icon={Users}
          title="No applicants yet"
          description="Applications will appear here as candidates apply."
        />
      }
      onRowClick={(row) => onOpenApplication(row.id)}
    />
  );
}
