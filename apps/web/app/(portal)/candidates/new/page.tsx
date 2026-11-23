"use client";

import { Lock } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AddCandidateForm } from "@/components/candidates/add-candidate-form";
import { EmptyState } from "@/components/empty-state";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { canManageJobs } from "@/lib/permissions";

function NewCandidatePageContent() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("job_id") ?? undefined;
  const departmentId = searchParams.get("department_id") ?? undefined;

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Breadcrumbs
          items={[{ label: "Candidates", href: "/candidates" }, { label: "Add candidate" }]}
        />
        <h1 className="text-2xl font-semibold tracking-tight">Add candidate</h1>
      </div>
      {canManageJobs(user?.role) ? (
        <AddCandidateForm sharedJobId={jobId} sharedDepartmentId={departmentId} />
      ) : (
        <EmptyState
          icon={Lock}
          title="You can't add candidates"
          description="Only recruiters and HR admins can manually add candidates."
        />
      )}
    </div>
  );
}

export default function NewCandidatePage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6" aria-busy="true">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <NewCandidatePageContent />
    </Suspense>
  );
}
