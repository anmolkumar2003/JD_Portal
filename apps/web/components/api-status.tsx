"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, RefreshCw, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, API_URL } from "@/lib/api";
import type { ComponentStatus, HealthResponse } from "@/types/api";

const COMPONENT_LABELS: Record<keyof HealthResponse["checks"], string> = {
  api: "API",
  database: "Database",
  redis: "Redis",
};

function ComponentRow({ label, check }: { label: string; check: ComponentStatus }) {
  const ok = check.status === "ok";
  return (
    <li className="flex items-center justify-between py-2 text-sm">
      <span className="flex items-center gap-2">
        {ok ? (
          <CheckCircle2 className="h-4 w-4 text-success" aria-hidden />
        ) : (
          <XCircle className="h-4 w-4 text-destructive" aria-hidden />
        )}
        {label}
      </span>
      <span className="font-mono text-xs text-muted-foreground">
        {ok ? (check.latency_ms !== null ? `${check.latency_ms} ms` : "up") : "down"}
      </span>
    </li>
  );
}

export function ApiStatus() {
  const { data, error, isPending, isFetching, refetch } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 15_000,
  });

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div className="space-y-1.5">
          <CardTitle>Backend status</CardTitle>
          <CardDescription className="font-mono">{API_URL}/health</CardDescription>
        </div>
        <Button
          variant="outline"
          size="icon"
          onClick={() => void refetch()}
          disabled={isFetching}
          aria-label="Re-check API health"
        >
          <RefreshCw className={isFetching ? "animate-spin" : undefined} />
        </Button>
      </CardHeader>
      <CardContent aria-live="polite">
        {isPending ? (
          <div className="space-y-3" aria-label="Checking API">
            <div className="h-6 w-32 animate-pulse rounded-full bg-muted" />
            <div className="h-24 animate-pulse rounded-md bg-muted" />
          </div>
        ) : error ? (
          <Badge variant="destructive">
            <XCircle className="h-3.5 w-3.5" aria-hidden />
            API unreachable
          </Badge>
        ) : (
          <div className="space-y-4">
            {data.status === "ok" ? (
              <Badge variant="success">
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                API connected
              </Badge>
            ) : (
              <Badge variant="warning">
                <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                API degraded
              </Badge>
            )}
            <ul className="divide-y rounded-md border px-4">
              {(Object.keys(COMPONENT_LABELS) as (keyof HealthResponse["checks"])[]).map((key) => (
                <ComponentRow key={key} label={COMPONENT_LABELS[key]} check={data.checks[key]} />
              ))}
            </ul>
            <p className="text-xs text-muted-foreground">Version {data.version}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
