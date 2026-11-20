"use client";

import { ErrorState } from "@/components/error-state";

export default function CareersError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="container py-14">
      <ErrorState error={null} title="We couldn't load our open roles" onRetry={reset} />
    </div>
  );
}
