import type { ReactNode } from "react";

import { Breadcrumbs, type Crumb } from "@/components/layout/breadcrumbs";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  breadcrumbs?: Crumb[];
  title: string;
  subtitle?: string;
  action?: ReactNode;
  className?: string;
}

/** Consistent page title row: breadcrumbs, title, subtitle, one primary action. */
export function PageHeader({ breadcrumbs, title, subtitle, action, className }: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between",
        className,
      )}
    >
      <div className="min-w-0 space-y-1">
        {breadcrumbs && breadcrumbs.length > 0 && <Breadcrumbs items={breadcrumbs} />}
        <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{title}</h1>
        {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0 self-start">{action}</div>}
    </div>
  );
}
