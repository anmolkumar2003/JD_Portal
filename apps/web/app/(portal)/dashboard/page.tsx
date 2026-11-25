"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Briefcase,
  CalendarDays,
  Download,
  Loader2,
  Sparkles,
  TrendingUp,
  UserCheck,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { toast } from "sonner";

import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { ROLE_LABELS } from "@/lib/labels";
import { cn } from "@/lib/utils";

const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(var(--chart-6))",
];

function toIsoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function daysBetweenInclusive(start: string, end: string): number {
  const a = new Date(`${start}T00:00:00Z`).getTime();
  const b = new Date(`${end}T00:00:00Z`).getTime();
  const diff = Math.ceil((b - a) / 86_400_000) + 1;
  return Math.min(365, Math.max(7, diff));
}

function StatCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: number | string;
  icon: LucideIcon;
  accent?: "primary" | "violet" | "cyan" | "success" | "warning";
}) {
  const accentClass =
    accent === "violet"
      ? "text-violet"
      : accent === "cyan"
        ? "text-cyan"
        : accent === "success"
          ? "text-success"
          : accent === "warning"
            ? "text-warning"
            : "text-primary";

  return (
    <Card surface="glass" className="group overflow-hidden">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="space-y-1.5">
          <CardDescription className="text-xs font-medium uppercase tracking-wider">
            {label}
          </CardDescription>
          <CardTitle className="text-2xl tabular-nums tracking-tight sm:text-3xl">{value}</CardTitle>
        </div>
        <div className={cn("kpi-icon transition-transform duration-250 group-hover:scale-105", accentClass)}>
          <Icon className="h-5 w-5" aria-hidden />
        </div>
      </CardHeader>
      <div
        className="h-1 w-full opacity-80"
        style={{
          background:
            accent === "violet"
              ? "linear-gradient(90deg, hsl(var(--violet) / 0.5), transparent)"
              : accent === "cyan"
                ? "linear-gradient(90deg, hsl(var(--cyan) / 0.5), transparent)"
                : accent === "success"
                  ? "linear-gradient(90deg, hsl(var(--success) / 0.5), transparent)"
                  : accent === "warning"
                    ? "linear-gradient(90deg, hsl(var(--warning) / 0.5), transparent)"
                    : "linear-gradient(90deg, hsl(var(--primary) / 0.5), transparent)",
        }}
      />
    </Card>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value: number; name?: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-strong rounded-lg px-3 py-2 text-sm text-popover-foreground">
      {label && <p className="mb-1 text-muted-foreground">{label}</p>}
      <p className="font-medium tabular-nums">{payload[0]?.value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const today = useMemo(() => new Date(), []);
  const defaultEnd = toIsoDate(today);
  const defaultStart = toIsoDate(new Date(today.getTime() - 29 * 86_400_000));

  const [start, setStart] = useState(defaultStart);
  const [end, setEnd] = useState(defaultEnd);
  const [exporting, setExporting] = useState(false);

  const trendDays = useMemo(() => daysBetweenInclusive(start, end), [start, end]);

  const rangeKey = { start, end };
  const overview = useQuery({
    queryKey: ["analytics", "overview", rangeKey],
    queryFn: () => api.analytics.overview(rangeKey),
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
    queryKey: ["analytics", "over-time", trendDays],
    queryFn: () => api.analytics.overTime(trendDays),
  });

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await api.analytics.exportCsv();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "analytics.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

  if (!user) return null;

  const kpi = overview.data ?? {};
  const sourceRows = (sources.data ?? []).map((row) => ({
    ...row,
    label: row.source.replaceAll("_", " "),
  }));

  return (
    <div className="space-y-6">
      <div className="glass relative overflow-hidden rounded-[var(--radius)] p-6 sm:p-8">
        <div className="pointer-events-none absolute -right-8 -top-8 h-40 w-40 rounded-full bg-cyan/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-10 left-1/3 h-32 w-32 rounded-full bg-primary/15 blur-3xl" />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-2">
            <Breadcrumbs items={[{ label: "Dashboard" }]} />
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" aria-hidden />
              <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">Dashboard</h1>
            </div>
            <p className="max-w-xl text-sm text-muted-foreground">
              Welcome back, {user.full_name}. Here&apos;s your recruitment pulse ·{" "}
              {ROLE_LABELS[user.role]}
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="shrink-0 self-start"
            disabled={exporting}
            onClick={() => void handleExport()}
          >
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Download className="h-4 w-4" aria-hidden />
            )}
            Export CSV
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Date range</CardTitle>
          <CardDescription>Filters overview metrics (API start / end).</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="grid w-full gap-2 sm:max-w-[11rem]">
            <Label htmlFor="dash-start">Start</Label>
            <Input
              id="dash-start"
              type="date"
              value={start}
              max={end}
              onChange={(e) => setStart(e.target.value)}
            />
          </div>
          <div className="grid w-full gap-2 sm:max-w-[11rem]">
            <Label htmlFor="dash-end">End</Label>
            <Input
              id="dash-end"
              type="date"
              value={end}
              min={start}
              max={defaultEnd}
              onChange={(e) => setEnd(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {overview.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            label="Open jobs"
            value={Number(kpi.open_jobs ?? 0)}
            icon={Briefcase}
            accent="primary"
          />
          <StatCard
            label="Total applicants"
            value={Number(kpi.total_applicants ?? 0)}
            icon={Users}
            accent="violet"
          />
          <StatCard
            label="New this week"
            value={Number(kpi.new_this_week ?? 0)}
            icon={TrendingUp}
            accent="cyan"
          />
          <StatCard
            label="Interviews today"
            value={Number(kpi.interviews_today ?? 0)}
            icon={CalendarDays}
            accent="warning"
          />
          <StatCard
            label="Offers pending"
            value={Number(kpi.offers_pending ?? 0)}
            icon={Sparkles}
            accent="violet"
          />
          <StatCard
            label="Hires this month"
            value={Number(kpi.hires_this_month ?? 0)}
            icon={UserCheck}
            accent="success"
          />
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Hiring funnel</CardTitle>
            <CardDescription>Candidates by pipeline stage</CardDescription>
          </CardHeader>
          <CardContent className="h-[280px] sm:h-[320px]">
            {funnel.isPending ? (
              <Skeleton className="h-full w-full" />
            ) : !funnel.data?.length ? (
              <p className="text-sm text-muted-foreground">No funnel data yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={funnel.data}
                  layout="vertical"
                  margin={{ top: 4, right: 8, left: 8, bottom: 4 }}
                >
                  <defs>
                    <linearGradient id="funnelBar" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="hsl(var(--primary))" />
                      <stop offset="100%" stopColor="hsl(var(--violet))" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    className="stroke-border"
                    horizontal={false}
                  />
                  <XAxis
                    type="number"
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                  />
                  <YAxis
                    type="category"
                    dataKey="stage"
                    width={100}
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                  />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar
                    dataKey="count"
                    fill="url(#funnelBar)"
                    radius={[0, 6, 6, 0]}
                    maxBarSize={28}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Source breakdown</CardTitle>
            <CardDescription>Where candidates come from</CardDescription>
          </CardHeader>
          <CardContent className="h-[280px] sm:h-[320px]">
            {sources.isPending ? (
              <Skeleton className="h-full w-full" />
            ) : !sourceRows.length ? (
              <p className="text-sm text-muted-foreground">No source data yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sourceRows}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    innerRadius={56}
                    outerRadius={92}
                    paddingAngle={3}
                    label={(props) => {
                      const name = String(props.name ?? "");
                      const pct = props.percent ?? 0;
                      return pct >= 0.08 ? `${name} (${Math.round(pct * 100)}%)` : "";
                    }}
                    labelLine={false}
                  >
                    {sourceRows.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Applications over time</CardTitle>
          <CardDescription>Last {trendDays} days (from selected range).</CardDescription>
        </CardHeader>
        <CardContent className="h-[240px] sm:h-[280px]">
          {trend.isPending ? (
            <Skeleton className="h-full w-full" />
          ) : !trend.data?.length ? (
            <p className="text-sm text-muted-foreground">No applications in this window.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend.data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                  width={32}
                />
                <Tooltip content={<ChartTooltip />} labelFormatter={(v) => String(v)} />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2.5}
                  fill="url(#trendFill)"
                  dot={{ r: 3, fill: "hsl(var(--primary))", strokeWidth: 0 }}
                  activeDot={{ r: 5, strokeWidth: 0 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
