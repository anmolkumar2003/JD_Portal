/**
 * Turns a Quick fill parse result into create FormData / patch body for the chatbot "Add" action.
 */

import {
  buildCreateFormData,
  EMPTY_CANDIDATE_FORM,
  type CandidateFormValues,
} from "@/components/candidates/candidate-form-schema";
import { defaultSalaryForm } from "@/components/candidates/salary-fields";
import type {
  CandidatePatchInput,
  CandidateSource,
  QuickParseField,
  QuickParseOut,
  SalaryIn,
  SalaryUnit,
} from "@/types/api";

const SOURCES = new Set<CandidateSource>([
  "manual",
  "referral",
  "linkedin",
  "agency",
  "career_site",
]);

function asString(value: unknown): string {
  return typeof value === "string" ? value : value == null ? "" : String(value);
}

function asNumberString(value: unknown): string {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (typeof value === "string" && value.trim() !== "") return value.trim();
  return "";
}

function asSalary(value: unknown): SalaryIn | null {
  if (!value || typeof value !== "object") return null;
  const row = value as Record<string, unknown>;
  const amount = row.amount;
  if (typeof amount !== "number" && typeof amount !== "string") return null;
  const currency = typeof row.currency === "string" ? row.currency : "INR";
  const unit = row.unit === "pm" ? "pm" : "pa";
  return {
    amount: typeof amount === "number" ? amount : Number(amount),
    currency,
    unit: unit as SalaryUnit,
    negotiable: Boolean(row.negotiable),
  };
}

function fieldMap(result: QuickParseOut): Map<string, QuickParseField> {
  return new Map(result.fields.map((f) => [f.field, f]));
}

function pick(fields: Map<string, QuickParseField>, name: string): unknown {
  const item = fields.get(name);
  return item?.value ?? null;
}

/** Editable draft held inside the chatbot after Extract. */
export interface ChatCandidateDraft {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  current_location: string;
  current_company: string;
  current_title: string;
  total_experience_years: string;
  notice_period_days: string;
  linkedin_url: string;
  portfolio_url: string;
  source: CandidateSource;
  tags: string;
  job_id: string;
  current_ctc_amount: string;
  current_ctc_currency: string;
  current_ctc_unit: SalaryUnit;
  expected_ctc_amount: string;
  expected_ctc_currency: string;
  expected_ctc_unit: SalaryUnit;
  offered_ctc_amount: string;
  offered_ctc_currency: string;
  offered_ctc_unit: SalaryUnit;
}

export function emptyChatDraft(): ChatCandidateDraft {
  return {
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
    source: "manual",
    tags: "",
    job_id: "",
    current_ctc_amount: "",
    current_ctc_currency: "INR",
    current_ctc_unit: "pa",
    expected_ctc_amount: "",
    expected_ctc_currency: "INR",
    expected_ctc_unit: "pa",
    offered_ctc_amount: "",
    offered_ctc_currency: "INR",
    offered_ctc_unit: "pa",
  };
}

function applySalary(
  draft: ChatCandidateDraft,
  prefix: "current_ctc" | "expected_ctc" | "offered_ctc",
  value: unknown,
): void {
  const salary = asSalary(value);
  if (!salary) return;
  draft[`${prefix}_amount`] = String(salary.amount);
  draft[`${prefix}_currency`] = salary.currency;
  draft[`${prefix}_unit`] = salary.unit;
}

export function draftFromParse(result: QuickParseOut, jobId = ""): ChatCandidateDraft {
  const fields = fieldMap(result);
  const draft = emptyChatDraft();
  draft.first_name = asString(pick(fields, "first_name"));
  draft.last_name = asString(pick(fields, "last_name"));
  draft.email = asString(pick(fields, "email"));
  draft.phone = asString(pick(fields, "phone"));
  draft.current_location = asString(pick(fields, "current_location"));
  draft.current_company = asString(pick(fields, "current_company"));
  draft.current_title = asString(pick(fields, "current_title"));
  draft.total_experience_years = asNumberString(pick(fields, "total_experience_years"));
  draft.notice_period_days = asNumberString(pick(fields, "notice_period_days"));
  draft.linkedin_url = asString(pick(fields, "linkedin_url"));
  draft.portfolio_url = asString(pick(fields, "portfolio_url"));
  const source = asString(pick(fields, "source"));
  if (SOURCES.has(source as CandidateSource)) draft.source = source as CandidateSource;
  const skills = pick(fields, "skills");
  const tags = pick(fields, "tags");
  const tagParts: string[] = [];
  if (Array.isArray(skills)) tagParts.push(...skills.map(asString).filter(Boolean));
  if (Array.isArray(tags)) tagParts.push(...tags.map(asString).filter(Boolean));
  draft.tags = [...new Set(tagParts)].join(", ");
  draft.job_id = jobId;
  applySalary(draft, "current_ctc", pick(fields, "current_ctc"));
  applySalary(draft, "expected_ctc", pick(fields, "expected_ctc"));
  applySalary(draft, "offered_ctc", pick(fields, "offered_ctc"));
  return draft;
}

function salaryForm(
  amount: string,
  currency: string,
  unit: SalaryUnit,
): CandidateFormValues["current_ctc"] {
  return { ...defaultSalaryForm(), amount, currency, unit, negotiable: false };
}

export function toFormValues(draft: ChatCandidateDraft): CandidateFormValues {
  return {
    ...EMPTY_CANDIDATE_FORM,
    first_name: draft.first_name,
    last_name: draft.last_name,
    email: draft.email,
    phone: draft.phone,
    current_location: draft.current_location,
    current_company: draft.current_company,
    current_title: draft.current_title,
    total_experience_years: draft.total_experience_years,
    notice_period_days: draft.notice_period_days,
    linkedin_url: draft.linkedin_url,
    portfolio_url: draft.portfolio_url,
    source: draft.source === "career_site" ? "manual" : draft.source,
    tags: draft.tags,
    job_id: draft.job_id,
    current_ctc: salaryForm(
      draft.current_ctc_amount,
      draft.current_ctc_currency,
      draft.current_ctc_unit,
    ),
    expected_ctc: salaryForm(
      draft.expected_ctc_amount,
      draft.expected_ctc_currency,
      draft.expected_ctc_unit,
    ),
    offered_ctc: salaryForm(
      draft.offered_ctc_amount,
      draft.offered_ctc_currency,
      draft.offered_ctc_unit,
    ),
  };
}

export function toCreateFormData(draft: ChatCandidateDraft): FormData {
  return buildCreateFormData(toFormValues(draft), null);
}

function optionalSalary(amount: string, currency: string, unit: SalaryUnit): SalaryIn | null {
  if (!amount.trim()) return null;
  const n = Number(amount);
  if (!Number.isFinite(n)) return null;
  return { amount: n, currency, unit, negotiable: false };
}

/** Only fields that have a value — never wipe existing profile data with blanks. */
export function toPatchBody(draft: ChatCandidateDraft): CandidatePatchInput {
  const body: CandidatePatchInput = {};
  if (draft.first_name.trim()) body.first_name = draft.first_name.trim();
  if (draft.last_name.trim()) body.last_name = draft.last_name.trim();
  if (draft.email.trim()) body.email = draft.email.trim();
  if (draft.phone.trim()) body.phone = draft.phone.trim();
  if (draft.current_location.trim()) body.current_location = draft.current_location.trim();
  if (draft.current_company.trim()) body.current_company = draft.current_company.trim();
  if (draft.current_title.trim()) body.current_title = draft.current_title.trim();
  if (draft.total_experience_years.trim()) {
    body.total_experience_years = Number(draft.total_experience_years);
  }
  if (draft.notice_period_days.trim()) {
    body.notice_period_days = Number(draft.notice_period_days);
  }
  if (draft.linkedin_url.trim()) body.linkedin_url = draft.linkedin_url.trim();
  if (draft.portfolio_url.trim()) body.portfolio_url = draft.portfolio_url.trim();
  if (draft.source) body.source = draft.source;
  if (draft.tags.trim()) {
    body.tags = draft.tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
  }
  const current = optionalSalary(
    draft.current_ctc_amount,
    draft.current_ctc_currency,
    draft.current_ctc_unit,
  );
  if (current) body.current_ctc = current;
  const expected = optionalSalary(
    draft.expected_ctc_amount,
    draft.expected_ctc_currency,
    draft.expected_ctc_unit,
  );
  if (expected) body.expected_ctc = expected;
  const offered = optionalSalary(
    draft.offered_ctc_amount,
    draft.offered_ctc_currency,
    draft.offered_ctc_unit,
  );
  if (offered) body.offered_ctc = offered;
  return body;
}

export function missingForCreate(draft: ChatCandidateDraft): string[] {
  const missing: string[] = [];
  if (!draft.first_name.trim()) missing.push("first name");
  if (!draft.last_name.trim()) missing.push("last name");
  if (!draft.email.trim()) missing.push("email");
  if (!draft.phone.trim()) missing.push("phone");
  if (!draft.job_id.trim()) missing.push("job");
  return missing;
}
