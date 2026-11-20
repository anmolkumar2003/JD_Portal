"use client";

import { ErrorState } from "@/components/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/labels";
import type { TimelineEvent } from "@/types/api";

function describeEvent(event: TimelineEvent): string {
  if (event.action === "application.created") {
    return "Application submitted";
  }
  if (event.action === "application.stage_changed") {
    const from = typeof event.meta.from_stage === "string" ? event.meta.from_stage : "?";
    const to = typeof event.meta.to_stage === "string" ? event.meta.to_stage : "?";
    const reason =
      typeof event.meta.rejection_reason === "string" ? ` — ${event.meta.rejection_reason}` : "";
    return `Moved from ${from} to ${to}${reason}`;
  }
  return event.action.replaceAll(".", " ");
}

interface TimelineProps {
  events: TimelineEvent[] | undefined;
  isLoading: boolean;
  error: unknown;
  onRetry?: () => void;
}

export function Timeline({ events, isLoading, error, onRetry }: TimelineProps) {
  if (error && !events) {
    return <ErrorState error={error} title="Could not load timeline" onRetry={onRetry} />;
  }
  if (isLoading && !events) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading timeline">
        {Array.from({ length: 3 }, (_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }
  if (!events || events.length === 0) {
    return <p className="text-sm text-muted-foreground">No activity yet.</p>;
  }

  return (
    <ol className="relative space-y-4 border-l border-border pl-6">
      {events.map((event) => (
        <li key={event.id} className="relative">
          <span
            className="absolute -left-[1.625rem] top-1.5 h-2.5 w-2.5 rounded-full bg-primary"
            aria-hidden
          />
          <p className="text-sm font-medium">{describeEvent(event)}</p>
          <p className="text-xs text-muted-foreground">
            {formatDateTime(event.occurred_at)}
            {event.actor ? ` · ${event.actor.full_name}` : ""}
          </p>
        </li>
      ))}
    </ol>
  );
}
