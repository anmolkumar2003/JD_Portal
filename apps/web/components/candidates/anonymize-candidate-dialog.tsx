"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface AnonymizeCandidateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateName: string;
  busy?: boolean;
  onConfirm: () => void;
}

export function AnonymizeCandidateDialog({
  open,
  onOpenChange,
  candidateName,
  busy,
  onConfirm,
}: AnonymizeCandidateDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="anonymize-candidate-dialog">
        <DialogHeader>
          <DialogTitle>Anonymize {candidateName}?</DialogTitle>
          <DialogDescription>
            This replaces personal details (name, email, phone, links) with anonymous placeholders.
            Applications and documents remain. Prefer this softer option when you only need to remove
            identifying information. Permanent delete is irreversible and removes everything.
          </DialogDescription>
        </DialogHeader>
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
            variant="secondary"
            data-testid="anonymize-candidate-confirm"
            disabled={busy}
            onClick={() => onConfirm()}
          >
            Anonymize
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
