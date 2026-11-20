"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface RejectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateName: string;
  isPending?: boolean;
  onConfirm: (reason: string) => void;
}

export function RejectDialog({
  open,
  onOpenChange,
  candidateName,
  isPending,
  onConfirm,
}: RejectDialogProps) {
  const [reason, setReason] = useState("");
  const trimmed = reason.trim();
  const invalid = trimmed.length < 3;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setReason("");
        onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reject {candidateName}?</DialogTitle>
          <DialogDescription>
            A rejection reason is required and will be recorded on the application timeline.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="rejection-reason">Rejection reason</Label>
          <Textarea
            id="rejection-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Insufficient experience with our stack"
            rows={4}
            maxLength={2000}
            aria-invalid={invalid && reason.length > 0 ? true : undefined}
          />
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            disabled={invalid || isPending}
            onClick={() => onConfirm(trimmed)}
          >
            {isPending ? "Rejecting…" : "Reject candidate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
