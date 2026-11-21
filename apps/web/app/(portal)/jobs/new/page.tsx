"use client";

import { Lock } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { JobForm } from "@/components/jobs/job-form";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { useAuth } from "@/hooks/use-auth";
import { canManageJobs } from "@/lib/permissions";

export default function NewJobPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Breadcrumbs items={[{ label: "Jobs", href: "/jobs" }, { label: "New job" }]} />
        <h1 className="text-2xl font-semibold tracking-tight">Create job</h1>
      </div>
      {canManageJobs(user?.role) ? (
        <JobForm />
      ) : (
        <EmptyState
          icon={Lock}
          title="You can't create jobs"
          description="Only recruiters and HR admins can create jobs."
        />
      )}
    </div>
  );
}
