"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Loader2, RefreshCw, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { ScoreMetric } from "@/components/candidates/score-metric";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { ScoreRing } from "@/components/score-ring";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useApplicationFinalScore } from "@/hooks/use-applications";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

function Chip({
  label,
  tone,
}: {
  label: string;
  tone: "matched" | "missing" | "preferred" | "extra";
}) {
  const tones = {
    matched: "border-success/40 bg-success/10 text-success",
    missing: "border-destructive/40 bg-destructive/10 text-destructive",
    preferred: "border-warning/40 bg-warning/10 text-warning",
    extra: "border-border bg-muted text-muted-foreground",
  };
  return (
    <li className={cn("rounded-full border px-2.5 py-1 text-xs font-medium", tones[tone])}>
      {label}
    </li>
  );
}

function ComponentBar({ label, value }: { label: string; value: number }) {
  const tone = value >= 80 ? "bg-success" : value >= 60 ? "bg-warning" : "bg-destructive";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="capitalize text-muted-foreground">{label}</span>
        <span className="font-mono tabular-nums">{value}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full transition-all", tone)}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

interface MatchAnalysisProps {
  applicationId: string;
}

export function MatchAnalysis({ applicationId }: MatchAnalysisProps) {
  const queryClient = useQueryClient();
  const analysis = useQuery({
    queryKey: ["applications", "analysis", applicationId],
    queryFn: () => api.applications.analysis(applicationId),
  });
  const finalScore = useApplicationFinalScore(applicationId);

  const [editJson, setEditJson] = useState<string | null>(null);
  const [useJsonEditor, setUseJsonEditor] = useState(false);
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formPhone, setFormPhone] = useState("");
  const [formSkills, setFormSkills] = useState("");
  const [formYears, setFormYears] = useState("");

  const reprocess = useMutation({
    mutationFn: (documentId: string) => api.documents.reprocess(documentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["applications", "analysis", applicationId] });
    },
  });

  const loadFormFromProfile = (data: Record<string, unknown>) => {
    const name =
      typeof data.full_name === "string"
        ? data.full_name
        : [data.first_name, data.last_name].filter(Boolean).join(" ");
    setFormName(name);
    setFormEmail(String(data.email ?? ""));
    setFormPhone(String(data.phone ?? ""));
    const skills = data.skills;
    if (Array.isArray(skills)) {
      setFormSkills(
        skills
          .map((s) => (typeof s === "string" ? s : (s as { name?: string })?.name))
          .filter(Boolean)
          .join(", "),
      );
    } else setFormSkills("");
    setFormYears(data.total_experience_years != null ? String(data.total_experience_years) : "");
  };

  const correct = useMutation({
    mutationFn: async () => {
      const profile = analysis.data?.parsed_profile;
      if (!profile?.id) throw new Error("Nothing to save");
      let data: Record<string, unknown>;
      let total_experience_years: number | null | undefined;
      if (useJsonEditor) {
        if (editJson === null) throw new Error("Nothing to save");
        data = JSON.parse(editJson) as Record<string, unknown>;
      } else {
        const base = { ...(profile.corrected_data ?? profile.data ?? {}) } as Record<
          string,
          unknown
        >;
        if (formName.includes(" ")) {
          const [first, ...rest] = formName.trim().split(/\s+/);
          base.first_name = first;
          base.last_name = rest.join(" ");
          base.full_name = formName.trim();
        } else if (formName) {
          base.full_name = formName.trim();
        }
        if (formEmail.trim()) base.email = formEmail.trim();
        if (formPhone.trim()) base.phone = formPhone.trim();
        base.skills = formSkills
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        total_experience_years = formYears.trim() ? Number(formYears) : null;
        data = base;
      }
      return api.parsedProfiles.patch(profile.id, { data, total_experience_years });
    },
    onSuccess: () => {
      setEditJson(null);
      void queryClient.invalidateQueries({ queryKey: ["applications", "analysis", applicationId] });
      void queryClient.invalidateQueries({ queryKey: ["applications", "detail", applicationId] });
    },
  });

  const profilePayload = analysis.data?.parsed_profile;

  useEffect(() => {
    if (profilePayload && !useJsonEditor) {
      loadFormFromProfile(
        (profilePayload.corrected_data ?? profilePayload.data ?? {}) as Record<string, unknown>,
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset form when profile payload changes
  }, [profilePayload?.id, profilePayload?.corrected_data, useJsonEditor]);

  if (analysis.isPending) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-56 w-full" />
      </div>
    );
  }

  if (analysis.isError) {
    return (
      <ErrorState
        error={analysis.error}
        title="Could not load match analysis"
        onRetry={() => void analysis.refetch()}
      />
    );
  }

  const data = analysis.data;
  const status = data.parsed_profile?.parse_status;

  if (status === "pending" || status === "processing") {
    return (
      <EmptyState
        icon={Loader2}
        title={status === "pending" ? "CV queued for analysis" : "Analyzing CV…"}
        description="Scores are advisory. This usually finishes within a minute."
        action={
          data.document_id ? (
            <Button
              variant="outline"
              onClick={() => reprocess.mutate(data.document_id!)}
              disabled={reprocess.isPending}
            >
              <RefreshCw className="h-4 w-4" aria-hidden />
              Refresh status
            </Button>
          ) : undefined
        }
      />
    );
  }

  if (status === "failed") {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="CV analysis failed"
        description={data.parsed_profile?.error ?? "Something went wrong while parsing the CV."}
        action={
          data.document_id ? (
            <Button
              onClick={() => reprocess.mutate(data.document_id!)}
              disabled={reprocess.isPending}
            >
              <RefreshCw className="h-4 w-4" aria-hidden />
              Retry
            </Button>
          ) : undefined
        }
      />
    );
  }

  const match = data.match_result;
  const ats = data.ats_check;
  const fs = finalScore.data;
  const interviewLabel =
    fs?.interview_avg != null ? `${Number(fs.interview_avg).toFixed(1)} / 5` : "—";
  const explanation = (match?.explanation ?? {}) as {
    summary?: string;
    strengths?: string[];
    concerns?: string[];
    component_scores?: Record<string, number>;
    score_version?: string;
  };
  const components = explanation.component_scores ?? {};

  return (
    <div className="space-y-6">
      <p className="rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground">
        {data.disclaimer} Score version:{" "}
        <span className="font-mono">
          {explanation.score_version ?? match?.engine_version ?? "—"}
        </span>
      </p>

      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        <ScoreMetric
          label="CV match"
          percentScore={match?.overall_score ?? fs?.match_score ?? null}
        />
        <ScoreMetric label="ATS" percentScore={ats?.score ?? fs?.ats_score ?? null} />
        <ScoreMetric label="Interview avg" scaleValue={interviewLabel} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[auto_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Overall match</CardTitle>
            <CardDescription>Advisory JD match score</CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center pb-6">
            <ScoreRing score={match?.overall_score ?? null} size={96} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Component scores</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.keys(components).length === 0 && (
              <p className="text-sm text-muted-foreground">No component breakdown yet.</p>
            )}
            {Object.entries(components).map(([key, value]) => (
              <ComponentBar key={key} label={key} value={Number(value)} />
            ))}
          </CardContent>
        </Card>
      </div>

      {explanation.summary && (
        <p className="text-sm leading-relaxed text-foreground">{explanation.summary}</p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Strengths</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {(explanation.strengths ?? []).map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Concerns</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {(explanation.concerns ?? []).map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Skills</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Matched
            </p>
            <ul className="flex flex-wrap gap-2">
              {(match?.matched_skills ?? []).map((s) => (
                <Chip key={s} label={s} tone="matched" />
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Missing required
            </p>
            <ul className="flex flex-wrap gap-2">
              {(match?.missing_required ?? []).map((s) => (
                <Chip key={s} label={s} tone="missing" />
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Missing preferred
            </p>
            <ul className="flex flex-wrap gap-2">
              {(match?.missing_preferred ?? []).map((s) => (
                <Chip key={s} label={s} tone="preferred" />
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Extra
            </p>
            <ul className="flex flex-wrap gap-2">
              {(match?.extra_skills ?? []).map((s) => (
                <Chip key={s} label={s} tone="extra" />
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base">ATS-friendliness</CardTitle>
            <CardDescription>
              Score {ats?.score ?? "—"} · {ats?.band ?? "n/a"} · {ats?.engine_version}
            </CardDescription>
          </div>
          <ScoreRing score={ats?.score ?? null} />
        </CardHeader>
        <CardContent>
          <ul className="space-y-3">
            {(ats?.checks ?? []).map((check) => (
              <li key={check.id} className="flex gap-3 text-sm">
                {check.passed ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden />
                ) : (
                  <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden />
                )}
                <div>
                  <p className="font-medium">
                    {check.id}: {check.label}
                  </p>
                  <p className="text-muted-foreground">{check.detail}</p>
                  {!check.passed && (
                    <p className="text-xs text-warning">Suggestion: {check.suggestion}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {data.parsed_profile && (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-2">
            <div>
              <CardTitle className="text-base">Correct parsed data</CardTitle>
              <CardDescription>
                Fix extracted fields or edit raw JSON. Saving recalculates the advisory match score.
              </CardDescription>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                const next = !useJsonEditor;
                setUseJsonEditor(next);
                if (!next) {
                  loadFormFromProfile(
                    (data.parsed_profile?.corrected_data ??
                      data.parsed_profile?.data ??
                      {}) as Record<string, unknown>,
                  );
                }
              }}
            >
              {useJsonEditor ? "Simple form" : "Raw JSON"}
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {useJsonEditor ? (
              <Textarea
                className="min-h-48 font-mono text-xs"
                value={
                  editJson ??
                  JSON.stringify(
                    data.parsed_profile.corrected_data ?? data.parsed_profile.data ?? {},
                    null,
                    2,
                  )
                }
                onChange={(e) => setEditJson(e.target.value)}
                aria-label="Parsed profile JSON"
              />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="parsed-name">Name</Label>
                  <Input
                    id="parsed-name"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="parsed-email">Email</Label>
                  <Input
                    id="parsed-email"
                    type="email"
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="parsed-phone">Phone</Label>
                  <Input
                    id="parsed-phone"
                    value={formPhone}
                    onChange={(e) => setFormPhone(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="parsed-years">Experience (years)</Label>
                  <Input
                    id="parsed-years"
                    type="number"
                    min={0}
                    step={0.5}
                    value={formYears}
                    onChange={(e) => setFormYears(e.target.value)}
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="parsed-skills">Skills (comma-separated)</Label>
                  <Textarea
                    id="parsed-skills"
                    value={formSkills}
                    onChange={(e) => setFormSkills(e.target.value)}
                    rows={2}
                  />
                </div>
              </div>
            )}
            <div className="flex gap-2">
              <Button
                onClick={() => correct.mutate()}
                disabled={correct.isPending || (useJsonEditor && !editJson)}
              >
                Save corrections &amp; re-score
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setEditJson(null);
                  loadFormFromProfile(
                    (data.parsed_profile?.corrected_data ??
                      data.parsed_profile?.data ??
                      {}) as Record<string, unknown>,
                  );
                }}
              >
                Reset
              </Button>
            </div>
            {correct.isError && (
              <p className="text-sm text-destructive">
                Could not save corrections. Check field values or JSON syntax.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
