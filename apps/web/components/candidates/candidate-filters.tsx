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
  DEFAULT_SKILLS_MODE,
  EMPTY_CANDIDATE_FILTERS,
  filtersToSavedPayload,
  savedPayloadToCandidateFilters,
  type CandidateFilterKey,
  type CandidateFilterValues,
} from "@/lib/candidate-filters";

export type { CandidateFilterValues };
import { APPLICATION_STATUS_LABELS, CANDIDATE_SOURCE_LABELS } from "@/lib/labels";
import type { ApplicationStatus, CandidateSource } from "@/types/api";

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
  "skills",
  "skills_mode",
  "tag",
  "is_shortlisted",
  "applied_from",
  "applied_to",
  "location",
  "experience_min",
  "experience_max",
  "notice_min_days",
  "notice_max_days",
  "expected_ctc_min",
  "expected_ctc_max",
  "expected_ctc_currency",
  "expected_ctc_unit",
  "ats_score_min",
  "ats_score_max",
  "rating_min",
  "rating_max",
  "status",
];

function activePopoverCount(value: CandidateFilterValues): number {
  return POPOVER_FILTER_KEYS.filter((key) => {
    if (key === "skills_mode") {
      return Boolean(value.skills) && value.skills_mode !== DEFAULT_SKILLS_MODE;
    }
    return Boolean(value[key]);
  }).length;
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
    if (value.score_min) list.push({ key: "score_min", label: `Min match: ${value.score_min}` });
    if (value.score_max) list.push({ key: "score_max", label: `Max match: ${value.score_max}` });
    if (value.skills) {
      const mode = value.skills_mode === "all" ? "all" : "any";
      list.push({ key: "skills", label: `Skills (${mode}): ${value.skills}` });
    } else if (value.skill) {
      list.push({ key: "skill", label: `Skill: ${value.skill}` });
    }
    if (value.tag) list.push({ key: "tag", label: `Tag: ${value.tag}` });
    if (value.is_shortlisted === "1") list.push({ key: "is_shortlisted", label: "Shortlisted" });
    if (value.is_shortlisted === "0")
      list.push({ key: "is_shortlisted", label: "Not shortlisted" });
    if (value.applied_from)
      list.push({ key: "applied_from", label: `From: ${value.applied_from}` });
    if (value.applied_to) list.push({ key: "applied_to", label: `To: ${value.applied_to}` });
    if (value.location) list.push({ key: "location", label: `Location: ${value.location}` });
    if (value.experience_min)
      list.push({ key: "experience_min", label: `Exp ≥ ${value.experience_min}y` });
    if (value.experience_max)
      list.push({ key: "experience_max", label: `Exp ≤ ${value.experience_max}y` });
    if (value.notice_min_days)
      list.push({ key: "notice_min_days", label: `Notice ≥ ${value.notice_min_days}d` });
    if (value.notice_max_days)
      list.push({ key: "notice_max_days", label: `Notice ≤ ${value.notice_max_days}d` });
    if (value.expected_ctc_min || value.expected_ctc_max) {
      const unit = value.expected_ctc_unit || "pa";
      const cur = value.expected_ctc_currency || "INR";
      const range = [value.expected_ctc_min || "…", value.expected_ctc_max || "…"].join("–");
      list.push({
        key: "expected_ctc_min",
        label: `CTC ${range} ${cur}/${unit}`,
      });
    }
    if (value.ats_score_min)
      list.push({ key: "ats_score_min", label: `ATS ≥ ${value.ats_score_min}` });
    if (value.ats_score_max)
      list.push({ key: "ats_score_max", label: `ATS ≤ ${value.ats_score_max}` });
    if (value.rating_min) list.push({ key: "rating_min", label: `Rating ≥ ${value.rating_min}` });
    if (value.rating_max) list.push({ key: "rating_max", label: `Rating ≤ ${value.rating_max}` });
    if (value.status) {
      list.push({
        key: "status",
        label: `Status: ${APPLICATION_STATUS_LABELS[value.status as ApplicationStatus] ?? value.status}`,
      });
    }
    return list;
  }, [value, jobTitleById, stageNameById, departmentNameById]);

  const popoverActive = activePopoverCount(value);

  const clearAll = () => onChange({ ...EMPTY_CANDIDATE_FILTERS });

  const removeChip = (key: string) => {
    if (key === "sort") onChange({ sort: DEFAULT_CANDIDATE_SORT });
    else if (key === "skills") onChange({ skills: "", skills_mode: DEFAULT_SKILLS_MODE });
    else if (key === "expected_ctc_min") {
      onChange({
        expected_ctc_min: "",
        expected_ctc_max: "",
        expected_ctc_currency: "",
        expected_ctc_unit: "",
      });
    } else onChange({ [key]: "" } as Partial<CandidateFilterValues>);
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
            Search name, email, company, title, skills, tags, notes or CV text
          </label>
          <Input
            id="candidate-search"
            type="search"
            placeholder="Search name, company, skills, tags, notes…"
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
                <Field label="Min match score" htmlFor="popover-score-min">
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
                <Field label="Max match score" htmlFor="popover-score-max">
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
                <Field label="Location" htmlFor="popover-location">
                  <Input
                    id="popover-location"
                    placeholder="e.g. Bangalore"
                    value={value.location}
                    onChange={(e) => onChange({ location: e.target.value })}
                  />
                </Field>
                <Field label="Status" htmlFor="popover-status">
                  <Select
                    id="popover-status"
                    value={value.status}
                    onChange={(e) => onChange({ status: e.target.value })}
                  >
                    <option value="">Any status</option>
                    {(Object.keys(APPLICATION_STATUS_LABELS) as ApplicationStatus[]).map((s) => (
                      <option key={s} value={s}>
                        {APPLICATION_STATUS_LABELS[s]}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Exp min (years)" htmlFor="popover-exp-min">
                  <Input
                    id="popover-exp-min"
                    type="number"
                    min={0}
                    max={60}
                    step={0.5}
                    placeholder="0"
                    value={value.experience_min}
                    onChange={(e) => onChange({ experience_min: e.target.value })}
                  />
                </Field>
                <Field label="Exp max (years)" htmlFor="popover-exp-max">
                  <Input
                    id="popover-exp-max"
                    type="number"
                    min={0}
                    max={60}
                    step={0.5}
                    placeholder="20"
                    value={value.experience_max}
                    onChange={(e) => onChange({ experience_max: e.target.value })}
                  />
                </Field>
                <Field label="Notice min (days)" htmlFor="popover-notice-min">
                  <Input
                    id="popover-notice-min"
                    type="number"
                    min={0}
                    max={730}
                    placeholder="0"
                    value={value.notice_min_days}
                    onChange={(e) => onChange({ notice_min_days: e.target.value })}
                  />
                </Field>
                <Field label="Notice max (days)" htmlFor="popover-notice-max">
                  <Input
                    id="popover-notice-max"
                    type="number"
                    min={0}
                    max={730}
                    placeholder="90"
                    value={value.notice_max_days}
                    onChange={(e) => onChange({ notice_max_days: e.target.value })}
                  />
                </Field>
                <Field label="Expected CTC min" htmlFor="popover-ctc-min">
                  <Input
                    id="popover-ctc-min"
                    type="number"
                    min={0}
                    placeholder="Amount"
                    value={value.expected_ctc_min}
                    onChange={(e) => onChange({ expected_ctc_min: e.target.value })}
                  />
                </Field>
                <Field label="Expected CTC max" htmlFor="popover-ctc-max">
                  <Input
                    id="popover-ctc-max"
                    type="number"
                    min={0}
                    placeholder="Amount"
                    value={value.expected_ctc_max}
                    onChange={(e) => onChange({ expected_ctc_max: e.target.value })}
                  />
                </Field>
                <Field label="CTC currency" htmlFor="popover-ctc-currency">
                  <Select
                    id="popover-ctc-currency"
                    value={value.expected_ctc_currency}
                    onChange={(e) => onChange({ expected_ctc_currency: e.target.value })}
                  >
                    <option value="">Any</option>
                    <option value="INR">INR</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="GBP">GBP</option>
                  </Select>
                </Field>
                <Field label="CTC unit" htmlFor="popover-ctc-unit">
                  <Select
                    id="popover-ctc-unit"
                    value={value.expected_ctc_unit}
                    onChange={(e) => onChange({ expected_ctc_unit: e.target.value })}
                  >
                    <option value="">Any</option>
                    <option value="pa">Per annum</option>
                    <option value="pm">Per month</option>
                  </Select>
                </Field>
                <Field label="ATS min" htmlFor="popover-ats-min">
                  <Input
                    id="popover-ats-min"
                    type="number"
                    min={0}
                    max={100}
                    placeholder="0"
                    value={value.ats_score_min}
                    onChange={(e) => onChange({ ats_score_min: e.target.value })}
                  />
                </Field>
                <Field label="ATS max" htmlFor="popover-ats-max">
                  <Input
                    id="popover-ats-max"
                    type="number"
                    min={0}
                    max={100}
                    placeholder="100"
                    value={value.ats_score_max}
                    onChange={(e) => onChange({ ats_score_max: e.target.value })}
                  />
                </Field>
                <Field label="Interview rating min" htmlFor="popover-rating-min">
                  <Input
                    id="popover-rating-min"
                    type="number"
                    min={1}
                    max={5}
                    step={0.1}
                    placeholder="1"
                    value={value.rating_min}
                    onChange={(e) => onChange({ rating_min: e.target.value })}
                  />
                </Field>
                <Field label="Interview rating max" htmlFor="popover-rating-max">
                  <Input
                    id="popover-rating-max"
                    type="number"
                    min={1}
                    max={5}
                    step={0.1}
                    placeholder="5"
                    value={value.rating_max}
                    onChange={(e) => onChange({ rating_max: e.target.value })}
                  />
                </Field>
                <Field label="Skills (comma-separated)" htmlFor="popover-skills">
                  <Input
                    id="popover-skills"
                    placeholder="Python, Kotlin"
                    value={value.skills || value.skill}
                    onChange={(e) =>
                      onChange({
                        skills: e.target.value,
                        skill: "",
                        skills_mode: value.skills_mode || DEFAULT_SKILLS_MODE,
                      })
                    }
                  />
                </Field>
                <Field label="Skills match" htmlFor="popover-skills-mode">
                  <Select
                    id="popover-skills-mode"
                    value={value.skills_mode || DEFAULT_SKILLS_MODE}
                    onChange={(e) => onChange({ skills_mode: e.target.value })}
                    disabled={!value.skills && !value.skill}
                  >
                    <option value="any">Match any</option>
                    <option value="all">Match all</option>
                  </Select>
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
