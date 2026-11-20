import { Users } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";

export default function CandidatesPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Breadcrumbs items={[{ label: "Candidates" }]} />
        <h1 className="text-2xl font-semibold tracking-tight">Candidates</h1>
      </div>
      <EmptyState
        icon={Users}
        title="No candidates yet"
        description="Candidates appear here once people apply through the careers site."
      />
    </div>
  );
}
