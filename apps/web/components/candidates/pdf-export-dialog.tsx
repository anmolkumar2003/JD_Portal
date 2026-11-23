"use client";

import { Loader2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, ApiError, triggerBrowserDownload } from "@/lib/api";

export interface PdfExportOptions {
  include_salary: boolean;
  include_contact: boolean;
  include_hr_notes: boolean;
}

interface PdfExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  applicationIds: string[];
  title?: string;
}

const DEFAULTS: PdfExportOptions = {
  include_salary: false,
  include_contact: true,
  include_hr_notes: false,
};

export function PdfExportDialog({
  open,
  onOpenChange,
  applicationIds,
  title = "Download PDF summary",
}: PdfExportDialogProps) {
  const [options, setOptions] = useState<PdfExportOptions>(DEFAULTS);
  const [busy, setBusy] = useState(false);

  const count = applicationIds.length;
  const description =
    count === 1
      ? "Choose what to include in the candidate PDF summary."
      : `One PDF per candidate (${count}), delivered as a ZIP archive.`;

  const onDownload = async () => {
    if (count === 0) {
      toast.error("Select at least one candidate.");
      return;
    }
    setBusy(true);
    try {
      const { blob, filename } = await api.exports.pdfSummaries({
        application_ids: applicationIds,
        ...options,
      });
      const fallback = count === 1 ? "candidate-summary.pdf" : "candidate-summaries.zip";
      triggerBrowserDownload(blob, filename || fallback);
      toast.success(count === 1 ? "PDF downloaded" : `ZIP with ${count} PDFs downloaded`);
      onOpenChange(false);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "PDF export failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setOptions(DEFAULTS);
        onOpenChange(next);
      }}
    >
      <DialogContent data-component="pdf-export-dialog">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <fieldset className="space-y-3" disabled={busy}>
          <legend className="sr-only">PDF contents</legend>
          {(
            [
              ["include_contact", "Include contact details", true],
              ["include_salary", "Include salary details", false],
              ["include_hr_notes", "Include HR notes", false],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex cursor-pointer items-center gap-2 text-sm font-medium">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-input"
                checked={options[key]}
                onChange={(e) => setOptions((prev) => ({ ...prev, [key]: e.target.checked }))}
              />
              {label}
            </label>
          ))}
        </fieldset>
        <p className="text-xs text-muted-foreground">
          Scores are advisory. Exports are audited and not stored on the server.
        </p>
        <DialogFooter>
          <Button type="button" variant="outline" disabled={busy} onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" disabled={busy || count === 0} onClick={() => void onDownload()}>
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
            Download
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
