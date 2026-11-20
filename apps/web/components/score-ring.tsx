"use client";

import { AlertTriangle, CheckCircle2, CircleHelp, MinusCircle } from "lucide-react";

import { cn } from "@/lib/utils";

type Tone = "empty" | "low" | "mid" | "high";

function toneFor(score: number | null | undefined): Tone {
  if (score === null || score === undefined) return "empty";
  if (score >= 80) return "high";
  if (score >= 60) return "mid";
  return "low";
}

const TONE_STYLES: Record<Tone, { ring: string; text: string; icon: typeof CheckCircle2 }> = {
  empty: {
    ring: "border-muted-foreground/30 text-muted-foreground",
    text: "text-muted-foreground",
    icon: MinusCircle,
  },
  high: {
    ring: "border-success text-success",
    text: "text-success",
    icon: CheckCircle2,
  },
  mid: {
    ring: "border-warning text-warning",
    text: "text-warning",
    icon: AlertTriangle,
  },
  low: {
    ring: "border-destructive text-destructive",
    text: "text-destructive",
    icon: CircleHelp,
  },
};

interface ScoreRingProps {
  score: number | null | undefined;
  size?: "sm" | "md";
  className?: string;
  /** Accessible label; defaults to score or “No score yet”. */
  label?: string;
}

/**
 * Advisory match score indicator (SPEC Part 10). Null scores render a muted placeholder
 * until the CV engine / matcher populate match_results.
 */
export function ScoreRing({ score, size = "sm", className, label }: ScoreRingProps) {
  const tone = toneFor(score);
  const { ring, text, icon: Icon } = TONE_STYLES[tone];
  const dim = size === "md" ? "h-14 w-14 text-sm" : "h-10 w-10 text-xs";
  const accessible =
    label ?? (score === null || score === undefined ? "No score yet" : `Score ${score}`);

  return (
    <span
      role="img"
      aria-label={accessible}
      className={cn(
        "inline-flex flex-col items-center justify-center rounded-full border-2 font-semibold tabular-nums",
        dim,
        ring,
        className,
      )}
    >
      {score === null || score === undefined ? (
        <span className={cn("flex items-center gap-0.5", text)}>
          <Icon className="h-3 w-3" aria-hidden />
          —
        </span>
      ) : (
        <span className={cn("flex items-center gap-0.5", text)}>
          <Icon className="h-3 w-3" aria-hidden />
          {score}
        </span>
      )}
    </span>
  );
}
