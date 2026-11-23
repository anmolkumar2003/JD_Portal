import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { BudgetStatus } from "@/types/api";

interface BudgetBadgeProps {
  status: BudgetStatus;
  className?: string;
}

/** Advisory budget label only — never implies rejection. */
export function BudgetBadge({ status, className }: BudgetBadgeProps) {
  if (status === "unknown") return null;
  if (status === "above") {
    return (
      <Badge variant="warning" className={cn("whitespace-nowrap", className)}>
        Above budget
      </Badge>
    );
  }
  return (
    <Badge variant="success" className={cn("whitespace-nowrap", className)}>
      Within budget
    </Badge>
  );
}
