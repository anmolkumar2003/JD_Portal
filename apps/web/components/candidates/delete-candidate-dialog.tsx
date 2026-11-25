"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const REMOVED_ITEMS = [
  "Candidate details",
  "Applications",
  "CV and other documents",
  "Parsed CV data",
  "ATS and match scores",
  "Notes",
  "Interview ratings and interviews",
  "Emails log",
  "Notifications",
] as const;

export type DeleteCandidateDialogMode = "single" | "bulk";

interface DeleteCandidateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: DeleteCandidateDialogMode;
  /** Full name for single-candidate confirmation. */
  candidateName?: string;
  /** Number of candidates in a bulk delete. */
  count?: number;
  busy?: boolean;
  onConfirm: () => void;
}

export function DeleteCandidateDialog({
  open,
  onOpenChange,
  mode,
  candidateName = "",
  count = 1,
  busy,
  onConfirm,
}: DeleteCandidateDialogProps) {
  const [typed, setTyped] = useState("");

  useEffect(() => {
    if (!open) setTyped("");
  }, [open]);

  const expected = useMemo(() => {
    if (mode === "bulk") return "DELETE";
    return candidateName.trim();
  }, [mode, candidateName]);

  const canDelete =
    expected.length > 0 && typed.trim().localeCompare(expected, undefined, { sensitivity: "accent" }) === 0;

  const title =
    mode === "bulk"
      ? `Permanently delete ${count} candidate${count === 1 ? "" : "s"}?`
      : `Permanently delete ${candidateName}?`;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setTyped("");
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-w-lg" data-testid="delete-candidate-dialog">
        <DialogHeader>
          <DialogTitle className="text-destructive">{title}</DialogTitle>
          <DialogDescription>
            This deletion is permanent and cannot be undone. The following will be removed for
            {mode === "bulk" ? " each selected candidate" : " this candidate"}:
          </DialogDescription>
        </DialogHeader>

        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {REMOVED_ITEMS.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>

        <div className="space-y-2">
          <Label htmlFor="delete-confirm-input">
            {mode === "bulk"
              ? 'Type DELETE to confirm'
              : `Type the candidate’s full name “${candidateName}” to confirm`}
          </Label>
          <Input
            id="delete-confirm-input"
            data-testid="delete-confirm-input"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            autoComplete="off"
            spellCheck={false}
            disabled={busy}
            placeholder={mode === "bulk" ? "DELETE" : candidateName}
          />
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={busy}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            data-testid="delete-candidate-confirm"
            disabled={busy || !canDelete}
            onClick={() => onConfirm()}
          >
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
