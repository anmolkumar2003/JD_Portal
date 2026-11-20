"use client";

import { Search, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { usePipelineStages } from "@/hooks/use-lookups";
import { useJobs } from "@/hooks/use-jobs";
import { SOURCE_LABELS } from "@/lib/labels";
import type { CandidateSource } from "@/types/api";

export interface CandidateFilterValues {
  q: string;
  job_id: string;
  stage_id: string;
  source: string;
  applied_from: string;
  applied_to: string;
}

interface CandidateFiltersProps {
  value: CandidateFilterValues;
  onChange: (changes: Partial<CandidateFilterValues>) => void;
}

const SEARCH_DEBOUNCE_MS = 300;
const SOURCES = Object.keys(SOURCE_LABELS) as CandidateSource[];

export function CandidateFilters({ value, onChange }: CandidateFiltersProps) {
  const stages = usePipelineStages();
  const jobs = useJobs({ page: 1, page_size: 100, sort: "title" });
  const [search, setSearch] = useState(value.q);

  useEffect(() => setSearch(value.q), [value.q]);

  useEffect(() => {
    if (search === value.q) return;
    const timer = window.setTimeout(() => onChange({ q: search }), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [search, value.q, onChange]);

  const hasFilters = Boolean(
    value.q ||
    value.job_id ||
    value.stage_id ||
    value.source ||
    value.applied_from ||
    value.applied_to,
  );

  return (
    <div className="flex flex-col gap-3" role="search">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="relative lg:w-72">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <label htmlFor="candidate-search" className="sr-only">
            Search by name, email, or skill
          </label>
          <Input
            id="candidate-search"
            className="pl-9"
            value={search}
            placeholder="Search name, email, skill…"
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select
          aria-label="Filter by job"
          value={value.job_id}
          onChange={(e) => onChange({ job_id: e.target.value })}
        >
          <option value="">All jobs</option>
          {jobs.data?.items.map((job) => (
            <option key={job.id} value={job.id}>
              {job.title}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Filter by stage"
          value={value.stage_id}
          onChange={(e) => onChange({ stage_id: e.target.value })}
        >
          <option value="">All stages</option>
          {stages.data?.map((stage) => (
            <option key={stage.id} value={stage.id}>
              {stage.name}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Filter by source"
          value={value.source}
          onChange={(e) => onChange({ source: e.target.value })}
        >
          <option value="">All sources</option>
          {SOURCES.map((source) => (
            <option key={source} value={source}>
              {SOURCE_LABELS[source]}
            </option>
          ))}
        </Select>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex items-center gap-2">
          <label htmlFor="applied-from" className="text-sm text-muted-foreground">
            From
          </label>
          <Input
            id="applied-from"
            type="date"
            value={value.applied_from}
            onChange={(e) => onChange({ applied_from: e.target.value })}
            className="w-auto"
          />
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="applied-to" className="text-sm text-muted-foreground">
            To
          </label>
          <Input
            id="applied-to"
            type="date"
            value={value.applied_to}
            onChange={(e) => onChange({ applied_to: e.target.value })}
            className="w-auto"
          />
        </div>
        {hasFilters && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() =>
              onChange({
                q: "",
                job_id: "",
                stage_id: "",
                source: "",
                applied_from: "",
                applied_to: "",
              })
            }
          >
            <X aria-hidden />
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}
