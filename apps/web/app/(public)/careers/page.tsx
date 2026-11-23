import { SearchX } from "lucide-react";
import Link from "next/link";

import { CareersFilters } from "@/components/careers/careers-filters";
import { JobCard } from "@/components/careers/job-card";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { serverApi } from "@/lib/server-api";

type SearchParams = Record<string, string | string[] | undefined>;

const param = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value) ?? "";

export default async function CareersPage({ searchParams }: { searchParams: SearchParams }) {
  const filters = {
    q: param(searchParams.q),
    department_id: param(searchParams.department_id),
    location_id: param(searchParams.location_id),
  };
  const [jobs, options, config] = await Promise.all([
    serverApi.listPublicJobs({ ...filters, page_size: 100 }),
    serverApi.publicJobFilters(),
    serverApi.config(),
  ]);
  const filtered = Boolean(filters.q || filters.department_id || filters.location_id);

  return (
    <>
      <section className="border-b bg-gradient-to-b from-accent to-background">
        <div className="container space-y-8 py-14 sm:py-20">
          <div className="max-w-2xl space-y-3">
            <p className="text-sm font-semibold uppercase tracking-wide text-primary">
              Careers at {config.org_name}
            </p>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Do the best work of your career
            </h1>
            <p className="text-lg text-muted-foreground">
              We are hiring across engineering and people teams. Find a role that fits you and apply
              in a few minutes.
            </p>
          </div>
          <CareersFilters key={JSON.stringify(filters)} options={options} initial={filters} />
        </div>
      </section>

      <section className="container space-y-4 py-10" aria-labelledby="open-roles">
        <h2 id="open-roles" className="text-lg font-semibold">
          {jobs.total} open {jobs.total === 1 ? "role" : "roles"}
        </h2>
        {jobs.items.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {jobs.items.map((job) => (
              <JobCard key={job.slug} job={job} />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={SearchX}
            title={filtered ? "No roles match your search" : "No open roles right now"}
            description={
              filtered
                ? "Try a different title, or clear the filters to see every open role."
                : "Please check back soon. New roles are posted regularly."
            }
            action={
              filtered ? (
                <Button asChild variant="outline">
                  <Link href="/careers">Clear filters</Link>
                </Button>
              ) : undefined
            }
          />
        )}
      </section>
    </>
  );
}
