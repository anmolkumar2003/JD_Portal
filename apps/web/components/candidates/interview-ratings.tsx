"use client";

import { Loader2, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog, type ConfirmRequest } from "@/components/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateRating,
  useDeleteRating,
  useInterviewRatings,
  useUpdateRating,
} from "@/hooks/use-ratings";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";
import { formatDateTime, RECOMMENDATION_LABELS } from "@/lib/labels";
import { canManageJobs } from "@/lib/permissions";
import type { InterviewRatingIn, InterviewRatingOut, InterviewRecommendation } from "@/types/api";

const MODES = ["phone", "video", "onsite", "other"] as const;
const RECS: InterviewRecommendation[] = ["strong_no", "no", "mixed", "yes", "strong_yes"];

function defaultForm(): InterviewRatingIn {
  const now = new Date();
  now.setMinutes(0, 0, 0);
  return {
    round_name: "",
    interviewed_at: now.toISOString(),
    interviewer_name: "",
    mode: "video",
    comments: "",
    skill_ratings: [],
    overall_rating: 3,
    recommendation: "mixed",
    strengths: "",
    concerns: "",
  };
}

function fromRating(row: InterviewRatingOut): InterviewRatingIn {
  return {
    round_name: row.round_name,
    interviewed_at: row.interviewed_at,
    interviewer_name: row.interviewer_name,
    interviewer_id: row.interviewer_id,
    mode: row.mode,
    comments: row.comments ?? "",
    skill_ratings: row.skill_ratings ?? [],
    overall_rating: row.overall_rating,
    recommendation: row.recommendation,
    strengths: row.strengths ?? "",
    concerns: row.concerns ?? "",
  };
}

interface RatingFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial: InterviewRatingIn;
  title: string;
  busy: boolean;
  onSubmit: (body: InterviewRatingIn) => void;
}

function RatingFormDialog({
  open,
  onOpenChange,
  initial,
  title,
  busy,
  onSubmit,
}: RatingFormDialogProps) {
  const [form, setForm] = useState(initial);
  const [skillName, setSkillName] = useState("");

  useEffect(() => {
    if (open) setForm(initial);
  }, [open, initial]);

  const addSkill = () => {
    const name = skillName.trim();
    if (!name) return;
    setForm((f) => ({
      ...f,
      skill_ratings: [...(f.skill_ratings ?? []), { skill: name, rating: null }],
    }));
    setSkillName("");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="round_name">Round</Label>
            <Input
              id="round_name"
              value={form.round_name}
              onChange={(e) => setForm((f) => ({ ...f, round_name: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="interviewed_at">Interviewed at</Label>
            <Input
              id="interviewed_at"
              type="datetime-local"
              value={form.interviewed_at.slice(0, 16)}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  interviewed_at: new Date(e.target.value).toISOString(),
                }))
              }
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="interviewer_name">Interviewer</Label>
            <Input
              id="interviewer_name"
              value={form.interviewer_name}
              onChange={(e) => setForm((f) => ({ ...f, interviewer_name: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="mode">Mode</Label>
            <Select
              id="mode"
              value={form.mode ?? "video"}
              onChange={(e) => setForm((f) => ({ ...f, mode: e.target.value }))}
            >
              {MODES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="overall_rating">Overall (1–5)</Label>
            <Input
              id="overall_rating"
              type="number"
              min={1}
              max={5}
              value={form.overall_rating}
              onChange={(e) =>
                setForm((f) => ({ ...f, overall_rating: Number(e.target.value) || 1 }))
              }
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="recommendation">Recommendation</Label>
            <Select
              id="recommendation"
              value={form.recommendation}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  recommendation: e.target.value as InterviewRecommendation,
                }))
              }
            >
              {RECS.map((r) => (
                <option key={r} value={r}>
                  {RECOMMENDATION_LABELS[r]}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="comments">Comments</Label>
            <Textarea
              id="comments"
              value={form.comments ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, comments: e.target.value }))}
              rows={3}
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="strengths">Strengths</Label>
            <Textarea
              id="strengths"
              value={form.strengths ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, strengths: e.target.value }))}
              rows={2}
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="concerns">Concerns</Label>
            <Textarea
              id="concerns"
              value={form.concerns ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, concerns: e.target.value }))}
              rows={2}
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label>Skill ratings</Label>
            <ul className="space-y-2">
              {(form.skill_ratings ?? []).map((sr, idx) => (
                <li key={`${sr.skill}-${idx}`} className="flex items-center gap-2">
                  <span className="min-w-0 flex-1 truncate text-sm">{sr.skill}</span>
                  <Input
                    type="number"
                    className="w-20"
                    min={1}
                    max={5}
                    placeholder="—"
                    value={sr.rating ?? ""}
                    onChange={(e) => {
                      const raw = e.target.value;
                      setForm((f) => {
                        const list = [...(f.skill_ratings ?? [])];
                        const current = list[idx];
                        if (!current) return f;
                        list[idx] = {
                          skill: current.skill,
                          rating: raw === "" ? null : Number(raw),
                        };
                        return { ...f, skill_ratings: list };
                      });
                    }}
                    aria-label={`Rating for ${sr.skill}`}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() =>
                      setForm((f) => ({
                        ...f,
                        skill_ratings: (f.skill_ratings ?? []).filter((_, i) => i !== idx),
                      }))
                    }
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </Button>
                </li>
              ))}
            </ul>
            <div className="flex gap-2">
              <Input
                value={skillName}
                onChange={(e) => setSkillName(e.target.value)}
                placeholder="Skill name"
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addSkill())}
              />
              <Button type="button" variant="outline" onClick={addSkill}>
                Add skill
              </Button>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={
              busy ||
              !form.round_name.trim() ||
              !form.interviewer_name.trim() ||
              !form.overall_rating
            }
            onClick={() => onSubmit(form)}
          >
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface InterviewRatingsProps {
  applicationId: string;
}

export function InterviewRatings({ applicationId }: InterviewRatingsProps) {
  const { user } = useAuth();
  const canEdit = canManageJobs(user?.role);
  const query = useInterviewRatings(applicationId);
  const create = useCreateRating(applicationId);
  const update = useUpdateRating(applicationId);
  const remove = useDeleteRating(applicationId);

  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<InterviewRatingOut | null>(null);
  const [confirm, setConfirm] = useState<ConfirmRequest | null>(null);

  const onCreate = (body: InterviewRatingIn) => {
    create.mutate(body, {
      onSuccess: () => {
        setCreateOpen(false);
        toast.success("Rating saved");
      },
      onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not save rating"),
    });
  };

  const onUpdate = (body: InterviewRatingIn) => {
    if (!editTarget) return;
    update.mutate(
      { id: editTarget.id, body },
      {
        onSuccess: () => {
          setEditTarget(null);
          toast.success("Rating updated");
        },
        onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not update rating"),
      },
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          Interview feedback is advisory and feeds the interview average on the profile header.
        </p>
        {canEdit && (
          <Button type="button" size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-1 h-4 w-4" aria-hidden />
            Add rating
          </Button>
        )}
      </div>

      {query.isPending && <Skeleton className="h-40 w-full" aria-busy="true" />}
      {query.isError && (
        <ErrorState
          error={query.error}
          title="Could not load ratings"
          onRetry={() => void query.refetch()}
        />
      )}
      {query.isSuccess && query.data.length === 0 && (
        <EmptyState
          icon={Plus}
          title="No interview ratings"
          description="Record feedback after each round."
        />
      )}

      <ul className="space-y-3">
        {query.data?.map((row) => (
          <Card key={row.id}>
            <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
              <div>
                <CardTitle className="text-base">{row.round_name}</CardTitle>
                <CardDescription>
                  {row.interviewer_name} · {row.mode} · {formatDateTime(row.interviewed_at)}
                </CardDescription>
              </div>
              {canEdit && (
                <div className="flex gap-1">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setEditTarget(row)}
                  >
                    Edit
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label="Delete rating"
                    onClick={() =>
                      setConfirm({
                        title: "Delete rating?",
                        description: "This updates the interview average.",
                        confirmLabel: "Delete",
                        destructive: true,
                        onConfirm: () =>
                          remove.mutate(row.id, {
                            onError: (e) =>
                              toast.error(e instanceof ApiError ? e.message : "Could not delete"),
                          }),
                      })
                    }
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </Button>
                </div>
              )}
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                Overall: <strong>{row.overall_rating}</strong> / 5 ·{" "}
                {RECOMMENDATION_LABELS[row.recommendation]}
              </p>
              {row.comments && <p className="text-muted-foreground">{row.comments}</p>}
              {(row.skill_ratings ?? []).length > 0 && (
                <ul className="flex flex-wrap gap-2 text-xs">
                  {row.skill_ratings.map((s) => (
                    <li key={s.skill} className="rounded-full border px-2 py-0.5">
                      {s.skill}
                      {s.rating != null ? `: ${s.rating}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        ))}
      </ul>

      <RatingFormDialog
        key="create"
        open={createOpen}
        onOpenChange={setCreateOpen}
        initial={defaultForm()}
        title="New interview rating"
        busy={create.isPending}
        onSubmit={onCreate}
      />
      {editTarget && (
        <RatingFormDialog
          key={editTarget.id}
          open={Boolean(editTarget)}
          onOpenChange={(open) => !open && setEditTarget(null)}
          initial={fromRating(editTarget)}
          title="Edit interview rating"
          busy={update.isPending}
          onSubmit={onUpdate}
        />
      )}
      <ConfirmDialog request={confirm} onClose={() => setConfirm(null)} />
    </div>
  );
}
