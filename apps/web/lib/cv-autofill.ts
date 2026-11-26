/**
 * Map CV parse results onto candidate form fields by field identity (named keys),
 * never by position. Values below the confidence floor stay blank for manual review.
 */

import type { CandidateFormValues } from "@/components/candidates/candidate-form-schema";
import type { CvParseOut } from "@/types/api";

/** Mirrors apps/api AUTOFILL_MIN_CONFIDENCE — only apply values the parser is sure about. */
export const AUTOFILL_MIN_CONFIDENCE = 0.6;

const CONFIDENCE_FOR_FIELD: Record<string, string> = {
  first_name: "name",
  last_name: "name",
  email: "email",
  phone: "phone",
  current_location: "location",
  current_company: "company",
  current_title: "title",
  total_experience_years: "experience",
};

export function isConfident(data: CvParseOut, formKey: keyof typeof CONFIDENCE_FOR_FIELD): boolean {
  const confKey = CONFIDENCE_FOR_FIELD[formKey];
  if (!confKey) return false;
  const score = data.confidence?.[confKey];
  if (typeof score !== "number") return false;
  return score >= AUTOFILL_MIN_CONFIDENCE;
}

/** Build a form patch from parse-cv / draft upload. Uncertain fields are omitted. */
export function parseToFormPatch(data: CvParseOut): Partial<CandidateFormValues> {
  const patch: Partial<CandidateFormValues> = {};
  if (data.first_name && isConfident(data, "first_name")) patch.first_name = data.first_name;
  if (data.last_name && isConfident(data, "last_name")) patch.last_name = data.last_name;
  if (data.email && isConfident(data, "email")) patch.email = data.email;
  if (data.phone && isConfident(data, "phone")) patch.phone = data.phone;
  if (data.current_location && isConfident(data, "current_location")) {
    patch.current_location = data.current_location;
  }
  if (data.current_company && isConfident(data, "current_company")) {
    patch.current_company = data.current_company;
  }
  if (data.current_title && isConfident(data, "current_title")) {
    patch.current_title = data.current_title;
  }
  if (data.total_experience_years != null && isConfident(data, "total_experience_years")) {
    const years = Math.round(Number(data.total_experience_years) * 10) / 10;
    if (Number.isFinite(years)) patch.total_experience_years = String(years);
  }
  if (data.linkedin_url) patch.linkedin_url = data.linkedin_url;
  return patch;
}
