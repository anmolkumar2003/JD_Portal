import { ScoreRing } from "@/components/score-ring";
import { cn } from "@/lib/utils";

interface ScoreMetricProps {
  label: string;
  /** 0–100 for match/ATS rings; pass null when unknown. */
  percentScore?: number | null;
  /** Shown instead of a ring when set (e.g. interview average out of 5). */
  scaleValue?: string | null;
  className?: string;
}

/** Side-by-side advisory score — never combines metrics in the label. */
export function ScoreMetric({ label, percentScore, scaleValue, className }: ScoreMetricProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-1 rounded-md border bg-card px-3 py-2",
        className,
      )}
    >
      <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      {scaleValue !== undefined && scaleValue !== null ? (
        <span className="text-sm font-semibold tabular-nums">{scaleValue}</span>
      ) : (
        <ScoreRing score={percentScore ?? null} size={40} />
      )}
    </div>
  );
}
