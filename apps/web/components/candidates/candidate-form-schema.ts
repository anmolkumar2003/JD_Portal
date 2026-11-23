import { z } from "zod";

import { defaultSalaryForm } from "@/components/candidates/salary-fields";
import { LINKEDIN_URL_MESSAGE, linkedInUrlSchemaRefine, normalizeLinkedInUrl } from "@/lib/linkedin";
import type { CandidateSource, SalaryUnit } from "@/types/api";

const salaryUnit = z.enum(["pa", "pm"] as const);

const salarySchema = z.object({
  amount: z
    .string()
    .trim()
    .refine((v) => v === "" || /^\d+(\.\d{1,2})?$/.test(v), "Enter a valid amount"),
  currency: z.string().trim().min(3).max(3),
  unit: salaryUnit,
  negotiable: z.boolean(),
});

const optionalDecimal = (pattern: RegExp, message: string, max?: number) =>
  z
    .string()
    .trim()
    .refine(
      (v) => v === "" || (pattern.test(v) && (max === undefined || Number(v) <= max)),
      message,
    );

const SOURCES = [
  "manual",
  "referral",
  "linkedin",
  "agency",
] as const satisfies readonly CandidateSource[];

export const candidateFormSchema = z.object({
  first_name: z.string().trim().min(1, "Enter first name").max(100),
  last_name: z.string().trim().min(1, "Enter last name").max(100),
  email: z.email("Enter a valid email address"),
  phone: z
    .string()
    .trim()
    .refine((v) => v === "" || /^\+?[0-9 ()\-.]{6,40}$/.test(v), "Enter a valid phone number"),
  current_location: z.string().trim().max(200),
  current_company: z.string().trim().max(200),
  current_title: z.string().trim().max(200),
  total_experience_years: optionalDecimal(
    /^\d+(\.\d)?$/,
    "Enter years, e.g. 4 or 4.5 (max 50)",
    50,
  ),
  notice_period_days: optionalDecimal(/^\d+$/, "Enter days from 0 to 365", 365),
  linkedin_url: z
    .string()
    .trim()
    .max(500)
    .refine((v) => linkedInUrlSchemaRefine(v), LINKEDIN_URL_MESSAGE),
  portfolio_url: z
    .string()
    .trim()
    .max(500)
    .refine(
      (v) => v === "" || /^https?:\/\/\S+$/i.test(v),
      "Enter a full URL starting with https://",
    ),
  department_id: z.string(),
  job_id: z.string(),
  source: z.enum(SOURCES),
  tags: z.string().trim().max(500),
  current_ctc: salarySchema,
  expected_ctc: salarySchema,
  offered_ctc: salarySchema,
});

export type CandidateFormValues = z.infer<typeof candidateFormSchema>;

export const EMPTY_CANDIDATE_FORM: CandidateFormValues = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  current_location: "",
  current_company: "",
  current_title: "",
  total_experience_years: "",
  notice_period_days: "",
  linkedin_url: "",
  portfolio_url: "",
  department_id: "",
  job_id: "",
  source: "manual",
  tags: "",
  current_ctc: defaultSalaryForm(),
  expected_ctc: defaultSalaryForm(),
  offered_ctc: defaultSalaryForm(),
};

export type AutofillKey = keyof Omit<
  CandidateFormValues,
  "department_id" | "job_id" | "source" | "tags" | "current_ctc" | "expected_ctc" | "offered_ctc"
>;

export function parseTagsInput(value: string): string[] {
  if (!value.trim()) return [];
  if (value.trim().startsWith("[")) {
    try {
      const parsed = JSON.parse(value) as unknown;
      if (Array.isArray(parsed)) return parsed.map(String).filter(Boolean);
    } catch {
      /* fall through */
    }
  }
  return value
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

export function appendSalary(fd: FormData, prefix: string, slice: SalaryFormSlice): void {
  const amount = slice.amount.trim();
  if (!amount) return;
  fd.append(`${prefix}_amount`, amount);
  fd.append(`${prefix}_currency`, slice.currency.toUpperCase());
  fd.append(`${prefix}_unit`, slice.unit);
  if (slice.negotiable) fd.append(`${prefix}_negotiable`, "true");
}

type SalaryFormSlice = {
  amount: string;
  currency: string;
  unit: SalaryUnit;
  negotiable: boolean;
};

export function buildCreateFormData(values: CandidateFormValues, cv: File | null): FormData {
  const fd = new FormData();
  fd.append("first_name", values.first_name.trim());
  fd.append("last_name", values.last_name.trim());
  fd.append("email", values.email.trim());
  if (values.phone.trim()) fd.append("phone", values.phone.trim());
  if (values.current_location.trim()) fd.append("current_location", values.current_location.trim());
  if (values.current_company.trim()) fd.append("current_company", values.current_company.trim());
  if (values.current_title.trim()) fd.append("current_title", values.current_title.trim());
  if (values.total_experience_years.trim()) {
    fd.append("total_experience_years", values.total_experience_years.trim());
  }
  if (values.notice_period_days.trim()) {
    fd.append("notice_period_days", values.notice_period_days.trim());
  }
  if (values.linkedin_url.trim()) {
    try {
      const normalized = normalizeLinkedInUrl(values.linkedin_url);
      if (normalized) fd.append("linkedin_url", normalized);
    } catch {
      fd.append("linkedin_url", values.linkedin_url.trim());
    }
  }
  if (values.portfolio_url.trim()) fd.append("portfolio_url", values.portfolio_url.trim());
  if (values.department_id) fd.append("department_id", values.department_id);
  if (values.job_id) fd.append("job_id", values.job_id);
  fd.append("source", values.source);
  const tags = parseTagsInput(values.tags);
  if (tags.length) fd.append("tags", JSON.stringify(tags));
  appendSalary(fd, "current_ctc", values.current_ctc);
  appendSalary(fd, "expected_ctc", values.expected_ctc);
  appendSalary(fd, "offered_ctc", values.offered_ctc);
  if (cv) fd.append("cv", cv);
  return fd;
}
