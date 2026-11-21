"use client";

import { Search, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useDepartments, useLocations } from "@/hooks/use-lookups";
import { JOB_STATUS_LABELS } from "@/lib/labels";
import type { JobStatus } from "@/types/api";

export interface JobFilterValues {
  q: string;
  status: string;
  department_id: string;
  location_id: string;
}

interface JobFiltersProps {
  value: JobFilterValues;
  onChange: (changes: Partial<JobFilterValues>) => void;
}

const SEARCH_DEBOUNCE_MS = 300;

export function JobFilters({ value, onChange }: JobFiltersProps) {
  const departments = useDepartments();
  const locations = useLocations();
  const [search, setSearch] = useState(value.q);

  useEffect(() => setSearch(value.q), [value.q]);

  useEffect(() => {
    if (search === value.q) return;
    const timer = window.setTimeout(() => onChange({ q: search }), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [search, value.q, onChange]);

  const hasFilters = Boolean(value.q || value.status || value.department_id || value.location_id);

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center" role="search">
      <div className="relative lg:w-72">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <label htmlFor="job-search" className="sr-only">
          Search jobs by title
        </label>
        <Input
          id="job-search"
          type="search"
          placeholder="Search by title"
          className="pl-9"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:flex-1">
        <div>
          <label htmlFor="job-status" className="sr-only">
            Status
          </label>
          <Select
            id="job-status"
            value={value.status}
            onChange={(e) => onChange({ status: e.target.value })}
          >
            <option value="">All statuses</option>
            {(Object.keys(JOB_STATUS_LABELS) as JobStatus[]).map((s) => (
              <option key={s} value={s}>
                {JOB_STATUS_LABELS[s]}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label htmlFor="job-department" className="sr-only">
            Department
          </label>
          <Select
            id="job-department"
            value={value.department_id}
            onChange={(e) => onChange({ department_id: e.target.value })}
            disabled={departments.isPending}
          >
            <option value="">All departments</option>
            {departments.data?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label htmlFor="job-location" className="sr-only">
            Location
          </label>
          <Select
            id="job-location"
            value={value.location_id}
            onChange={(e) => onChange({ location_id: e.target.value })}
            disabled={locations.isPending}
          >
            <option value="">All locations</option>
            {locations.data?.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </Select>
        </div>
      </div>
      {hasFilters && (
        <Button
          variant="ghost"
          onClick={() => onChange({ q: "", status: "", department_id: "", location_id: "" })}
        >
          <X aria-hidden />
          Clear
        </Button>
      )}
    </div>
  );
}
