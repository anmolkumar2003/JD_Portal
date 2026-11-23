"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Loader2, RefreshCw, XCircle } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { ScoreRing } from "@/components/score-ring";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
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

  const [editJson, setEditJson] = useState<string | null>(null);

  const reprocess = useMutation({
    mutationFn: (documentId: string) => api.documents.reprocess(documentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["applications", "analysis", applicationId] });
    },
  });

  const correct = useMutation({
    mutationFn: async () => {
      const profile = analysis.data?.parsed_profile;
      if (!profile?.id || editJson === null) throw new Error("Nothing to save");
      const data = JSON.parse(editJson) as Record<string, unknown>;
      return api.parsedProfiles.patch(profile.id, { data });
    },
    onSuccess: () => {
      setEditJson(null);
      void queryClient.invalidateQueries({ queryKey: ["applications", "analysis", applicationId] });
      void queryClient.invalidateQueries({ queryKey: ["applications", "detail", applicationId] });
    },
  });

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
          <CardHeader>
            <CardTitle className="text-base">Correct parsed data</CardTitle>
            <CardDescription>
              Edit the JSON overlay. Saving recalculates the advisory match score (CV-08).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
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
            <div className="flex gap-2">
              <Button onClick={() => correct.mutate()} disabled={correct.isPending || !editJson}>
                Save corrections &amp; re-score
              </Button>
              <Button variant="outline" onClick={() => setEditJson(null)}>
                Reset
              </Button>
            </div>
            {correct.isError && (
              <p className="text-sm text-destructive">
                Could not save corrections. Check JSON syntax.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
