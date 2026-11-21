"use client";

import { Search, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useJobs } from "@/hooks/use-jobs";
import { usePipelineStages } from "@/hooks/use-applications";
import { CANDIDATE_SOURCE_LABELS } from "@/lib/labels";
import type { CandidateSource } from "@/types/api";

export interface CandidateFilterValues {
  q: string;
  job_id: string;
  stage_id: string;
  source: string;
}

interface CandidateFiltersProps {
  value: CandidateFilterValues;
  onChange: (changes: Partial<CandidateFilterValues>) => void;
}

const SEARCH_DEBOUNCE_MS = 300;

export function CandidateFilters({ value, onChange }: CandidateFiltersProps) {
  const jobs = useJobs({ page_size: 100, sort: "title" });
  const stages = usePipelineStages();
  const [search, setSearch] = useState(value.q);

  useEffect(() => setSearch(value.q), [value.q]);

  useEffect(() => {
    if (search === value.q) return;
    const timer = window.setTimeout(() => onChange({ q: search }), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [search, value.q, onChange]);

  const hasFilters = Boolean(value.q || value.job_id || value.stage_id || value.source);

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center" role="search">
      <div className="relative lg:w-72">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <label htmlFor="candidate-search" className="sr-only">
          Search by name, email or skill
        </label>
        <Input
          id="candidate-search"
          type="search"
          placeholder="Search name, email or skill"
          className="pl-9"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:flex-1">
        <div>
          <label htmlFor="candidate-job" className="sr-only">
            Job
          </label>
          <Select
            id="candidate-job"
            value={value.job_id}
            onChange={(e) => onChange({ job_id: e.target.value })}
          >
            <option value="">All jobs</option>
            {(jobs.data?.items ?? []).map((job) => (
              <option key={job.id} value={job.id}>
                {job.title}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label htmlFor="candidate-stage" className="sr-only">
            Stage
          </label>
          <Select
            id="candidate-stage"
            value={value.stage_id}
            onChange={(e) => onChange({ stage_id: e.target.value })}
          >
            <option value="">All stages</option>
            {(stages.data ?? []).map((stage) => (
              <option key={stage.id} value={stage.id}>
                {stage.name}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label htmlFor="candidate-source" className="sr-only">
            Source
          </label>
          <Select
            id="candidate-source"
            value={value.source}
            onChange={(e) => onChange({ source: e.target.value })}
          >
            <option value="">All sources</option>
            {(Object.keys(CANDIDATE_SOURCE_LABELS) as CandidateSource[]).map((source) => (
              <option key={source} value={source}>
                {CANDIDATE_SOURCE_LABELS[source]}
              </option>
            ))}
          </Select>
        </div>
      </div>
      {hasFilters && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => onChange({ q: "", job_id: "", stage_id: "", source: "" })}
        >
          <X aria-hidden />
          Clear
        </Button>
      )}
    </div>
  );
}
