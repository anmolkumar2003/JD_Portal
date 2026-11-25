import { ArrowRight, Briefcase, Building2, MapPin } from "lucide-react";
import Link from "next/link";

import { EMPLOYMENT_TYPE_LABELS, WORK_MODE_LABELS, formatDate } from "@/lib/labels";
import type { PublicJobListItem } from "@/types/api";

export function JobCard({ job }: { job: PublicJobListItem }) {
  return (
    <Link
      href={`/careers/${job.slug}`}
      className="glass-strong group flex flex-col gap-4 rounded-[var(--radius)] p-5 transition-all duration-180 hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="space-y-1">
        <h3 className="font-semibold tracking-tight transition-colors group-hover:text-primary">
          {job.title}
        </h3>
        {job.level && <p className="text-sm text-muted-foreground">{job.level}</p>}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
        {job.department && (
          <li className="flex items-center gap-1.5">
            <Building2 className="h-4 w-4 text-primary/70" aria-hidden />
            {job.department.name}
          </li>
        )}
        {job.location && (
          <li className="flex items-center gap-1.5">
            <MapPin className="h-4 w-4 text-primary/70" aria-hidden />
            {job.location.name}
          </li>
        )}
        <li className="flex items-center gap-1.5">
          <Briefcase className="h-4 w-4 text-primary/70" aria-hidden />
          {WORK_MODE_LABELS[job.work_mode]} · {EMPLOYMENT_TYPE_LABELS[job.employment_type]}
        </li>
      </ul>
      <div className="mt-auto flex items-center justify-between text-xs text-muted-foreground">
        <span>Posted {formatDate(job.published_at)}</span>
        <span className="flex items-center gap-1 font-medium text-primary">
          View role
          <ArrowRight
            className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5"
            aria-hidden
          />
        </span>
      </div>
    </Link>
  );
}
