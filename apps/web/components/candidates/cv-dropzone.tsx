"use client";

import { AlertCircle, FileText, Loader2, UploadCloud, X } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";

import { CV_ACCEPT, cvFileError, MAX_CV_BYTES } from "@/components/careers/cv-dropzone";
import { cn } from "@/lib/utils";

export type CvUploadItem = {
  id: string;
  file: File;
  status: "ready" | "parsing" | "done" | "error";
  error?: string;
};

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function newId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `cv-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

interface MultiCvDropzoneProps {
  items: CvUploadItem[];
  onChange: (items: CvUploadItem[]) => void;
}

export function MultiCvDropzone({ items, onChange }: MultiCvDropzoneProps) {
  const id = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const addFiles = (list: FileList | null) => {
    if (!list?.length) return;
    const next: CvUploadItem[] = [];
    for (const file of Array.from(list)) {
      const err = cvFileError(file);
      if (err) {
        next.push({ id: newId(), file, status: "error", error: err });
      } else {
        next.push({ id: newId(), file, status: "ready" });
      }
    }
    onChange([...items, ...next]);
  };

  const remove = (itemId: string) => {
    onChange(items.filter((i) => i.id !== itemId));
    if (inputRef.current) inputRef.current.value = "";
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    addFiles(event.dataTransfer.files);
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-center transition-colors",
          dragging ? "border-primary bg-accent" : "border-input bg-muted/30",
        )}
      >
        <UploadCloud className="h-8 w-8 text-muted-foreground" aria-hidden />
        <p className="text-sm">
          <span className="font-medium">Drop CV files here</span>, or{" "}
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            browse
          </button>
        </p>
        <p className="text-xs text-muted-foreground">PDF or DOCX, up to 5 MB each</p>
      </div>
      <input
        ref={inputRef}
        id={id}
        type="file"
        multiple
        accept={CV_ACCEPT}
        className="sr-only"
        onChange={(e) => addFiles(e.target.files)}
      />
      {items.length > 0 && (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className={cn(
                "glass flex items-center gap-3 rounded-xl p-3",
                item.status === "error" && "border-destructive",
              )}
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent">
                {item.status === "parsing" ? (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden />
                ) : item.status === "error" ? (
                  <AlertCircle className="h-4 w-4 text-destructive" aria-hidden />
                ) : (
                  <FileText className="h-4 w-4 text-accent-foreground" aria-hidden />
                )}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{item.file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatSize(item.file.size)}
                  {item.file.size > MAX_CV_BYTES && " · exceeds 5 MB"}
                  {item.status === "parsing" && " · Parsing…"}
                  {item.status === "done" && " · Parsed"}
                  {item.error && ` · ${item.error}`}
                </p>
              </div>
              <button
                type="button"
                onClick={() => remove(item.id)}
                className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label={`Remove ${item.file.name}`}
              >
                <X className="h-4 w-4" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
