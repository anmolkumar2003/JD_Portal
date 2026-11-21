"use client";

import { useQuery } from "@tanstack/react-query";

import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { ROLE_LABELS } from "@/lib/labels";

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-3xl tabular-nums">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const overview = useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: () => api.analytics.overview(),
  });
  const funnel = useQuery({
    queryKey: ["analytics", "funnel"],
    queryFn: () => api.analytics.funnel(),
  });
  const sources = useQuery({
    queryKey: ["analytics", "sources"],
    queryFn: () => api.analytics.sources(),
  });
  const trend = useQuery({
    queryKey: ["analytics", "over-time"],
    queryFn: () => api.analytics.overTime(30),
  });

  if (!user) return null;

  const kpi = overview.data ?? {};

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Breadcrumbs items={[{ label: "Dashboard" }]} />
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Welcome, {user.full_name} · {ROLE_LABELS[user.role]}
        </p>
      </div>

      {overview.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard label="Open jobs" value={Number(kpi.open_jobs ?? 0)} />
          <StatCard label="Total applicants" value={Number(kpi.total_applicants ?? 0)} />
          <StatCard label="New this week" value={Number(kpi.new_this_week ?? 0)} />
          <StatCard label="Interviews today" value={Number(kpi.interviews_today ?? 0)} />
          <StatCard label="Offers pending" value={Number(kpi.offers_pending ?? 0)} />
          <StatCard label="Hires this month" value={Number(kpi.hires_this_month ?? 0)} />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Funnel by stage</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {(funnel.data ?? []).map((row) => (
                <li key={row.stage} className="flex justify-between gap-4">
                  <span>{row.stage}</span>
                  <span className="font-mono tabular-nums">{row.count}</span>
                </li>
              ))}
              {!funnel.data?.length && (
                <li className="text-muted-foreground">No funnel data yet.</li>
              )}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Source breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {(sources.data ?? []).map((row) => (
                <li key={row.source} className="flex justify-between gap-4">
                  <span className="capitalize">{row.source.replaceAll("_", " ")}</span>
                  <span className="font-mono tabular-nums">{row.count}</span>
                </li>
              ))}
              {!sources.data?.length && (
                <li className="text-muted-foreground">No source data yet.</li>
              )}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Applications over time (30 days)</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="grid gap-1 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {(trend.data ?? []).map((row) => (
              <li key={row.date} className="flex justify-between gap-2 rounded border px-2 py-1">
                <span className="text-muted-foreground">{row.date}</span>
                <span className="font-mono tabular-nums">{row.count}</span>
              </li>
            ))}
            {!trend.data?.length && (
              <li className="text-muted-foreground">No applications in this window.</li>
            )}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
