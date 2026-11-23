"use client";

import { useQueries } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { ScoreRing } from "@/components/score-ring";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

function CompareContent() {
  const params = useSearchParams();
  const ids = (params.get("ids") ?? "")
    .split(",")
    .map((id) => id.trim())
    .filter(Boolean)
    .slice(0, 4);

  const queries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["applications", "detail", id],
      queryFn: () => api.applications.get(id),
      enabled: ids.length >= 2,
    })),
  });

  if (ids.length < 2) {
    return (
      <p className="text-sm text-muted-foreground">
        Select 2–4 candidates from the list (add <code>?ids=id1,id2</code> to the URL).
      </p>
    );
  }

  if (queries.some((q) => q.isPending)) {
    return <Skeleton className="h-64 w-full" />;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="p-3 font-medium text-muted-foreground">Field</th>
            {queries.map((q) => (
              <th key={q.data?.id} className="p-3 font-semibold">
                {q.data ? `${q.data.candidate.first_name} ${q.data.candidate.last_name}` : "—"}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr className="border-b">
            <td className="p-3 text-muted-foreground">Score</td>
            {queries.map((q) => (
              <td key={`score-${q.data?.id}`} className="p-3">
                <ScoreRing score={q.data?.match_result?.overall_score ?? null} />
              </td>
            ))}
          </tr>
          <tr className="border-b">
            <td className="p-3 text-muted-foreground">Title</td>
            {queries.map((q) => (
              <td key={`title-${q.data?.id}`} className="p-3">
                {q.data?.candidate.current_title ?? "—"}
              </td>
            ))}
          </tr>
          <tr className="border-b">
            <td className="p-3 text-muted-foreground">Experience</td>
            {queries.map((q) => (
              <td key={`exp-${q.data?.id}`} className="p-3">
                {q.data?.candidate.total_experience_years ?? "—"} yrs
              </td>
            ))}
          </tr>
          <tr className="border-b">
            <td className="p-3 text-muted-foreground">Matched skills</td>
            {queries.map((q) => (
              <td key={`skills-${q.data?.id}`} className="p-3">
                {(q.data?.match_result?.matched_skills ?? []).join(", ") || "—"}
              </td>
            ))}
          </tr>
          <tr>
            <td className="p-3 text-muted-foreground">Missing required</td>
            {queries.map((q) => (
              <td key={`miss-${q.data?.id}`} className="p-3 text-destructive">
                {(q.data?.match_result?.missing_required ?? []).join(", ") || "—"}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export default function ComparePage() {
  return (
    <div className="space-y-6">
      <div>
        <Breadcrumbs
          items={[
            { label: "Candidates", href: "/candidates" },
            { label: "Compare" },
          ]}
        />
        <h1 className="text-2xl font-semibold tracking-tight">Compare candidates</h1>
        <p className="text-sm text-muted-foreground">Side-by-side view for 2–4 applications (CAND-07).</p>
      </div>
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <CompareContent />
      </Suspense>
    </div>
  );
}
