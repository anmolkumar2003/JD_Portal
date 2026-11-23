"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { applicationKeys } from "@/hooks/use-applications";
import type { ApplicationDetail } from "@/types/api";
import { canManageJobs } from "@/lib/permissions";
import { useAuth } from "@/hooks/use-auth";

interface CandidateTagsEditorProps {
  application: ApplicationDetail;
}

export function CandidateTagsEditor({ application }: CandidateTagsEditorProps) {
  const { user } = useAuth();
  const canEdit = canManageJobs(user?.role);
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const tags = application.candidate.tags;

  const save = useMutation({
    mutationFn: (next: string[]) => api.candidates.setTags(application.candidate.id, next),
    onSuccess: (out) => {
      queryClient.setQueryData<ApplicationDetail>(applicationKeys.detail(application.id), (prev) =>
        prev ? { ...prev, candidate: { ...prev.candidate, tags: out.tags } } : prev,
      );
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
      setDraft("");
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not update tags"),
  });

  const addTag = () => {
    const tag = draft.trim();
    if (!tag || tags.includes(tag)) return;
    if (tags.length >= 20) {
      toast.error("At most 20 tags.");
      return;
    }
    save.mutate([...tags, tag]);
  };

  const removeTag = (tag: string) => {
    save.mutate(tags.filter((t) => t !== tag));
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {tags.map((tag) => (
        <Badge key={tag} variant="secondary" className="gap-1 pr-1">
          {tag}
          {canEdit && (
            <button
              type="button"
              className="rounded p-0.5 hover:bg-muted"
              aria-label={`Remove tag ${tag}`}
              onClick={() => removeTag(tag)}
              disabled={save.isPending}
            >
              <X className="h-3 w-3" aria-hidden />
            </button>
          )}
        </Badge>
      ))}
      {canEdit && (
        <form
          className="flex items-center gap-1"
          onSubmit={(e) => {
            e.preventDefault();
            addTag();
          }}
        >
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Add tag"
            className="h-8 w-28"
            maxLength={50}
            disabled={save.isPending}
            aria-label="New tag"
          />
          <Button
            type="submit"
            size="sm"
            variant="outline"
            disabled={!draft.trim() || save.isPending}
          >
            Add
          </Button>
        </form>
      )}
    </div>
  );
}
