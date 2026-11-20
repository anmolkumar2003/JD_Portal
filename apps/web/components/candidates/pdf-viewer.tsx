"use client";

import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "@/components/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

interface PdfViewerProps {
  documentId: string | null;
  fileName?: string;
}

export function PdfViewer({ documentId, fileName }: PdfViewerProps) {
  const download = useQuery({
    queryKey: ["documents", "download-url", documentId],
    queryFn: () => api.documents.downloadUrl(documentId as string),
    enabled: Boolean(documentId),
    staleTime: 60_000,
  });

  if (!documentId) {
    return <p className="text-sm text-muted-foreground">No CV uploaded for this application.</p>;
  }
  if (download.isPending) {
    return <Skeleton className="h-[70vh] w-full" aria-label="Loading CV" />;
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

  return (
    <iframe
      title={fileName ?? download.data.file_name}
      src={download.data.url}
      className="h-[70vh] w-full rounded-md border bg-muted"
    />
  );
}
