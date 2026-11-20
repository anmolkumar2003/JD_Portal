"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Check, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Controller, useForm, type FieldPath } from "react-hook-form";
import { z } from "zod";

import { SkillChips, SkillChipsInput } from "@/components/skill-chips";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { JobPublishError, useSaveJob } from "@/hooks/use-jobs";
import { useDepartments, useLocations } from "@/hooks/use-lookups";
import { ApiError } from "@/lib/api";
import {
  EMPLOYMENT_TYPE_LABELS,
  WORK_MODE_LABELS,
  formatExperience,
  formatSalary,
} from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { EmploymentType, Job, JobFieldsInput, RequirementsInput, WorkMode } from "@/types/api";

const WORK_MODES = Object.keys(WORK_MODE_LABELS) as [WorkMode, ...WorkMode[]];
const EMPLOYMENT_TYPES = Object.keys(EMPLOYMENT_TYPE_LABELS) as [
  EmploymentType,
  ...EmploymentType[],
];

const skillSchema = z.object({ name: z.string(), weight: z.number() });

/** Numeric inputs stay strings in the form and are converted on submit. */
const optionalDecimal = (places: number, message: string) =>
  z
    .string()
    .trim()
    .refine((v) => v === "" || new RegExp(`^\\d+(\\.\\d{1,${places}})?$`).test(v), message);

const jobFormSchema = z.object({
  title: z
    .string()
    .trim()
    .min(2, "Title must be at least 2 characters")
    .max(200, "Title must be at most 200 characters"),
  department_id: z.string(),
  location_id: z.string(),
  work_mode: z.enum(WORK_MODES),
  employment_type: z.enum(EMPLOYMENT_TYPES),
  level: z.string().trim().max(50, "Level must be at most 50 characters"),
  openings: z
    .string()
    .trim()
    .refine(
      (v) => /^\d+$/.test(v) && Number(v) >= 1 && Number(v) <= 1000,
      "Enter a number from 1 to 1000",
    ),
  closes_at: z
    .string()
    .refine((v) => v === "" || v >= todayIso(), "Closing date cannot be in the past"),
  description: z.string().max(20_000, "Description is too long"),
  responsibilities: z.string().max(20_000, "Responsibilities are too long"),
  qualifications: z.string().max(20_000, "Qualifications are too long"),
  salary_min: optionalDecimal(2, "Enter a valid amount"),
  salary_max: optionalDecimal(2, "Enter a valid amount"),
  salary_currency: z
    .string()
    .trim()
    .refine((v) => v === "" || /^[A-Za-z]{3}$/.test(v), "Use a 3-letter code, e.g. INR"),
  required_skills: z.array(skillSchema).max(50, "At most 50 skills"),
  preferred_skills: z.array(skillSchema).max(50, "At most 50 skills"),
  min_experience: optionalDecimal(1, "Enter years, e.g. 3 or 3.5"),
  max_experience: optionalDecimal(1, "Enter years, e.g. 3 or 3.5"),
  education_level: z.string().trim().max(100, "Education level must be at most 100 characters"),
});

type JobFormValues = z.infer<typeof jobFormSchema>;

const STEPS: { title: string; description: string; fields: FieldPath<JobFormValues>[] }[] = [
  {
    title: "Basics",
    description: "Title, team placement and logistics.",
    fields: [
      "title",
      "department_id",
      "location_id",
      "work_mode",
      "employment_type",
      "level",
      "openings",
      "closes_at",
      "salary_min",
      "salary_max",
      "salary_currency",
    ],
  },
  {
    title: "Description",
    description: "What the role is and what the person will do.",
    fields: ["description", "responsibilities", "qualifications"],
  },
  {
    title: "Requirements",
    description: "Skills and experience used to match candidates.",
    fields: [
      "required_skills",
      "preferred_skills",
      "min_experience",
      "max_experience",
      "education_level",
    ],
  },
  { title: "Review", description: "Check everything, then save or publish.", fields: [] },
];

function todayIso(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function isoToDateInput(value: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function decimalToInput(value: string | null): string {
  return value === null ? "" : Number(value).toString();
}

function defaultValues(job?: Job): JobFormValues {
  const req = job?.requirements;
  return {
    title: job?.title ?? "",
    department_id: job?.department?.id ?? "",
    location_id: job?.location?.id ?? "",
    work_mode: job?.work_mode ?? "onsite",
    employment_type: job?.employment_type ?? "full_time",
    level: job?.level ?? "",
    openings: String(job?.openings ?? 1),
    closes_at: isoToDateInput(job?.closes_at ?? null),
    description: job?.description ?? "",
    responsibilities: job?.responsibilities ?? "",
    qualifications: job?.qualifications ?? "",
    salary_min: decimalToInput(job?.salary_min ?? null),
    salary_max: decimalToInput(job?.salary_max ?? null),
    salary_currency: job?.salary_currency ?? "",
    required_skills: req?.required_skills ?? [],
    preferred_skills: req?.preferred_skills ?? [],
    min_experience: decimalToInput(req?.min_experience ?? null),
    max_experience: decimalToInput(req?.max_experience ?? null),
    education_level: req?.education_level ?? "",
  };
}

const orNull = (v: string) => (v.trim() === "" ? null : v.trim());
const numberOrNull = (v: string) => (v.trim() === "" ? null : Number(v));

function toPayload(values: JobFormValues): {
  fields: JobFieldsInput;
  requirements: RequirementsInput;
} {
  return {
    fields: {
      title: values.title.trim(),
      department_id: orNull(values.department_id),
      location_id: orNull(values.location_id),
      work_mode: values.work_mode,
      employment_type: values.employment_type,
      level: orNull(values.level),
      description: values.description.trim(),
      responsibilities: orNull(values.responsibilities),
      qualifications: orNull(values.qualifications),
      salary_min: numberOrNull(values.salary_min),
      salary_max: numberOrNull(values.salary_max),
      salary_currency: orNull(values.salary_currency)?.toUpperCase() ?? null,
      openings: Number(values.openings),
      // The job closes at the end of the chosen day in the recruiter's time zone.
      closes_at: values.closes_at ? new Date(`${values.closes_at}T23:59:59`).toISOString() : null,
    },
    requirements: {
      required_skills: values.required_skills,
      preferred_skills: values.preferred_skills,
      min_experience: numberOrNull(values.min_experience),
      max_experience: numberOrNull(values.max_experience),
      education_level: orNull(values.education_level),
    },
  };
}

function errorMessage(error: unknown): string {
  if (error instanceof JobPublishError) {
    const reason = error.cause instanceof ApiError ? ` ${error.cause.message}` : "";
    return `${error.message}${reason}`;
  }
  if (error instanceof ApiError) return error.message;
  return "Something went wrong. Please try again.";
}

function Field({
  id,
  label,
  error,
  hint,
  optional,
  children,
  className,
}: {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  optional?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={id}>
        {label}
        {optional && <span className="ml-1 font-normal text-muted-foreground">(optional)</span>}
      </Label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {error}
        </p>
      ) : (
        hint && <p className="text-xs text-muted-foreground">{hint}</p>
      )}
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="grid gap-1 py-3 sm:grid-cols-3 sm:gap-4">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm sm:col-span-2">{value || "—"}</dd>
    </div>
  );
}

interface JobFormProps {
  /** Existing job to edit; omit to create a new one. */
  job?: Job;
}

export function JobForm({ job }: JobFormProps) {
  const router = useRouter();
  const departments = useDepartments();
  const locations = useLocations();
  const saveJob = useSaveJob();
  const [step, setStep] = useState(0);
  // Set when a create succeeded but publishing failed, so a retry updates instead of duplicating.
  const [savedJobId, setSavedJobId] = useState<string | undefined>(job?.id);

  const {
    register,
    control,
    handleSubmit,
    trigger,
    setError,
    clearErrors,
    getValues,
    watch,
    formState: { errors },
  } = useForm<JobFormValues>({
    resolver: zodResolver(jobFormSchema),
    defaultValues: defaultValues(job),
    mode: "onTouched",
  });

  const canPublish = !job || job.status === "draft" || job.status === "on_hold";
  const isLast = step === STEPS.length - 1;

  const checkRanges = (stepIndex: number): boolean => {
    const values = getValues();
    const pairs: [FieldPath<JobFormValues>, string, string, string, number][] = [
      [
        "salary_max",
        values.salary_min,
        values.salary_max,
        "Maximum salary must be at least the minimum",
        0,
      ],
      [
        "max_experience",
        values.min_experience,
        values.max_experience,
        "Maximum experience must be at least the minimum",
        2,
      ],
    ];
    let ok = true;
    for (const [field, low, high, message, owner] of pairs) {
      if (owner !== stepIndex && stepIndex !== STEPS.length - 1) continue;
      if (low && high && Number(low) > Number(high)) {
        setError(field, { message });
        ok = false;
      }
    }
    if ((stepIndex === 2 || stepIndex === STEPS.length - 1) && Number(values.max_experience) > 50) {
      setError("max_experience", { message: "At most 50 years" });
      ok = false;
    }
    if ((stepIndex === 2 || stepIndex === STEPS.length - 1) && Number(values.min_experience) > 50) {
      setError("min_experience", { message: "At most 50 years" });
      ok = false;
    }
    return ok;
  };

  const validateStep = async (index: number) => {
    const valid = await trigger(STEPS[index]?.fields);
    return checkRanges(index) && valid;
  };

  const next = async () => {
    if (await validateStep(step)) setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };

  const goToStep = async (index: number) => {
    if (index < step) {
      setStep(index);
      return;
    }
    for (let i = step; i < index; i++) {
      if (!(await validateStep(i))) {
        setStep(i);
        return;
      }
    }
    setStep(index);
  };

  const submit = (publish: boolean) =>
    handleSubmit(
      (values) => {
        if (!checkRanges(STEPS.length - 1)) return;
        if (publish && !values.description.trim()) {
          setError("description", { message: "A description is required to publish" });
          setStep(1);
          return;
        }
        const { fields, requirements } = toPayload(values);
        saveJob.mutate(
          { jobId: savedJobId, fields, requirements, publish },
          {
            onSuccess: (saved) => router.push(`/jobs/${saved.id}`),
            onError: (error) => {
              if (error instanceof JobPublishError) setSavedJobId(error.job.id);
            },
          },
        );
      },
      (fieldErrors) => {
        const firstStep = STEPS.findIndex((s) => s.fields.some((f) => f in fieldErrors));
        if (firstStep >= 0) setStep(firstStep);
      },
    )();

  const values = watch();
  const departmentName = departments.data?.find((d) => d.id === values.department_id)?.name;
  const locationName = locations.data?.find((l) => l.id === values.location_id)?.name;
  const invalid = (name: keyof JobFormValues) =>
    errors[name] ? { "aria-invalid": true, "aria-describedby": `${name}-error` } : {};

  return (
    <form
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        if (!isLast) void next();
      }}
      className="space-y-6"
    >
      <nav aria-label="Form progress">
        <ol className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {STEPS.map((s, index) => {
            const state = index < step ? "done" : index === step ? "current" : "upcoming";
            return (
              <li key={s.title}>
                <button
                  type="button"
                  onClick={() => void goToStep(index)}
                  aria-current={state === "current" ? "step" : undefined}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg border p-3 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    state === "current" && "border-primary bg-accent",
                    state !== "current" && "hover:bg-muted",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                      state === "done" && "border-primary bg-primary text-primary-foreground",
                      state === "current" && "border-primary text-primary",
                      state === "upcoming" && "text-muted-foreground",
                    )}
                    aria-hidden
                  >
                    {state === "done" ? <Check className="h-4 w-4" /> : index + 1}
                  </span>
                  <span className="min-w-0 truncate font-medium">{s.title}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      <Card>
        <CardHeader>
          <CardTitle>{STEPS[step]?.title}</CardTitle>
          <CardDescription>{STEPS[step]?.description}</CardDescription>
        </CardHeader>
        <CardContent>
          {step === 0 && (
            <div className="grid gap-5 sm:grid-cols-2">
              <Field
                id="title"
                label="Job title"
                error={errors.title?.message}
                className="sm:col-span-2"
              >
                <Input
                  id="title"
                  placeholder="e.g. Senior Backend Engineer"
                  {...register("title")}
                  {...invalid("title")}
                />
              </Field>
              <Field id="department_id" label="Department" optional>
                <Controller
                  control={control}
                  name="department_id"
                  render={({ field }) => (
                    <Select id="department_id" {...field} disabled={departments.isPending}>
                      <option value="">No department</option>
                      {departments.data?.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </Select>
                  )}
                />
              </Field>
              <Field id="location_id" label="Location" optional>
                <Controller
                  control={control}
                  name="location_id"
                  render={({ field }) => (
                    <Select id="location_id" {...field} disabled={locations.isPending}>
                      <option value="">No location</option>
                      {locations.data?.map((l) => (
                        <option key={l.id} value={l.id}>
                          {l.name}
                        </option>
                      ))}
                    </Select>
                  )}
                />
              </Field>
              <Field id="work_mode" label="Work mode">
                <Select id="work_mode" {...register("work_mode")}>
                  {WORK_MODES.map((m) => (
                    <option key={m} value={m}>
                      {WORK_MODE_LABELS[m]}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field id="employment_type" label="Employment type">
                <Select id="employment_type" {...register("employment_type")}>
                  {EMPLOYMENT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {EMPLOYMENT_TYPE_LABELS[t]}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field id="level" label="Level" optional error={errors.level?.message}>
                <Input
                  id="level"
                  placeholder="e.g. Senior"
                  {...register("level")}
                  {...invalid("level")}
                />
              </Field>
              <Field id="openings" label="Openings" error={errors.openings?.message}>
                <Input
                  id="openings"
                  inputMode="numeric"
                  {...register("openings")}
                  {...invalid("openings")}
                />
              </Field>
              <Field
                id="closes_at"
                label="Closing date"
                optional
                error={errors.closes_at?.message}
                hint="Applications close at the end of this day."
              >
                <Input
                  id="closes_at"
                  type="date"
                  min={todayIso()}
                  {...register("closes_at")}
                  {...invalid("closes_at")}
                />
              </Field>
              <div className="hidden sm:block" />
              <Field
                id="salary_min"
                label="Salary minimum"
                optional
                error={errors.salary_min?.message}
              >
                <Input
                  id="salary_min"
                  inputMode="decimal"
                  placeholder="e.g. 2500000"
                  {...register("salary_min")}
                  {...invalid("salary_min")}
                />
              </Field>
              <Field
                id="salary_max"
                label="Salary maximum"
                optional
                error={errors.salary_max?.message}
              >
                <Input
                  id="salary_max"
                  inputMode="decimal"
                  placeholder="e.g. 4000000"
                  {...register("salary_max", { onChange: () => clearErrors("salary_max") })}
                  {...invalid("salary_max")}
                />
              </Field>
              <Field
                id="salary_currency"
                label="Currency"
                optional
                error={errors.salary_currency?.message}
                hint="Not shown on the public job page."
              >
                <Input
                  id="salary_currency"
                  placeholder="INR"
                  maxLength={3}
                  className="uppercase"
                  {...register("salary_currency")}
                  {...invalid("salary_currency")}
                />
              </Field>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-5">
              <Field
                id="description"
                label="Description"
                error={errors.description?.message}
                hint="Required before the job can be published."
              >
                <Textarea
                  id="description"
                  rows={8}
                  {...register("description")}
                  {...invalid("description")}
                />
              </Field>
              <Field
                id="responsibilities"
                label="Responsibilities"
                optional
                error={errors.responsibilities?.message}
              >
                <Textarea
                  id="responsibilities"
                  rows={5}
                  {...register("responsibilities")}
                  {...invalid("responsibilities")}
                />
              </Field>
              <Field
                id="qualifications"
                label="Qualifications"
                optional
                error={errors.qualifications?.message}
              >
                <Textarea
                  id="qualifications"
                  rows={5}
                  {...register("qualifications")}
                  {...invalid("qualifications")}
                />
              </Field>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <Controller
                control={control}
                name="required_skills"
                render={({ field, fieldState }) => (
                  <SkillChipsInput
                    label="Required skills"
                    tone="required"
                    value={field.value}
                    onChange={field.onChange}
                    exclude={values.preferred_skills.map((s) => s.name)}
                    error={fieldState.error?.message}
                    placeholder="e.g. Python"
                  />
                )}
              />
              <Controller
                control={control}
                name="preferred_skills"
                render={({ field, fieldState }) => (
                  <SkillChipsInput
                    label="Preferred skills"
                    tone="preferred"
                    value={field.value}
                    onChange={field.onChange}
                    exclude={values.required_skills.map((s) => s.name)}
                    error={fieldState.error?.message}
                    placeholder="e.g. Kubernetes"
                  />
                )}
              />
              <div className="grid gap-5 sm:grid-cols-3">
                <Field
                  id="min_experience"
                  label="Min experience (years)"
                  optional
                  error={errors.min_experience?.message}
                >
                  <Input
                    id="min_experience"
                    inputMode="decimal"
                    {...register("min_experience")}
                    {...invalid("min_experience")}
                  />
                </Field>
                <Field
                  id="max_experience"
                  label="Max experience (years)"
                  optional
                  error={errors.max_experience?.message}
                >
                  <Input
                    id="max_experience"
                    inputMode="decimal"
                    {...register("max_experience", {
                      onChange: () => clearErrors("max_experience"),
                    })}
                    {...invalid("max_experience")}
                  />
                </Field>
                <Field
                  id="education_level"
                  label="Education level"
                  optional
                  error={errors.education_level?.message}
                >
                  <Input
                    id="education_level"
                    placeholder="e.g. Bachelor's"
                    {...register("education_level")}
                    {...invalid("education_level")}
                  />
                </Field>
              </div>
            </div>
          )}

          {step === 3 && (
            <dl className="divide-y">
              <ReviewRow label="Title" value={values.title} />
              <ReviewRow label="Department" value={departmentName} />
              <ReviewRow label="Location" value={locationName} />
              <ReviewRow
                label="Work"
                value={`${WORK_MODE_LABELS[values.work_mode]} · ${EMPLOYMENT_TYPE_LABELS[values.employment_type]}`}
              />
              <ReviewRow label="Level" value={values.level} />
              <ReviewRow label="Openings" value={values.openings} />
              <ReviewRow label="Closing date" value={values.closes_at} />
              <ReviewRow
                label="Salary"
                value={formatSalary(
                  orNull(values.salary_min),
                  orNull(values.salary_max),
                  orNull(values.salary_currency)?.toUpperCase() ?? null,
                )}
              />
              <ReviewRow
                label="Description"
                value={
                  values.description.trim() ? (
                    <p className="line-clamp-4 whitespace-pre-line">{values.description}</p>
                  ) : (
                    <span className="text-destructive">Missing — required to publish</span>
                  )
                }
              />
              <ReviewRow
                label="Required skills"
                value={<SkillChips skills={values.required_skills} />}
              />
              <ReviewRow
                label="Preferred skills"
                value={<SkillChips skills={values.preferred_skills} tone="preferred" />}
              />
              <ReviewRow
                label="Experience"
                value={formatExperience(
                  orNull(values.min_experience),
                  orNull(values.max_experience),
                )}
              />
              <ReviewRow label="Education" value={values.education_level} />
            </dl>
          )}
        </CardContent>
      </Card>

      {saveJob.isError && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <span>{errorMessage(saveJob.error)}</span>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button
          type="button"
          variant="ghost"
          onClick={() => (step === 0 ? router.back() : setStep(step - 1))}
          disabled={saveJob.isPending}
        >
          <ChevronLeft aria-hidden />
          {step === 0 ? "Cancel" : "Back"}
        </Button>
        {isLast ? (
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant={canPublish ? "outline" : "default"}
              onClick={() => void submit(false)}
              disabled={saveJob.isPending}
            >
              {saveJob.isPending && !saveJob.variables?.publish && (
                <Loader2 className="animate-spin" aria-hidden />
              )}
              {job?.status === "draft" || !job ? "Save as draft" : "Save changes"}
            </Button>
            {canPublish && (
              <Button type="button" onClick={() => void submit(true)} disabled={saveJob.isPending}>
                {saveJob.isPending && saveJob.variables?.publish && (
                  <Loader2 className="animate-spin" aria-hidden />
                )}
                Save and publish
              </Button>
            )}
          </div>
        ) : (
          <Button type="submit">
            Next
            <ChevronRight aria-hidden />
          </Button>
        )}
      </div>
    </form>
  );
}
