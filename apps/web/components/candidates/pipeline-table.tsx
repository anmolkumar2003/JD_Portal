"use client";

import { Users } from "lucide-react";

import { DataTable, type Column } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { ScoreRing } from "@/components/score-ring";
import { StageBadge } from "@/components/stage-badge";
import { DaysInStageBadge } from "@/components/days-in-stage-badge";
import { formatDate } from "@/lib/labels";
import type { BoardCard, BoardOut } from "@/types/api";

interface FlatCard extends BoardCard {
  stage: BoardOut["stages"][number]["stage"];
}

const COLUMNS: Column<FlatCard>[] = [
  {
    id: "name",
    header: "Candidate",
    cell: (row) => (
      <div>
        <p className="font-medium">
          {row.first_name} {row.last_name}
        </p>
        <p className="text-xs text-muted-foreground">{row.reference_no}</p>
      </div>
    ),
  },
  {
    id: "title",
    header: "Current title",
    cell: (row) => row.current_title ?? "—",
  },
  {
    id: "stage",
    header: "Stage",
    cell: (row) => <StageBadge stage={row.stage} />,
  },
  {
    id: "days",
    header: "Days in stage",
    cell: (row) => <DaysInStageBadge stageEnteredAt={row.stage_entered_at} />,
  },
  {
    id: "score",
    header: "Score",
    cell: (row) => <ScoreRing score={row.overall_score} />,
  },
  {
    id: "applied",
    header: "Applied",
    cell: (row) => formatDate(row.applied_at),
  },
];

interface PipelineTableProps {
  board: BoardOut | undefined;
  isLoading: boolean;
  error: unknown;
  onRetry?: () => void;
  onRowClick: (applicationId: string) => void;
}

export function PipelineTable({
  board,
  isLoading,
  error,
  onRetry,
  onRowClick,
}: PipelineTableProps) {
  const rows: FlatCard[] | undefined = board
    ? board.stages.flatMap((col) => col.cards.map((card) => ({ ...card, stage: col.stage })))
    : undefined;

  return (
    <DataTable
      columns={COLUMNS}
      rows={rows}
      getRowId={(row) => row.id}
      isLoading={isLoading}
      error={error}
      onRetry={onRetry}
      onRowClick={(row) => onRowClick(row.id)}
      caption="Pipeline applications"
      empty={
        <EmptyState
          icon={Users}
          title="No applicants yet"
          description="Applications will appear here as candidates apply."
        />
      }
    />
  );
}
