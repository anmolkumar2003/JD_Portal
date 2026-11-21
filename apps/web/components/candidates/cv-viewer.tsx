"use client";

import { FileWarning, Loader2 } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { useDocumentUrl } from "@/hooks/use-applications";
import type { DocumentOut } from "@/types/api";

interface CvViewerProps {
  documents: DocumentOut[];
}

export function CvViewer({ documents }: CvViewerProps) {
  const cv =
    documents.find((d) => d.type === "cv" && d.is_primary) ??
    documents.find((d) => d.type === "cv") ??
    documents[0];

  const download = useDocumentUrl(cv?.id ?? null);

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
      <div className="flex h-[70vh] items-center justify-center rounded-lg border" aria-busy="true">
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
        <a
          href={download.data.url}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-primary hover:underline"
        >
          Open in new tab
        </a>
      </div>
      {isPdf ? (
        <iframe
          title={`CV: ${cv.file_name}`}
          src={download.data.url}
          className="h-[70vh] w-full rounded-lg border bg-muted/20"
        />
      ) : (
        <EmptyState
          icon={FileWarning}
          title="Preview not available"
          description="This file type cannot be shown inline. Use Open in new tab to download it."
        />
      )}
    </div>
  );
}
