"use client";

import { Users } from "lucide-react";

import { DataTable, type Column } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { ScoreRing } from "@/components/score-ring";
import { BudgetBadge } from "@/components/candidates/budget-badge";
import { StageBadge } from "@/components/stage-badge";
import { CANDIDATE_SOURCE_LABELS, formatDate } from "@/lib/labels";
import type { ApplicationListItem } from "@/types/api";

const COLUMNS: Column<ApplicationListItem>[] = [
  {
    id: "name",
    header: "Candidate",
    sortKey: "last_name",
    cell: (row) => (
      <div className="min-w-[160px]">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium">
            {row.first_name} {row.last_name}
          </p>
          <BudgetBadge status={row.budget_status} />
        </div>
        <p className="text-xs text-muted-foreground">{row.email}</p>
      </div>
    ),
  },
  {
    id: "job",
    header: "Job",
    cell: (row) => row.job.name,
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
    id: "score",
    header: "Match",
    sortKey: "overall_score",
    cell: (row) => <ScoreRing score={row.overall_score} />,
  },
  {
    id: "interview",
    header: "Interview",
    cell: (row) =>
      row.overall_rating != null ? (
        <span className="text-sm font-medium tabular-nums">
          {Number(row.overall_rating).toFixed(1)}/5
        </span>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  },
  {
    id: "source",
    header: "Source",
    cell: (row) => CANDIDATE_SOURCE_LABELS[row.source],
  },
  {
    id: "applied",
    header: "Applied",
    sortKey: "applied_at",
    cell: (row) => <span className="whitespace-nowrap">{formatDate(row.applied_at)}</span>,
  },
];

interface CandidatesTableProps {
  rows: ApplicationListItem[] | undefined;
  isLoading: boolean;
  error: unknown;
  onRetry?: () => void;
  sort: string;
  onSortChange: (sort: string) => void;
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onRowClick: (row: ApplicationListItem) => void;
  selectedIds?: ReadonlySet<string>;
  onToggleRow?: (id: string) => void;
  onToggleAll?: (ids: string[], select: boolean) => void;
}

export function CandidatesTable({
  rows,
  isLoading,
  error,
  onRetry,
  sort,
  onSortChange,
  page,
  pageSize,
  total,
  onPageChange,
  onRowClick,
  selectedIds,
  onToggleRow,
  onToggleAll,
}: CandidatesTableProps) {
  const selection =
    selectedIds && onToggleRow && onToggleAll
      ? { selectedIds, onToggle: onToggleRow, onToggleAll }
      : undefined;

  return (
    <DataTable
      columns={COLUMNS}
      rows={rows}
      getRowId={(row) => row.id}
      isLoading={isLoading}
      error={error}
      onRetry={onRetry}
      sort={sort}
      onSortChange={onSortChange}
      pagination={{ page, pageSize, total, onPageChange }}
      onRowClick={onRowClick}
      selection={selection}
      caption="Applications"
      empty={
        <EmptyState
          icon={Users}
          title="No candidates yet"
          description="Candidates appear here once people apply through the careers site."
        />
      }
    />
  );
}
