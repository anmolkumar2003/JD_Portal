"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileWarning, Loader2, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog, type ConfirmRequest } from "@/components/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDocumentUrl } from "@/hooks/use-applications";
import { useAuth } from "@/hooks/use-auth";
import { ApiError, api } from "@/lib/api";
import { canManageJobs } from "@/lib/permissions";
import type { DocumentOut } from "@/types/api";

interface CvViewerProps {
  documents: DocumentOut[];
  applicationId?: string;
}

export function CvViewer({ documents, applicationId }: CvViewerProps) {
  const { user } = useAuth();
  const canEdit = canManageJobs(user?.role);
  const queryClient = useQueryClient();
  const cv =
    documents.find((d) => d.type === "cv" && d.is_primary) ??
    documents.find((d) => d.type === "cv") ??
    documents[0];

  const download = useDocumentUrl(cv?.id ?? null);
  const [renameOpen, setRenameOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [confirm, setConfirm] = useState<ConfirmRequest | null>(null);

  const rename = useMutation({
    mutationFn: (file_name: string) => api.documents.rename(cv!.id, file_name),
    onSuccess: () => {
      setRenameOpen(false);
      toast.success("Document renamed");
      if (applicationId) {
        void queryClient.invalidateQueries({ queryKey: ["applications", "detail", applicationId] });
      }
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not rename"),
  });

  const remove = useMutation({
    mutationFn: () => api.documents.delete(cv!.id),
    onSuccess: () => {
      toast.success("Document deleted");
      if (applicationId) {
        void queryClient.invalidateQueries({ queryKey: ["applications", "detail", applicationId] });
      }
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not delete"),
  });

  if (!cv) {
    return (
      <EmptyState
        icon={FileWarning}
        title="No CV uploaded"
        description="This application does not have a CV document yet."
      />
    );
  }

  if (download.isPending) {
    return (
      <div className="glass-strong flex h-[70vh] items-center justify-center rounded-[var(--radius)]" aria-busy="true">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" aria-label="Loading CV" />
      </div>
    );
  }

  if (download.isError || !download.data) {
    return (
      <ErrorState
        error={download.error}
        title="Could not load CV"
        onRetry={() => void download.refetch()}
      />
    );
  }

  const isPdf = cv.mime_type.includes("pdf") || cv.file_name.toLowerCase().endsWith(".pdf");

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">{cv.file_name}</p>
        <div className="flex flex-wrap items-center gap-2">
          {canEdit && (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setNewName(cv.file_name);
                  setRenameOpen(true);
                }}
              >
                <Pencil className="mr-1 h-4 w-4" aria-hidden />
                Rename
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  setConfirm({
                    title: "Delete this document?",
                    description: "The file will be removed from storage. This cannot be undone.",
                    confirmLabel: "Delete document",
                    destructive: true,
                    onConfirm: () => remove.mutate(),
                  })
                }
                disabled={remove.isPending}
              >
                <Trash2 className="mr-1 h-4 w-4" aria-hidden />
                Delete
              </Button>
            </>
          )}
          <a
            href={download.data.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-11 items-center text-sm text-primary hover:underline"
          >
            Open in new tab
          </a>
        </div>
      </div>
      {isPdf ? (
        <iframe
          title={`CV: ${cv.file_name}`}
          src={download.data.url}
          className="glass-strong h-[70vh] w-full rounded-[var(--radius)] bg-muted/20"
        />
      ) : (
        <EmptyState
          icon={FileWarning}
          title="Preview not available"
          description="This file type cannot be shown inline. Use Open in new tab to download it."
        />
      )}

      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename document</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="doc-file-name">File name</Label>
            <Input
              id="doc-file-name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setRenameOpen(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              disabled={!newName.trim() || rename.isPending}
              onClick={() => rename.mutate(newName.trim())}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog request={confirm} onClose={() => setConfirm(null)} />
    </div>
  );
}
