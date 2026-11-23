"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";

import { ErrorState } from "@/components/error-state";
import { ScoreRing } from "@/components/score-ring";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApplicationFinalScore } from "@/hooks/use-applications";
import { useAuth } from "@/hooks/use-auth";
import { isAdmin } from "@/lib/permissions";

interface FinalScorePanelProps {
  applicationId: string;
}

export function FinalScorePanel({ applicationId }: FinalScorePanelProps) {
  const { user } = useAuth();
  const query = useApplicationFinalScore(applicationId);

  if (query.isPending) {
    return <Skeleton className="h-36 w-full" aria-busy="true" />;
  }

  if (query.isError) {
    return (
      <ErrorState
        error={query.error}
        title="Could not load advisory final score"
        onRetry={() => void query.refetch()}
      />
    );
  }

  const data = query.data;
  const { weights } = data;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Advisory final score</CardTitle>
        <CardDescription>
          Weighted from match ({weights.match_weight}%) and interview average (
          {weights.interview_weight}
          %). ATS is shown separately and is not blended here. {data.note}
          {isAdmin(user?.role) && (
            <>
              {" "}
              Adjust weights in{" "}
              <Link
                href="/settings/scoring"
                className="text-primary underline-offset-4 hover:underline"
              >
                Settings → Scoring
              </Link>
              .
            </>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-6">
        <ScoreRing score={data.final_score ?? null} size={72} />
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">Match input</dt>
            <dd className="font-mono tabular-nums">{data.match_score ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Interview avg input</dt>
            <dd className="font-mono tabular-nums">
              {data.interview_avg !== null ? `${data.interview_avg} / 5` : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Weights</dt>
            <dd>
              {weights.match_weight}% / {weights.interview_weight}%
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Computed final</dt>
            <dd className="font-mono tabular-nums">
              {data.final_score !== null ? data.final_score : "—"}
              {query.isFetching && (
                <Loader2
                  className="ml-1 inline h-3 w-3 animate-spin text-muted-foreground"
                  aria-hidden
                />
              )}
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
