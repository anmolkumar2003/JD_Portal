"use client";

import { History } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useCandidateTimeline } from "@/hooks/use-applications";
import { formatDateTime } from "@/lib/labels";

function describe(action: string, meta: Record<string, unknown>): string {
  if (action === "application.created") {
    return "Applied via careers site";
  }
  if (action === "application.stage_changed") {
    const from = typeof meta.from_stage_name === "string" ? meta.from_stage_name : "previous stage";
    const to = typeof meta.to_stage_name === "string" ? meta.to_stage_name : "new stage";
    const reason = typeof meta.reason === "string" ? ` — ${meta.reason}` : "";
    return `Moved from ${from} to ${to}${reason}`;
  }
  return action.replaceAll(".", " ");
}

interface ActivityTimelineProps {
  candidateId: string;
}

export function ActivityTimeline({ candidateId }: ActivityTimelineProps) {
  const timeline = useCandidateTimeline(candidateId);

  if (timeline.isPending) {
    return (
      <div className="space-y-3" aria-busy="true">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (timeline.isError) {
    return (
      <ErrorState
        error={timeline.error}
        title="Could not load timeline"
        onRetry={() => void timeline.refetch()}
      />
    );
  }

  const entries = timeline.data ?? [];
  if (entries.length === 0) {
    return (
      <EmptyState
        icon={History}
        title="No activity yet"
        description="Stage changes and applications will appear here."
      />
    );
  }

  return (
    <ol className="relative space-y-0 border-l border-border pl-6">
      {entries.map((entry) => (
        <li key={entry.id} className="relative pb-6 last:pb-0">
          <span
            className="absolute -left-[1.625rem] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-background bg-primary"
            aria-hidden
          />
          <p className="text-sm font-medium">{describe(entry.action, entry.meta)}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {formatDateTime(entry.occurred_at)}
            {entry.actor_name ? ` · ${entry.actor_name}` : ""}
          </p>
        </li>
      ))}
    </ol>
  );
}
