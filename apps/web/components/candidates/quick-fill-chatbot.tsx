"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Loader2, MessageSquare, Send, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { applicationKeys } from "@/hooks/use-applications";
import { useAuth } from "@/hooks/use-auth";
import { useJobs } from "@/hooks/use-jobs";
import { useQuickParse } from "@/hooks/use-quick-parse";
import { ApiError, api } from "@/lib/api";
import { isAdmin } from "@/lib/permissions";
import {
  draftFromParse,
  emptyChatDraft,
  formatValidationError,
  missingForCreate,
  toCreateFormData,
  toPatchBody,
  type ChatCandidateDraft,
} from "@/lib/quick-fill-candidate";
import { cn } from "@/lib/utils";
import type { DuplicateMatch } from "@/types/api";

const PLACEHOLDER =
  "e.g. Rahul Sharma, Pune, 5 years, current 8 LPA, rahul@mail.com, +91 98765 43210";
const TAGLINE = "One quick paste, one step closer to your next great hire!";

type Phase = "compose" | "review";

/** Local-time greeting for the Quick Add header. */
export function greetingForLocalHour(hour: number): string {
  if (hour >= 5 && hour < 12) return "Good morning";
  if (hour >= 12 && hour < 17) return "Good afternoon";
  if (hour >= 17 && hour < 21) return "Good evening";
  return "Good night";
}

/** The greeting always addresses the same name, whoever is signed in. */
const GREETING_NAME = "Akanksha";

function greeted(hour: number): string {
  return `${greetingForLocalHour(hour)}, ${GREETING_NAME}`;
}

/**
 * Floating Quick fill chatbot for HR Admin / Super Admin. Paste candidate text → Extract → Add.
 * Add creates a new candidate, or updates an existing one when email/phone already matches.
 * Drag-and-drop on Add candidate is unrelated and stays as it is.
 */
export function QuickFillChatbot() {
  const { user } = useAuth();
  if (!isAdmin(user?.role)) return null;
  return <QuickFillChatbotInner />;
}

function QuickFillChatbotInner() {
  const { user } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const jobs = useJobs({ page_size: 100 });
  const parse = useQuickParse();
  const panelId = useId();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [phase, setPhase] = useState<Phase>("compose");
  const [draft, setDraft] = useState<ChatCandidateDraft>(emptyChatDraft);
  const [match, setMatch] = useState<DuplicateMatch | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const [greeting, setGreeting] = useState(() => greeted(new Date().getHours()));

  useEffect(() => {
    if (open) setGreeting(greeted(new Date().getHours()));
  }, [open]);

  useEffect(() => {
    if (open) {
      window.setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const jobItems = jobs.data?.items ?? [];
  const trimmed = text.trim();

  const reset = () => {
    setText("");
    setPhase("compose");
    setDraft(emptyChatDraft());
    setMatch(null);
    setStatus(null);
  };

  const extract = async () => {
    if (!trimmed || parse.isPending) return;
    setStatus(null);
    try {
      const result = await parse.mutateAsync(trimmed);
      if (result.multiple_candidates) {
        setStatus(
          result.warnings[0] ?? "This looks like several candidates. Paste one person at a time.",
        );
        setPhase("compose");
        return;
      }
      if (!result.fields.some((f) => f.value != null)) {
        setStatus(
          result.warnings[0] ??
            "Nothing was recognised. Try labels such as Name:, Exp:, Current CTC:.",
        );
        setPhase("compose");
        return;
      }
      const next = draftFromParse(result, draft.job_id);
      setDraft(next);
      setPhase("review");
      const found = await api.candidates.duplicates({
        email: next.email || undefined,
        phone: next.phone || undefined,
      });
      const hit =
        found.matches.find((m) => m.matched_on.includes("email")) ??
        found.matches.find((m) => m.matched_on.includes("phone")) ??
        null;
      setMatch(hit);
      setStatus(
        hit
          ? `Matches existing candidate ${hit.first_name} ${hit.last_name}. Add will update their profile.`
          : "Review the details, pick a job, then click Add.",
      );
    } catch (error) {
      setStatus(error instanceof ApiError ? error.message : "Could not extract details");
    }
  };

  const addOrUpdate = async () => {
    const missing = match ? [] : missingForCreate(draft);
    if (!match && missing.length > 0) {
      setStatus(`Add needs: ${missing.join(", ")}.`);
      return;
    }
    if (match && !draft.email.trim() && !draft.phone.trim()) {
      setStatus("Need an email or phone to update the existing candidate.");
      return;
    }
    setBusy(true);
    setStatus(null);
    try {
      if (match) {
        await api.candidates.update(match.id, toPatchBody(draft));
        toast.success(`Updated ${match.first_name} ${match.last_name}`);
      } else {
        const created = await api.candidates.create(toCreateFormData(draft));
        toast.success(
          created.reused ? "Existing candidate updated with this application" : "Candidate added",
        );
      }
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
      setOpen(false);
      reset();
      router.push("/candidates");
    } catch (error) {
      if (error instanceof ApiError) {
        setStatus(formatValidationError(error));
      } else {
        setStatus("Could not save candidate");
      }
    } finally {
      setBusy(false);
    }
  };

  const setField = <K extends keyof ChatCandidateDraft>(key: K, value: ChatCandidateDraft[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        data-testid="quick-fill-fab"
        className={cn(
          "fixed z-40 flex h-12 w-12 items-center justify-center rounded-full sm:h-14 sm:w-14",
          "bottom-[max(1rem,env(safe-area-inset-bottom))] right-[max(1rem,env(safe-area-inset-right))]",
          "bg-primary text-primary-foreground shadow-lg shadow-primary/30",
          "transition hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
        title="Quick Add"
      >
        {open ? (
          <X className="h-5 w-5 sm:h-6 sm:w-6" aria-hidden />
        ) : (
          <MessageSquare className="h-5 w-5 sm:h-6 sm:w-6" aria-hidden />
        )}
        <span className="sr-only">{open ? "Close Quick Add" : "Open Quick Add"}</span>
      </button>

      {open && (
        <div
          id={panelId}
          ref={panelRef}
          role="dialog"
          aria-label="Quick Add"
          data-testid="quick-fill-chatbot"
          className={cn(
            "fixed z-40 flex flex-col overflow-hidden rounded-2xl border border-border/70 bg-card/95 shadow-2xl backdrop-blur-md",
            "left-3 right-3 max-h-[min(85dvh,36rem)]",
            "bottom-[calc(4.5rem+env(safe-area-inset-bottom))]",
            "sm:bottom-24 sm:left-auto sm:right-4 sm:w-[min(100vw-2rem,24rem)]",
          )}
        >
          <header className="flex items-start justify-between gap-2 border-b border-border/60 px-4 py-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold">{greeting}</p>
              <p className="text-xs text-muted-foreground">{TAGLINE}</p>
            </div>
            <Button type="button" variant="ghost" size="icon" onClick={() => setOpen(false)}>
              <X className="h-4 w-4" aria-hidden />
              <span className="sr-only">Close</span>
            </Button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto overscroll-contain p-4">
            {phase === "compose" && (
              <div className="space-y-2">
                <Label htmlFor={`${panelId}-text`} className="sr-only">
                  Candidate details
                </Label>
                <Textarea
                  ref={inputRef}
                  id={`${panelId}-text`}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder={PLACEHOLDER}
                  rows={5}
                  maxLength={2000}
                  spellCheck={false}
                  className="resize-none text-sm"
                />
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground">{text.length}/2000</span>
                  <Button
                    type="button"
                    size="sm"
                    disabled={!trimmed || parse.isPending}
                    onClick={() => void extract()}
                    data-testid="quick-fill-chat-extract"
                  >
                    {parse.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <Send className="h-4 w-4" aria-hidden />
                    )}
                    Extract
                  </Button>
                </div>
              </div>
            )}

            {phase === "review" && (
              <div className="space-y-3">
                <div className="grid grid-cols-1 gap-2 min-[380px]:grid-cols-2">
                  <Field
                    label="First name"
                    value={draft.first_name}
                    onChange={(v) => setField("first_name", v)}
                  />
                  <Field
                    label="Last name"
                    value={draft.last_name}
                    onChange={(v) => setField("last_name", v)}
                  />
                  <Field label="Email" value={draft.email} onChange={(v) => setField("email", v)} />
                  <Field label="Phone" value={draft.phone} onChange={(v) => setField("phone", v)} />
                  <Field
                    label="Location"
                    value={draft.current_location}
                    onChange={(v) => setField("current_location", v)}
                  />
                  <Field
                    label="Company"
                    value={draft.current_company}
                    onChange={(v) => setField("current_company", v)}
                  />
                  <Field
                    label="Title"
                    value={draft.current_title}
                    onChange={(v) => setField("current_title", v)}
                  />
                  <Field
                    label="Experience (years)"
                    value={draft.total_experience_years}
                    onChange={(v) => setField("total_experience_years", v)}
                  />
                  <Field
                    label="Notice (days)"
                    value={draft.notice_period_days}
                    onChange={(v) => setField("notice_period_days", v)}
                  />
                  <Field
                    label="Current CTC"
                    value={draft.current_ctc_amount}
                    onChange={(v) => setField("current_ctc_amount", v)}
                  />
                  <Field
                    label="Expected CTC"
                    value={draft.expected_ctc_amount}
                    onChange={(v) => setField("expected_ctc_amount", v)}
                  />
                </div>

                {!match && (
                  <div className="space-y-1.5">
                    <Label htmlFor={`${panelId}-job`}>Job *</Label>
                    <Select
                      id={`${panelId}-job`}
                      value={draft.job_id}
                      onChange={(e) => setField("job_id", e.target.value)}
                      data-testid="quick-fill-chat-job"
                    >
                      <option value="">Select a job</option>
                      {jobItems.map((j) => (
                        <option key={j.id} value={j.id}>
                          {j.title}
                        </option>
                      ))}
                    </Select>
                  </div>
                )}

                {match && (
                  <p className="rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-xs">
                    Will update{" "}
                    <Link
                      href={`/candidates/${match.id}`}
                      className="font-medium underline underline-offset-2"
                    >
                      {match.first_name} {match.last_name}
                    </Link>{" "}
                    ({match.email}). Other candidates are not changed.
                  </p>
                )}

                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setPhase("compose");
                      setMatch(null);
                    }}
                  >
                    Back
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    disabled={busy}
                    onClick={() => void addOrUpdate()}
                    data-testid="quick-fill-chat-add"
                  >
                    {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
                    {match ? "Update candidate" : "Add"}
                  </Button>
                </div>
              </div>
            )}

            {status && (
              <p
                role="status"
                className="text-xs text-muted-foreground"
                data-testid="quick-fill-chat-status"
              >
                {status}
              </p>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = useId();
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs">
        {label}
      </Label>
      <Input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 text-sm"
      />
    </div>
  );
}
