"use client";

import {
  BookmarkPlus,
  ChevronDown,
  Filter,
  Loader2,
  Search,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { FilterChips, type FilterChip } from "@/components/filter-chips";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select } from "@/components/ui/select";
import { usePipelineStages } from "@/hooks/use-applications";
import { useJobs } from "@/hooks/use-jobs";
import { useDepartments } from "@/hooks/use-lookups";
import {
  useCreateSavedFilter,
  useDeleteSavedFilter,
  useSavedFilters,
} from "@/hooks/use-saved-filters";
import {
  DEFAULT_CANDIDATE_SORT,
  EMPTY_CANDIDATE_FILTERS,
  filtersToSavedPayload,
  savedPayloadToCandidateFilters,
  type CandidateFilterKey,
  type CandidateFilterValues,
} from "@/lib/candidate-filters";

export type { CandidateFilterValues };
import { CANDIDATE_SOURCE_LABELS } from "@/lib/labels";
import type { CandidateSource } from "@/types/api";

interface CandidateFiltersProps {
  value: CandidateFilterValues;
  onChange: (changes: Partial<CandidateFilterValues>) => void;
}

const SEARCH_DEBOUNCE_MS = 300;
const POPOVER_FILTER_KEYS: CandidateFilterKey[] = [
  "job_id",
  "stage_id",
  "source",
  "department_id",
  "score_min",
  "score_max",
  "skill",
  "tag",
  "is_shortlisted",
  "applied_from",
  "applied_to",
];

function activePopoverCount(value: CandidateFilterValues): number {
  return POPOVER_FILTER_KEYS.filter((key) => Boolean(value[key])).length;
}

export function CandidateFilters({ value, onChange }: CandidateFiltersProps) {
  const jobs = useJobs({ page_size: 100, sort: "title" });
  const stages = usePipelineStages();
  const departments = useDepartments();
  const savedFilters = useSavedFilters();
  const createSaved = useCreateSavedFilter();
  const deleteSaved = useDeleteSavedFilter();

  const [search, setSearch] = useState(value.q);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveName, setSaveName] = useState("");

  useEffect(() => setSearch(value.q), [value.q]);

  useEffect(() => {
    if (search === value.q) return;
    const timer = window.setTimeout(() => onChange({ q: search }), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [search, value.q, onChange]);

  const jobTitleById = useMemo(() => {
    const map = new Map<string, string>();
    for (const job of jobs.data?.items ?? []) map.set(job.id, job.title);
    return map;
  }, [jobs.data?.items]);

  const stageNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const stage of stages.data ?? []) map.set(stage.id, stage.name);
    return map;
  }, [stages.data]);

  const departmentNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const dept of departments.data ?? []) map.set(dept.id, dept.name);
    return map;
  }, [departments.data]);

  const chips = useMemo((): FilterChip[] => {
    const list: FilterChip[] = [];
    if (value.q) list.push({ key: "q", label: `Search: ${value.q}` });
    if (value.job_id) {
      list.push({
        key: "job_id",
        label: `Job: ${jobTitleById.get(value.job_id) ?? value.job_id}`,
      });
    }
    if (value.stage_id) {
      list.push({
        key: "stage_id",
        label: `Stage: ${stageNameById.get(value.stage_id) ?? value.stage_id}`,
      });
    }
    if (value.source) {
      list.push({
        key: "source",
        label: `Source: ${CANDIDATE_SOURCE_LABELS[value.source as CandidateSource] ?? value.source}`,
      });
    }
    if (value.department_id) {
      list.push({
        key: "department_id",
        label: `Department: ${departmentNameById.get(value.department_id) ?? value.department_id}`,
      });
    }
    if (value.score_min) list.push({ key: "score_min", label: `Min score: ${value.score_min}` });
    if (value.score_max) list.push({ key: "score_max", label: `Max score: ${value.score_max}` });
    if (value.skill) list.push({ key: "skill", label: `Skill: ${value.skill}` });
    if (value.tag) list.push({ key: "tag", label: `Tag: ${value.tag}` });
    if (value.is_shortlisted === "1") list.push({ key: "is_shortlisted", label: "Shortlisted" });
    if (value.is_shortlisted === "0")
      list.push({ key: "is_shortlisted", label: "Not shortlisted" });
    if (value.applied_from)
      list.push({ key: "applied_from", label: `From: ${value.applied_from}` });
    if (value.applied_to) list.push({ key: "applied_to", label: `To: ${value.applied_to}` });
    return list;
  }, [value, jobTitleById, stageNameById, departmentNameById]);

  const popoverActive = activePopoverCount(value);

  const clearAll = () => onChange({ ...EMPTY_CANDIDATE_FILTERS });

  const removeChip = (key: string) => {
    if (key === "sort") onChange({ sort: DEFAULT_CANDIDATE_SORT });
    else onChange({ [key]: "" } as Partial<CandidateFilterValues>);
  };

  const applySaved = (filters: Record<string, unknown>) => {
    onChange({ ...EMPTY_CANDIDATE_FILTERS, ...savedPayloadToCandidateFilters(filters) });
  };

  const submitSave = () => {
    const name = saveName.trim();
    if (!name) return;
    const payload = filtersToSavedPayload(value);
    if (Object.keys(payload).length === 0) {
      toast.error("Set at least one filter before saving");
      return;
    }
    createSaved.mutate(
      { name, filters: payload },
      {
        onSuccess: () => {
          toast.success("Filter saved");
          setSaveOpen(false);
          setSaveName("");
        },
        onError: () => toast.error("Could not save filter"),
      },
    );
  };

  return (
    <div className="space-y-3" role="search">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="relative flex-1 lg:max-w-sm">
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

        <div className="flex flex-wrap items-center gap-2">
          <Popover>
            <PopoverTrigger asChild>
              <Button type="button" variant="outline" size="sm" className="gap-2">
                <SlidersHorizontal className="h-4 w-4" aria-hidden />
                Filters
                {popoverActive > 0 && (
                  <span className="rounded-full bg-primary px-1.5 text-[10px] font-semibold text-primary-foreground">
                    {popoverActive}
                  </span>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[min(24rem,calc(100vw-2rem))] p-0" align="start">
              <div className="border-b px-4 py-3">
                <p className="text-sm font-medium">Filter candidates</p>
              </div>
              <div className="grid max-h-[min(28rem,60vh)] gap-3 overflow-y-auto p-4 sm:grid-cols-2">
                <Field label="Job" htmlFor="popover-job">
                  <Select
                    id="popover-job"
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
                </Field>
                <Field label="Stage" htmlFor="popover-stage">
                  <Select
                    id="popover-stage"
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
                </Field>
                <Field label="Source" htmlFor="popover-source">
                  <Select
                    id="popover-source"
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
                </Field>
                <Field label="Department" htmlFor="popover-department">
                  <Select
                    id="popover-department"
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
                </Field>
                <Field label="Min score" htmlFor="popover-score-min">
                  <Input
                    id="popover-score-min"
                    type="number"
                    min={0}
                    max={100}
                    placeholder="0"
                    value={value.score_min}
                    onChange={(e) => onChange({ score_min: e.target.value })}
                  />
                </Field>
                <Field label="Max score" htmlFor="popover-score-max">
                  <Input
                    id="popover-score-max"
                    type="number"
                    min={0}
                    max={100}
                    placeholder="100"
                    value={value.score_max}
                    onChange={(e) => onChange({ score_max: e.target.value })}
                  />
                </Field>
                <Field label="Skill" htmlFor="popover-skill">
                  <Input
                    id="popover-skill"
                    placeholder="e.g. Python"
                    value={value.skill}
                    onChange={(e) => onChange({ skill: e.target.value })}
                  />
                </Field>
                <Field label="Tag" htmlFor="popover-tag">
                  <Input
                    id="popover-tag"
                    placeholder="Tag name"
                    value={value.tag}
                    onChange={(e) => onChange({ tag: e.target.value })}
                  />
                </Field>
                <Field label="Shortlisted" htmlFor="popover-shortlisted">
                  <Select
                    id="popover-shortlisted"
                    value={value.is_shortlisted}
                    onChange={(e) => onChange({ is_shortlisted: e.target.value })}
                  >
                    <option value="">Any</option>
                    <option value="1">Shortlisted only</option>
                    <option value="0">Not shortlisted</option>
                  </Select>
                </Field>
                <Field label="Applied from" htmlFor="popover-from">
                  <Input
                    id="popover-from"
                    type="date"
                    value={value.applied_from}
                    onChange={(e) => onChange({ applied_from: e.target.value })}
                  />
                </Field>
                <Field label="Applied to" htmlFor="popover-to">
                  <Input
                    id="popover-to"
                    type="date"
                    value={value.applied_to}
                    onChange={(e) => onChange({ applied_to: e.target.value })}
                  />
                </Field>
              </div>
            </PopoverContent>
          </Popover>

          <div className="min-w-[8rem]">
            <label htmlFor="candidate-sort" className="sr-only">
              Sort
            </label>
            <Select
              id="candidate-sort"
              value={value.sort}
              onChange={(e) => onChange({ sort: e.target.value })}
            >
              <option value="-applied_at">Newest applied</option>
              <option value="-overall_score">Highest score</option>
              <option value="overall_score">Lowest score</option>
              <option value="last_name">Name A–Z</option>
            </Select>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button type="button" variant="outline" size="sm" className="gap-1">
                <Filter className="h-4 w-4" aria-hidden />
                Saved
                <ChevronDown className="h-3 w-3 opacity-60" aria-hidden />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>Saved filters</DropdownMenuLabel>
              <DropdownMenuItem
                onSelect={(e) => {
                  e.preventDefault();
                  setSaveOpen(true);
                }}
              >
                <BookmarkPlus aria-hidden />
                Save current…
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {savedFilters.isPending && (
                <div className="flex justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              )}
              {savedFilters.isSuccess && savedFilters.data.length === 0 && (
                <p className="px-2 py-3 text-xs text-muted-foreground">No saved filters yet</p>
              )}
              {savedFilters.data?.map((row) => (
                <DropdownMenuItem
                  key={row.id}
                  className="flex items-center justify-between gap-2"
                  onSelect={(e) => {
                    e.preventDefault();
                    applySaved(row.filters);
                  }}
                >
                  <span className="truncate">{row.name}</span>
                  <button
                    type="button"
                    className="shrink-0 rounded p-1 text-muted-foreground hover:bg-muted hover:text-destructive"
                    aria-label={`Delete ${row.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSaved.mutate(row.id, {
                        onSuccess: () => toast.success("Filter deleted"),
                        onError: () => toast.error("Could not delete filter"),
                      });
                    }}
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <FilterChips chips={chips} onRemove={removeChip} onClearAll={clearAll} />

      <Dialog open={saveOpen} onOpenChange={setSaveOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Save filter set</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="saved-filter-name">Name</Label>
            <Input
              id="saved-filter-name"
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              placeholder="e.g. Senior backend — shortlisted"
              maxLength={100}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitSave();
              }}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setSaveOpen(false)}>
              Cancel
            </Button>
            <Button type="button" disabled={createSaved.isPending} onClick={submitSave}>
              {createSaved.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor} className="text-xs text-muted-foreground">
        {label}
      </Label>
      {children}
    </div>
  );
}
