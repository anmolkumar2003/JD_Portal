"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, StickyNote } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/labels";
import type { ApplicationDetail, NoteOut, UserRef } from "@/types/api";

interface NotesPanelProps {
  application: ApplicationDetail;
  onEmail?: () => void;
}

export function NotesPanel({ application, onEmail }: NotesPanelProps) {
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionIds, setMentionIds] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const notes = useQuery({
    queryKey: ["candidates", "notes", application.candidate.id],
    queryFn: () => api.candidates.notes(application.candidate.id),
  });

  const users = useQuery({
    queryKey: ["users", "lookup"],
    queryFn: () => api.users.lookup(),
    staleTime: 5 * 60_000,
  });

  const mentionOptions = useMemo(() => {
    if (!mentionQuery || !users.data) return [];
    const q = mentionQuery.toLowerCase();
    return users.data.filter((u) => u.full_name.toLowerCase().includes(q)).slice(0, 8);
  }, [mentionQuery, users.data]);

  const create = useMutation({
    mutationFn: () =>
      api.candidates.createNote(application.candidate.id, {
        body: body.trim(),
        mentions: mentionIds,
        application_id: application.id,
      }),
    onSuccess: () => {
      setBody("");
      setMentionIds([]);
      void queryClient.invalidateQueries({
        queryKey: ["candidates", "notes", application.candidate.id],
      });
      void queryClient.invalidateQueries({
        queryKey: ["candidates", "timeline", application.candidate.id],
      });
      toast.success("Note added");
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not save note"),
  });

  const insertMention = (user: UserRef) => {
    const el = textareaRef.current;
    const value = body;
    const at = value.lastIndexOf("@");
    if (at < 0) return;
    const next = `${value.slice(0, at)}@${user.full_name} `;
    setBody(next);
    setMentionQuery(null);
    if (!mentionIds.includes(user.id)) setMentionIds((ids) => [...ids, user.id]);
    el?.focus();
  };

  const onBodyChange = (value: string) => {
    setBody(value);
    const match = /@([^\s@]*)$/.exec(value);
    setMentionQuery(match ? (match[1] ?? "") : null);
    const stillMentioned = (users.data ?? []).filter((u) => value.includes(`@${u.full_name}`));
    setMentionIds(stillMentioned.map((u) => u.id));
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        {notes.isPending && <Skeleton className="h-48 w-full" aria-busy="true" />}
        {notes.isError && (
          <ErrorState
            error={notes.error}
            title="Could not load notes"
            onRetry={() => void notes.refetch()}
          />
        )}
        {notes.isSuccess && notes.data.length === 0 && (
          <EmptyState
            icon={StickyNote}
            title="No notes yet"
            description="Leave @mentions for teammates. Notes stay on this candidate profile."
          />
        )}
        {notes.data?.map((note: NoteOut) => (
          <Card key={note.id}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {note.author?.full_name ?? "Unknown"}{" "}
                <span className="font-normal text-muted-foreground">
                  · {formatDateTime(note.created_at)}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{note.body}</p>
              {note.mentions.length > 0 && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Mentioned: {note.mentions.map((m) => m.full_name).join(", ")}
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="h-fit lg:sticky lg:top-4">
        <CardHeader>
          <CardTitle className="text-base">Add note</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="relative">
            <Textarea
              ref={textareaRef}
              value={body}
              onChange={(e) => onBodyChange(e.target.value)}
              placeholder="Write a note… Use @ to mention someone"
              rows={5}
              aria-label="Note body"
            />
            {mentionQuery !== null && mentionOptions.length > 0 && (
              <ul
                className="absolute bottom-full left-0 z-10 mb-1 max-h-40 w-full overflow-y-auto rounded-md border bg-popover p-1 shadow-md"
                role="listbox"
              >
                {mentionOptions.map((user) => (
                  <li key={user.id}>
                    <button
                      type="button"
                      className="w-full rounded px-2 py-1.5 text-left text-sm hover:bg-muted"
                      onClick={() => insertMention(user)}
                    >
                      @{user.full_name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              onClick={() => create.mutate()}
              disabled={!body.trim() || create.isPending}
            >
              {create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
              Save note
            </Button>
            {onEmail && (
              <Button type="button" variant="outline" onClick={onEmail}>
                Email candidate
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
