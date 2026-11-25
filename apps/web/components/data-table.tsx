"use client";

import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export interface Column<T> {
  id: string;
  header: string;
  cell: (row: T) => ReactNode;
  /** Server-side sort field; omit for unsortable columns. */
  sortKey?: string;
  className?: string;
}

interface Pagination {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

interface RowSelection {
  selectedIds: ReadonlySet<string>;
  onToggle: (id: string) => void;
  onToggleAll: (ids: string[], select: boolean) => void;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[] | undefined;
  getRowId: (row: T) => string;
  isLoading: boolean;
  error: unknown;
  onRetry?: () => void;
  /** Rendered when the request succeeded with no rows. */
  empty: ReactNode;
  /** Current sort, e.g. "title" or "-created_at". */
  sort?: string;
  onSortChange?: (sort: string) => void;
  pagination?: Pagination;
  onRowClick?: (row: T) => void;
  selection?: RowSelection;
  caption: string;
}

function SortIcon({ direction }: { direction: "asc" | "desc" | null }) {
  if (direction === "asc") return <ArrowUp className="h-3.5 w-3.5" aria-hidden />;
  if (direction === "desc") return <ArrowDown className="h-3.5 w-3.5" aria-hidden />;
  return <ArrowUpDown className="h-3.5 w-3.5 opacity-50" aria-hidden />;
}

export function DataTable<T>({
  columns,
  rows,
  getRowId,
  isLoading,
  error,
  onRetry,
  empty,
  sort,
  onSortChange,
  pagination,
  onRowClick,
  selection,
  caption,
}: DataTableProps<T>) {
  if (error && !rows) {
    return <ErrorState error={error} title="Could not load data" onRetry={onRetry} />;
  }
  if (!isLoading && rows && rows.length === 0) {
    return <>{empty}</>;
  }

  const directionFor = (key?: string): "asc" | "desc" | null => {
    if (!key || !sort) return null;
    if (sort === key) return "asc";
    if (sort === `-${key}`) return "desc";
    return null;
  };

  const toggleSort = (key: string) => {
    const current = directionFor(key);
    onSortChange?.(current === "asc" ? `-${key}` : key);
  };

  const totalPages = pagination
    ? Math.max(1, Math.ceil(pagination.total / pagination.pageSize))
    : 1;

  const rowIds = rows?.map(getRowId) ?? [];
  const allSelected = rowIds.length > 0 && rowIds.every((id) => selection?.selectedIds.has(id));
  const someSelected = rowIds.some((id) => selection?.selectedIds.has(id));

  return (
    <div className="glass-strong overflow-hidden rounded-[var(--radius)]">
      <Table aria-busy={isLoading}>
        <caption className="sr-only">{caption}</caption>
        <TableHeader>
          <TableRow>
            {selection && (
              <TableHead className="w-10">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-input"
                  aria-label="Select all on this page"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected && !allSelected;
                  }}
                  onChange={() => selection.onToggleAll(rowIds, !allSelected)}
                />
              </TableHead>
            )}
            {columns.map((column) => {
              const direction = directionFor(column.sortKey);
              return (
                <TableHead
                  key={column.id}
                  className={column.className}
                  aria-sort={
                    direction === "asc"
                      ? "ascending"
                      : direction === "desc"
                        ? "descending"
                        : undefined
                  }
                >
                  {column.sortKey && onSortChange ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(column.sortKey as string)}
                      className="-mx-1 inline-flex items-center gap-1 rounded px-1 uppercase hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      {column.header}
                      <SortIcon direction={direction} />
                    </button>
                  ) : (
                    column.header
                  )}
                </TableHead>
              );
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && !rows
            ? Array.from({ length: 5 }, (_, i) => (
                <TableRow key={`skeleton-${i}`}>
                  {selection && (
                    <TableCell>
                      <Skeleton className="h-4 w-4" />
                    </TableCell>
                  )}
                  {columns.map((column) => (
                    <TableCell key={column.id} className={column.className}>
                      <Skeleton className="h-4 w-full max-w-[160px]" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            : rows?.map((row) => {
                const id = getRowId(row);
                return (
                  <TableRow
                    key={id}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className={cn(onRowClick && "cursor-pointer hover:bg-muted/50")}
                  >
                    {selection && (
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-input"
                          aria-label="Select row"
                          checked={selection.selectedIds.has(id)}
                          onChange={() => selection.onToggle(id)}
                        />
                      </TableCell>
                    )}
                    {columns.map((column) => (
                      <TableCell key={column.id} className={column.className}>
                        {column.cell(row)}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })}
        </TableBody>
      </Table>
      {pagination && pagination.total > 0 && (
        <div className="flex items-center justify-between border-t px-4 py-3 text-sm text-muted-foreground">
          <span>
            {(pagination.page - 1) * pagination.pageSize + 1}–
            {Math.min(pagination.page * pagination.pageSize, pagination.total)} of{" "}
            {pagination.total}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              aria-label="Previous page"
            >
              <ChevronLeft aria-hidden />
            </Button>
            <span>
              Page {pagination.page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(pagination.page + 1)}
              disabled={pagination.page >= totalPages}
              aria-label="Next page"
            >
              <ChevronRight aria-hidden />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
