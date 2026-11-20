import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { StageType } from "@/types/api";

const STAGE_VARIANT: Record<StageType, BadgeProps["variant"]> = {
  applied: "secondary",
  screening: "default",
  interview: "warning",
  offer: "success",
  hired: "success",
  rejected: "destructive",
  custom: "outline",
};

export function StageBadge({ name, type }: { name: string; type: StageType }) {
  return (
    <Badge variant={STAGE_VARIANT[type]} className="whitespace-nowrap">
      {name}
    </Badge>
  );
}
