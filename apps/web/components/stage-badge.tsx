import { Badge } from "@/components/ui/badge";
import type { StageRef, StageType } from "@/types/api";

const VARIANT: Record<
  StageType,
  "secondary" | "default" | "warning" | "success" | "destructive" | "outline"
> = {
  applied: "secondary",
  screening: "default",
  interview: "warning",
  offer: "success",
  hired: "success",
  rejected: "destructive",
  custom: "outline",
};

interface StageBadgeProps {
  stage: Pick<StageRef, "name" | "type">;
}

export function StageBadge({ stage }: StageBadgeProps) {
  return <Badge variant={VARIANT[stage.type]}>{stage.name}</Badge>;
}
