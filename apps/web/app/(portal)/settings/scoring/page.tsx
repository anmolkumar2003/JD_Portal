"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/components/error-state";
import { AdminOnly } from "@/components/settings/admin-only";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import type { ScoringWeights } from "@/types/api";

const WEIGHTS_KEY = ["org", "scoring-weights"] as const;

function ScoringForm({ initial }: { initial: ScoringWeights }) {
  const queryClient = useQueryClient();
  const [match, setMatch] = useState(String(initial.match_weight));
  const [interview, setInterview] = useState(String(initial.interview_weight));

  useEffect(() => {
    setMatch(String(initial.match_weight));
    setInterview(String(initial.interview_weight));
  }, [initial.match_weight, initial.interview_weight]);

  const save = useMutation({
    mutationFn: () =>
      api.org.updateScoringWeights({
        match_weight: Number(match),
        interview_weight: Number(interview),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(WEIGHTS_KEY, data);
      toast.success("Scoring weights saved");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not save"),
  });

  const sum = (Number(match) || 0) + (Number(interview) || 0);
  const valid = sum === 100 && Number(match) >= 0 && Number(interview) >= 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Advisory final score weights</CardTitle>
        <CardDescription>
          Match and interview averages are combined for the profile final score panel only. Weights
          must total 100%. Defaults are 50% / 50%.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="grid max-w-md gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (valid) save.mutate();
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="match_weight">Match weight (%)</Label>
            <Input
              id="match_weight"
              type="number"
              min={0}
              max={100}
              value={match}
              onChange={(e) => setMatch(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="interview_weight">Interview weight (%)</Label>
            <Input
              id="interview_weight"
              type="number"
              min={0}
              max={100}
              value={interview}
              onChange={(e) => setInterview(e.target.value)}
            />
          </div>
          {!valid && (
            <p className="text-sm text-destructive" role="alert">
              Weights must sum to 100 (currently {sum}).
            </p>
          )}
          <Button type="submit" disabled={!valid || save.isPending}>
            {save.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
            Save weights
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function ScoringSettings() {
  const weights = useQuery({ queryKey: WEIGHTS_KEY, queryFn: api.org.scoringWeights });
  if (weights.isPending) return <Skeleton className="h-64 w-full max-w-lg" />;
  if (weights.isError) {
    return <ErrorState error={weights.error} onRetry={() => void weights.refetch()} />;
  }
  return <ScoringForm initial={weights.data} />;
}

export default function ScoringSettingsPage() {
  return (
    <AdminOnly>
      <ScoringSettings />
    </AdminOnly>
  );
}
