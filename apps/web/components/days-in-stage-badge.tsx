import { Badge } from "@/components/ui/badge";
import { daysInStage } from "@/lib/labels";

interface DaysInStageBadgeProps {
  stageEnteredAt: string;
  className?: string;
}

/** Amber after 7 days in stage, red after 14. */
export function DaysInStageBadge({ stageEnteredAt, className }: DaysInStageBadgeProps) {
  const days = daysInStage(stageEnteredAt);
  const label = days === 0 ? "Today" : `${days}d in stage`;
  const variant = days >= 14 ? "destructive" : days >= 7 ? "warning" : "secondary";
  return (
    <Badge variant={variant} className={className}>
      {label}
    </Badge>
  );
}
