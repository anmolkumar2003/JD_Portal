import {
  CheckCircle2,
  CircleDashed,
  PauseCircle,
  UserCheck,
  XCircle,
  type LucideIcon,
} from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { JOB_STATUS_LABELS } from "@/lib/labels";
import type { JobStatus } from "@/types/api";

const STATUS_STYLES: Record<JobStatus, { variant: BadgeProps["variant"]; icon: LucideIcon }> = {
  draft: { variant: "secondary", icon: CircleDashed },
  open: { variant: "success", icon: CheckCircle2 },
  on_hold: { variant: "warning", icon: PauseCircle },
  closed: { variant: "outline", icon: XCircle },
  filled: { variant: "default", icon: UserCheck },
};

/** Status chip: color is always paired with an icon and a text label. */
export function StatusBadge({ status }: { status: JobStatus }) {
  const { variant, icon: Icon } = STATUS_STYLES[status];
  return (
    <Badge variant={variant} className="whitespace-nowrap">
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {JOB_STATUS_LABELS[status]}
    </Badge>
  );
}
