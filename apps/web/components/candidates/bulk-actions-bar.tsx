"use client";

import { FileDown, Loader2, X } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { PdfExportDialog } from "@/components/candidates/pdf-export-dialog";
import { RejectDialog } from "@/components/candidates/reject-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useBulkAction, usePipelineStages } from "@/hooks/use-applications";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";
import { isAdmin } from "@/lib/permissions";
import type { ApplicationListItem } from "@/types/api";

interface BulkActionsBarProps {
  selectedIds: string[];
  rows: ApplicationListItem[];
  onClear: () => void;
}

export function BulkActionsBar({ selectedIds, rows, onClear }: BulkActionsBarProps) {
  const { user } = useAuth();
  const canExport = isAdmin(user?.role);
  const bulk = useBulkAction();
  const stages = usePipelineStages();
  const [stageId, setStageId] = useState("");
  const [tag, setTag] = useState("");
  const [rejectOpen, setRejectOpen] = useState(false);
  const [pdfOpen, setPdfOpen] = useState(false);

  const selectedRows = useMemo(
    () => rows.filter((r) => selectedIds.includes(r.id)),
    [rows, selectedIds],
  );

  const label =
    selectedIds.length === 1 && selectedRows[0]
      ? `${selectedRows[0].first_name} ${selectedRows[0].last_name}`
      : `${selectedIds.length} selected`;

  const onMove = () => {
    if (!stageId) {
      toast.error("Choose a stage.");
      return;
    }
    bulk.mutate(
      { action: "move_stage", ids: selectedIds, payload: { stage_id: stageId } },
      {
        onSuccess: (result) => {
          toast.success(`Moved ${result.succeeded.length} application(s)`);
          if (result.failed.length) toast.warning(`${result.failed.length} could not be moved`);
          onClear();
        },
        onError: (e) => toast.error(e instanceof ApiError ? e.message : "Bulk move failed"),
      },
    );
  };

  const onTag = () => {
    const t = tag.trim();
    if (!t) {
      toast.error("Enter a tag.");
      return;
    }
    bulk.mutate(
      { action: "tag", ids: selectedIds, payload: { add_tags: [t] } },
      {
        onSuccess: (result) => {
          toast.success(`Tagged ${result.succeeded.length} application(s)`);
          onClear();
          setTag("");
        },
        onError: (e) => toast.error(e instanceof ApiError ? e.message : "Bulk tag failed"),
      },
    );
  };

  const onReject = (reason: string) => {
    bulk.mutate(
      { action: "reject", ids: selectedIds, payload: { reason } },
      {
        onSuccess: (result) => {
          toast.success(`Rejected ${result.succeeded.length} application(s)`);
          setRejectOpen(false);
          onClear();
        },
        onError: (e) => toast.error(e instanceof ApiError ? e.message : "Bulk reject failed"),
      },
    );
  };

  if (selectedIds.length === 0) return null;

  return (
    <>
      <div
        className="glass sticky bottom-4 z-20 mx-auto flex max-w-4xl flex-wrap items-center gap-3 rounded-[var(--radius)] p-3 shadow-glow-sm"
        role="toolbar"
        aria-label="Bulk actions"
      >
        <span className="text-sm font-medium">{label}</span>
        <Select
          value={stageId}
          onChange={(e) => setStageId(e.target.value)}
          aria-label="Move to stage"
        >
          <option value="">Move to…</option>
          {(stages.data ?? []).map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </Select>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={bulk.isPending}
          onClick={onMove}
        >
          {bulk.isPending && <Loader2 className="mr-1 h-4 w-4 animate-spin" aria-hidden />}
          Move
        </Button>
        <Button
          type="button"
          size="sm"
          variant="destructive"
          disabled={bulk.isPending}
          onClick={() => setRejectOpen(true)}
        >
          Reject
        </Button>
        <div className="flex items-center gap-1">
          <Input
            value={tag}
            onChange={(e) => setTag(e.target.value)}
            placeholder="Tag"
            className="h-8 w-28"
            maxLength={50}
            aria-label="Tag to add"
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={bulk.isPending}
            onClick={onTag}
          >
            Tag
          </Button>
        </div>
        {canExport && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setPdfOpen(true)}
          >
            <FileDown className="mr-1 h-4 w-4" aria-hidden />
            Download PDF summary
          </Button>
        )}
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={onClear}
          aria-label="Clear selection"
        >
          <X className="h-4 w-4" aria-hidden />
        </Button>
      </div>

      <RejectDialog
        open={rejectOpen}
        onOpenChange={setRejectOpen}
        candidateName={label}
        busy={bulk.isPending}
        onConfirm={onReject}
      />
      <PdfExportDialog
        open={pdfOpen}
        onOpenChange={setPdfOpen}
        applicationIds={selectedIds}
        title="Download PDF summaries"
      />
    </>
  );
}
