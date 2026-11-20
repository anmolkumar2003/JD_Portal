import { Skeleton } from "@/components/ui/skeleton";

export default function CareersLoading() {
  return (
    <div className="container space-y-8 py-14" aria-busy="true" aria-label="Loading">
      <div className="max-w-2xl space-y-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-10 w-full max-w-lg" />
        <Skeleton className="h-6 w-full max-w-md" />
      </div>
      <Skeleton className="h-16 w-full rounded-xl" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-40" />
        ))}
      </div>
    </div>
  );
}
