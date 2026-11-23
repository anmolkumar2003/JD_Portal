"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { AlertCircle, Check, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Controller, useForm, type FieldPath } from "react-hook-form";
import { z } from "zod";

import { CvDropzone, cvFileError } from "@/components/careers/cv-dropzone";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { cn } from "@/lib/utils";

const optionalNumber = (pattern: RegExp, message: string, max?: number) =>
  z
    .string()
    .trim()
    .refine(
      (v) => v === "" || (pattern.test(v) && (max === undefined || Number(v) <= max)),
      message,
    );

const applySchema = z.object({
  first_name: z.string().trim().min(1, "Enter your first name").max(100),
  last_name: z.string().trim().min(1, "Enter your last name").max(100),
  email: z.email("Enter a valid email address"),
  phone: z
    .string()
    .trim()
    .regex(/^\+?[0-9 ()\-.]{6,40}$/, "Enter a valid phone number, e.g. +91 98765 43210"),
  current_location: z.string().trim().max(200),
  linkedin_url: z
    .string()
    .trim()
    .max(500)
    .refine(
      (v) => v === "" || /^https?:\/\/\S+$/i.test(v),
      "Enter a full URL starting with https://",
    ),
  current_company: z.string().trim().max(200),
  current_title: z.string().trim().max(200),
  total_experience_years: optionalNumber(/^\d+(\.\d)?$/, "Enter years, e.g. 4 or 4.5 (max 50)", 50),
  expected_ctc: optionalNumber(/^\d+(\.\d{1,2})?$/, "Enter an amount using digits only"),
  notice_period_days: optionalNumber(/^\d+$/, "Enter days from 0 to 365", 365),
  cover_letter: z.string().trim().max(5000, "Keep it under 5000 characters"),
  cv: z.custom<File | null>().superRefine((file, ctx) => {
    if (!file) {
      ctx.addIssue({ code: "custom", message: "Please upload your CV" });
      return;
    }
    const error = cvFileError(file);
    if (error) ctx.addIssue({ code: "custom", message: error });
  }),
  consent: z.boolean().refine((v) => v, "You must agree before you can apply"),
  website: z.string(),
});

type ApplyValues = z.infer<typeof applySchema>;

const STEPS: { title: string; description: string; fields: FieldPath<ApplyValues>[] }[] = [
  {
    title: "Personal details",
    description: "How we can reach you.",
    fields: ["first_name", "last_name", "email", "phone", "current_location", "linkedin_url"],
  },
  {
    title: "Experience",
    description: "A little about your current role.",
    fields: [
      "current_company",
      "current_title",
      "total_experience_years",
      "expected_ctc",
      "notice_period_days",
      "cover_letter",
    ],
  },
  {
    title: "CV and consent",
    description: "Upload your CV and confirm how we use your data.",
    fields: ["cv", "consent"],
  },
];

const DEFAULTS: ApplyValues = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  current_location: "",
  linkedin_url: "",
  current_company: "",
  current_title: "",
  total_experience_years: "",
  expected_ctc: "",
  notice_period_days: "",
  cover_letter: "",
  cv: null,
  consent: false,
  website: "",
};

function toFormData(values: ApplyValues): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(values)) {
    if (key === "cv" || key === "consent") continue;
    if (typeof value === "string" && (value.trim() !== "" || key === "website")) {
      data.append(key, value.trim());
    }
  }
  data.append("consent", String(values.consent));
  if (values.cv) data.append("cv", values.cv);
  return data;
}

function Field({
  id,
  label,
  error,
  optional,
  hint,
  className,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  optional?: boolean;
  hint?: string;
  className?: string;
  children: ReactNode;
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

interface ApplyFormProps {
  slug: string;
  jobTitle: string;
  orgName: string;
}

export function ApplyForm({ slug, jobTitle, orgName }: ApplyFormProps) {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const {
    register,
    control,
    handleSubmit,
    trigger,
    setError,
    formState: { errors },
  } = useForm<ApplyValues>({
    resolver: zodResolver(applySchema),
    defaultValues: DEFAULTS,
    mode: "onTouched",
  });

  const submission = useMutation({
    mutationFn: (values: ApplyValues) => api.publicJobs.apply(slug, toFormData(values)),
    onSuccess: (result) => {
      const query = new URLSearchParams({ ref: result.reference_no, title: result.job_title });
      router.push(`/careers/${slug}/applied?${query.toString()}`);
    },
    onError: (error) => {
      if (!(error instanceof ApiError)) return;
      if (error.code === "invalid_file") {
        setError("cv", { message: error.message });
        setStep(2);
      } else if (error.code === "validation_error" && Array.isArray(error.details)) {
        let firstStep = STEPS.length;
        for (const issue of error.details as { loc?: unknown[]; msg?: string }[]) {
          const field = issue.loc?.at(-1);
          const stepIndex = STEPS.findIndex((s) =>
            s.fields.includes(field as FieldPath<ApplyValues>),
          );
          if (stepIndex >= 0) {
            setError(field as FieldPath<ApplyValues>, {
              message: (issue.msg ?? "Invalid value").replace(/^Value error, /, ""),
            });
            firstStep = Math.min(firstStep, stepIndex);
          }
        }
        if (firstStep < STEPS.length) setStep(firstStep);
      }
    },
  });

  const isLast = step === STEPS.length - 1;
  const invalid = (name: keyof ApplyValues) =>
    errors[name] ? { "aria-invalid": true, "aria-describedby": `${name}-error` } : {};

  const next = async () => {
    if (await trigger(STEPS[step]?.fields)) setStep((s) => s + 1);
  };

  const onSubmit = handleSubmit(
    (values) => submission.mutate(values),
    (fieldErrors) => {
      const firstStep = STEPS.findIndex((s) => s.fields.some((f) => f in fieldErrors));
      if (firstStep >= 0) setStep(firstStep);
    },
  );

  const bannerError =
    submission.error instanceof ApiError &&
    !["invalid_file", "validation_error"].includes(submission.error.code)
      ? submission.error.code === "network_error"
        ? "We couldn't reach our servers. Check your connection and try again."
        : submission.error.message
      : submission.isError && !(submission.error instanceof ApiError)
        ? "Something went wrong. Please try again."
        : null;

  return (
    <form
      noValidate
      onSubmit={(e) => {
        if (!isLast) {
          e.preventDefault();
          void next();
          return;
        }
        void onSubmit(e);
      }}
      className="space-y-6"
      aria-label={`Application for ${jobTitle}`}
    >
      <ol className="flex items-center gap-2" aria-label="Application progress">
        {STEPS.map((s, index) => {
          const state = index < step ? "done" : index === step ? "current" : "upcoming";
          return (
            <li key={s.title} className="flex flex-1 items-center gap-2">
              <span
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm font-semibold",
                  state === "done" && "border-primary bg-primary text-primary-foreground",
                  state === "current" && "border-primary text-primary",
                  state === "upcoming" && "text-muted-foreground",
                )}
                aria-current={state === "current" ? "step" : undefined}
              >
                {state === "done" ? <Check className="h-4 w-4" aria-hidden /> : index + 1}
                <span className="sr-only">
                  {s.title} ({state})
                </span>
              </span>
              <span
                className={cn(
                  "hidden truncate text-sm sm:block",
                  state === "current" ? "font-medium" : "text-muted-foreground",
                )}
                aria-hidden
              >
                {s.title}
              </span>
              {index < STEPS.length - 1 && <span className="h-px flex-1 bg-border" aria-hidden />}
            </li>
          );
        })}
      </ol>

      <Card>
        <CardHeader>
          <CardTitle>{STEPS[step]?.title}</CardTitle>
          <CardDescription>{STEPS[step]?.description}</CardDescription>
        </CardHeader>
        <CardContent>
          {step === 0 && (
            <div className="grid gap-5 sm:grid-cols-2">
              <Field id="first_name" label="First name" error={errors.first_name?.message}>
                <Input
                  id="first_name"
                  autoComplete="given-name"
                  {...register("first_name")}
                  {...invalid("first_name")}
                />
              </Field>
              <Field id="last_name" label="Last name" error={errors.last_name?.message}>
                <Input
                  id="last_name"
                  autoComplete="family-name"
                  {...register("last_name")}
                  {...invalid("last_name")}
                />
              </Field>
              <Field id="email" label="Email" error={errors.email?.message}>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  {...register("email")}
                  {...invalid("email")}
                />
              </Field>
              <Field id="phone" label="Phone" error={errors.phone?.message}>
                <Input
                  id="phone"
                  type="tel"
                  autoComplete="tel"
                  placeholder="+91 98765 43210"
                  {...register("phone")}
                  {...invalid("phone")}
                />
              </Field>
              <Field
                id="current_location"
                label="Current location"
                optional
                error={errors.current_location?.message}
              >
                <Input
                  id="current_location"
                  placeholder="e.g. Bengaluru"
                  {...register("current_location")}
                  {...invalid("current_location")}
                />
              </Field>
              <Field
                id="linkedin_url"
                label="LinkedIn profile"
                optional
                error={errors.linkedin_url?.message}
              >
                <Input
                  id="linkedin_url"
                  type="url"
                  placeholder="https://linkedin.com/in/you"
                  {...register("linkedin_url")}
                  {...invalid("linkedin_url")}
                />
              </Field>
            </div>
          )}

          {step === 1 && (
            <div className="grid gap-5 sm:grid-cols-2">
              <Field
                id="current_company"
                label="Current company"
                optional
                error={errors.current_company?.message}
              >
                <Input
                  id="current_company"
                  autoComplete="organization"
                  {...register("current_company")}
                  {...invalid("current_company")}
                />
              </Field>
              <Field
                id="current_title"
                label="Current job title"
                optional
                error={errors.current_title?.message}
              >
                <Input
                  id="current_title"
                  autoComplete="organization-title"
                  {...register("current_title")}
                  {...invalid("current_title")}
                />
              </Field>
              <Field
                id="total_experience_years"
                label="Total experience (years)"
                optional
                error={errors.total_experience_years?.message}
              >
                <Input
                  id="total_experience_years"
                  inputMode="decimal"
                  placeholder="e.g. 4.5"
                  {...register("total_experience_years")}
                  {...invalid("total_experience_years")}
                />
              </Field>
              <Field
                id="notice_period_days"
                label="Notice period (days)"
                optional
                error={errors.notice_period_days?.message}
              >
                <Input
                  id="notice_period_days"
                  inputMode="numeric"
                  placeholder="e.g. 30"
                  {...register("notice_period_days")}
                  {...invalid("notice_period_days")}
                />
              </Field>
              <Field
                id="expected_ctc"
                label="Expected annual CTC"
                optional
                hint="In your local currency, digits only."
                error={errors.expected_ctc?.message}
              >
                <Input
                  id="expected_ctc"
                  inputMode="decimal"
                  placeholder="e.g. 2500000"
                  {...register("expected_ctc")}
                  {...invalid("expected_ctc")}
                />
              </Field>
              <Field
                id="cover_letter"
                label="Cover letter"
                optional
                className="sm:col-span-2"
                error={errors.cover_letter?.message}
              >
                <Textarea
                  id="cover_letter"
                  rows={6}
                  placeholder="Why are you interested in this role?"
                  {...register("cover_letter")}
                  {...invalid("cover_letter")}
                />
              </Field>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <div className="space-y-2">
                <p className="text-sm font-medium">CV</p>
                <Controller
                  control={control}
                  name="cv"
                  render={({ field, fieldState }) => (
                    <CvDropzone
                      value={field.value}
                      onChange={(file) => {
                        field.onChange(file);
                        void trigger("cv");
                      }}
                      error={fieldState.error?.message}
                    />
                  )}
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="consent" className="flex items-start gap-3 text-sm">
                  <input
                    id="consent"
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 shrink-0 rounded border-input accent-primary"
                    {...register("consent")}
                    {...invalid("consent")}
                  />
                  <span>
                    I agree that {orgName} may store and process my personal data and CV to assess
                    my application for this and similar roles. I can ask for my data to be deleted
                    at any time.
                  </span>
                </label>
                {errors.consent && (
                  <p id="consent-error" className="text-sm text-destructive">
                    {errors.consent.message}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Honeypot: invisible to people and screen readers; bots tend to fill every field. */}
          <div className="absolute -left-[9999px] h-px w-px overflow-hidden" aria-hidden="true">
            <label htmlFor="website">Website</label>
            <input
              id="website"
              type="text"
              tabIndex={-1}
              autoComplete="off"
              {...register("website")}
            />
          </div>
        </CardContent>
      </Card>

      {bannerError && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <span>{bannerError}</span>
        </div>
      )}

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button
          type="button"
          variant="ghost"
          onClick={() => setStep((s) => s - 1)}
          disabled={step === 0 || submission.isPending}
          className={cn(step === 0 && "invisible")}
        >
          <ChevronLeft aria-hidden />
          Back
        </Button>
        <Button type="submit" size="lg" disabled={submission.isPending}>
          {isLast ? (
            <>
              {submission.isPending && <Loader2 className="animate-spin" aria-hidden />}
              {submission.isPending ? "Submitting…" : "Submit application"}
            </>
          ) : (
            <>
              Continue
              <ChevronRight aria-hidden />
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
