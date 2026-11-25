"use client";

import { FileText, UploadCloud, X } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";

import { cn } from "@/lib/utils";

export const MAX_CV_BYTES = 5 * 1024 * 1024;
export const CV_ACCEPT =
  ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

/** Client-side check for fast feedback; the API re-checks the real type from file contents. */
export function cvFileError(file: File): string | null {
  if (!/\.(pdf|docx)$/i.test(file.name)) return "Upload a PDF or Word (.docx) file.";
  if (file.size === 0) return "This file is empty.";
  if (file.size > MAX_CV_BYTES) return "The file must be 5 MB or smaller.";
  return null;
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface CvDropzoneProps {
  value: File | null;
  onChange: (file: File | null) => void;
  error?: string;
}

export function CvDropzone({ value, onChange, error }: CvDropzoneProps) {
  const id = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const pick = (files: FileList | null) => {
    const file = files?.[0];
    if (file) onChange(file);
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    pick(event.dataTransfer.files);
  };

  const errorId = `${id}-error`;

  return (
    <div className="space-y-2">
      {value ? (
        <div
          className={cn(
            "glass-strong flex items-center gap-3 rounded-control p-4",
            error && "border-destructive",
          )}
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-accent">
            <FileText className="h-5 w-5 text-accent-foreground" aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{value.name}</p>
            <p className="text-xs text-muted-foreground">{formatSize(value.size)}</p>
          </div>
          <button
            type="button"
            onClick={() => {
              onChange(null);
              if (inputRef.current) inputRef.current.value = "";
            }}
            className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={`Remove ${value.name}`}
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={cn(
            "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors",
            dragging ? "border-primary bg-accent" : "border-input bg-muted/30",
            error && "border-destructive",
          )}
        >
          <UploadCloud className="h-8 w-8 text-muted-foreground" aria-hidden />
          <p className="text-sm">
            <span className="font-medium">Drag and drop your CV here</span>, or{" "}
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              browse files
            </button>
          </p>
          <p className="text-xs text-muted-foreground">PDF or DOCX, up to 5 MB</p>
        </div>
      )}
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={CV_ACCEPT}
        className="sr-only"
        tabIndex={-1}
        aria-label="CV file"
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        onChange={(e) => pick(e.target.files)}
      />
      {error && (
        <p id={errorId} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
