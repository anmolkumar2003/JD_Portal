import { CircleHelp } from "lucide-react";

import { cn } from "@/lib/utils";

function scoreTone(score: number): string {
  if (score >= 80) return "text-success";
  if (score >= 60) return "text-warning";
  return "text-destructive";
}

interface ScoreRingProps {
  score: number | null | undefined;
  size?: number;
  className?: string;
}

/** Compact match score with color threshold (≥80 green, 60–79 amber, &lt;60 red). */
export function ScoreRing({ score, size = 36, className }: ScoreRingProps) {
  if (score === null || score === undefined) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-full border border-dashed px-2 py-0.5 text-xs text-muted-foreground",
          className,
        )}
        title="Score not available yet"
      >
        <CircleHelp className="h-3.5 w-3.5" aria-hidden />—
      </span>
    );
  }

  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const radius = (size - 4) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const tone = scoreTone(clamped);

  return (
    <span
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: size, height: size }}
      title={`Match score ${clamped}`}
      aria-label={`Match score ${clamped}`}
    >
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={3}
          className="text-muted"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={3}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={tone}
        />
      </svg>
      <span className={cn("absolute text-[10px] font-semibold tabular-nums", tone)}>{clamped}</span>
    </span>
  );
}
