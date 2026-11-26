import { CANDIDATE_SOURCE_LABELS } from "@/lib/labels";
import { linkedInUrlSchemaRefine } from "@/lib/linkedin";
import type {
  CandidateSource,
  QuickFillConfidence,
  QuickFillFieldName,
  QuickFillValue,
  QuickParseCandidate,
  QuickParseField,
  QuickParseOut,
  SalaryUnit,
} from "@/types/api";

/**
 * Quick fill: pure helpers that turn the API result into preview rows and decide what each row
 * would do to the form. No React and no network here, so the rules are easy to read and test.
 */

/** Currencies the salary fields offer. The API accepts any 3-letter code. */
export const SALARY_CURRENCIES = [
  "INR",
  "USD",
  "EUR",
  "GBP",
  "AED",
  "SAR",
  "QAR",
  "SGD",
  "AUD",
  "CAD",
] as const;

export type RowKind =
  "text" | "number" | "salary" | "boolean" | "tags" | "source" | "department" | "job";

interface FieldMeta {
  key: QuickFillFieldName;
  label: string;
  kind: RowKind;
  /** Form paths the row writes to (react-hook-form names). */
  paths: string[];
  /** Shown as a "Not found" row when the text had nothing for it. */
  showWhenMissing: boolean;
}

const salaryPaths = (prefix: string) => [
  `${prefix}.amount`,
  `${prefix}.currency`,
  `${prefix}.unit`,
];

export const FIELD_META: readonly FieldMeta[] = [
  {
    key: "first_name",
    label: "First name",
    kind: "text",
    paths: ["first_name"],
    showWhenMissing: true,
  },
  {
    key: "last_name",
    label: "Last name",
    kind: "text",
    paths: ["last_name"],
    showWhenMissing: true,
  },
  { key: "email", label: "Email", kind: "text", paths: ["email"], showWhenMissing: true },
  { key: "phone", label: "Phone", kind: "text", paths: ["phone"], showWhenMissing: true },
  {
    key: "current_location",
    label: "Location",
    kind: "text",
    paths: ["current_location"],
    showWhenMissing: true,
  },
  {
    key: "current_company",
    label: "Company",
    kind: "text",
    paths: ["current_company"],
    showWhenMissing: true,
  },
  {
    key: "current_title",
    label: "Title",
    kind: "text",
    paths: ["current_title"],
    showWhenMissing: true,
  },
  {
    key: "total_experience_years",
    label: "Experience (years)",
    kind: "number",
    paths: ["total_experience_years"],
    showWhenMissing: true,
  },
  {
    key: "notice_period_days",
    label: "Notice period (days)",
    kind: "number",
    paths: ["notice_period_days"],
    showWhenMissing: true,
  },
  {
    key: "current_ctc",
    label: "Current CTC",
    kind: "salary",
    paths: salaryPaths("current_ctc"),
    showWhenMissing: true,
  },
  {
    key: "current_ctc_negotiable",
    label: "Current CTC negotiable",
    kind: "boolean",
    paths: ["current_ctc.negotiable"],
    showWhenMissing: false,
  },
  {
    key: "expected_ctc",
    label: "Expected CTC",
    kind: "salary",
    paths: salaryPaths("expected_ctc"),
    showWhenMissing: true,
  },
  {
    key: "expected_ctc_negotiable",
    label: "Expected CTC negotiable",
    kind: "boolean",
    paths: ["expected_ctc.negotiable"],
    showWhenMissing: false,
  },
  {
    key: "offered_ctc",
    label: "Offered CTC",
    kind: "salary",
    paths: salaryPaths("offered_ctc"),
    showWhenMissing: false,
  },
  {
    key: "offered_ctc_negotiable",
    label: "Offered CTC negotiable",
    kind: "boolean",
    paths: ["offered_ctc.negotiable"],
    showWhenMissing: false,
  },
  // The form has one Tags field: skills found in the text are added to it.
  {
    key: "skills",
    label: "Skills (added to Tags)",
    kind: "tags",
    paths: ["tags"],
    showWhenMissing: false,
  },
  { key: "tags", label: "Tags", kind: "tags", paths: ["tags"], showWhenMissing: false },
  {
    key: "linkedin_url",
    label: "LinkedIn",
    kind: "text",
    paths: ["linkedin_url"],
    showWhenMissing: false,
  },
  {
    key: "portfolio_url",
    label: "Portfolio",
    kind: "text",
    paths: ["portfolio_url"],
    showWhenMissing: false,
  },
  { key: "source", label: "Source", kind: "source", paths: ["source"], showWhenMissing: false },
  {
    key: "department_hint",
    label: "Department",
    kind: "department",
    paths: ["department_id"],
    showWhenMissing: false,
  },
  { key: "job_hint", label: "Job", kind: "job", paths: ["job_id"], showWhenMissing: false },
];

const META_BY_KEY = new Map(FIELD_META.map((m) => [m.key, m]));

export function metaFor(key: QuickFillFieldName): FieldMeta {
  const meta = META_BY_KEY.get(key);
  if (!meta) throw new Error(`Unknown quick fill field: ${key}`);
  return meta;
}

export interface NamedOption {
  id: string;
  name: string;
}

/** What this particular form can take. The edit dialog has no job picker, for example. */
export interface QuickFillOptions {
  departments: NamedOption[];
  /** Null when the form has no job picker (edit dialog). */
  jobs: NamedOption[] | null;
  sources: readonly CandidateSource[];
  /** The department follows the selected job and cannot be set by hand. */
  departmentLocked: boolean;
}

export interface PreviewCandidate {
  /** Editable text form of the candidate (see `PreviewRow.text`). */
  text: string;
  unit: SalaryUnit;
  currency: string;
  display: string;
  reason: string;
}

export interface PreviewRow {
  key: QuickFillFieldName;
  label: string;
  kind: RowKind;
  /** The text had something (a value or choices) for this field. */
  found: boolean;
  confidence: QuickFillConfidence | null;
  reason: string;
  warning: string | null;
  /** Other readings. For a range these are low / midpoint / high; for ambiguity they are the choices. */
  candidates: PreviewCandidate[];
  /** True when there is no value yet and the user must pick one of `candidates`. */
  needsChoice: boolean;
  /**
   * The editable found value. Salary: the amount. Boolean: "yes" | "no". Tags: comma list.
   * Source / department / job: the option id.
   */
  text: string;
  unit: SalaryUnit;
  currency: string;
  checked: boolean;
  /** HR marked "Replace": only then may a row overwrite a value already in the form. */
  replace: boolean;
  /** Why the form cannot take this row, or null. */
  unsupported: string | null;
}

function emptyRow(meta: FieldMeta): PreviewRow {
  return {
    key: meta.key,
    label: meta.label,
    kind: meta.kind,
    found: false,
    confidence: null,
    reason: "",
    warning: null,
    candidates: [],
    needsChoice: false,
    text: "",
    unit: "pa",
    currency: "INR",
    checked: false,
    replace: false,
    unsupported: null,
  };
}

interface SalaryValue {
  amount: number;
  currency: string;
  unit: SalaryUnit;
}

function asSalary(value: QuickFillValue): SalaryValue | null {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return null;
  const { amount, currency, unit } = value;
  if (typeof amount !== "number" || typeof currency !== "string") return null;
  return { amount, currency, unit: unit === "pm" ? "pm" : "pa" };
}

function norm(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/** Department / job named in the text -> the matching option, if exactly one fits. */
function matchOption(
  hint: string,
  options: NamedOption[],
): { exact: NamedOption | null; near: NamedOption[] } {
  const wanted = norm(hint);
  if (!wanted) return { exact: null, near: [] };
  const exact = options.filter((o) => norm(o.name) === wanted);
  if (exact.length === 1) return { exact: exact[0] ?? null, near: [] };
  const near = options.filter((o) => {
    const name = norm(o.name);
    return name !== "" && (name.includes(wanted) || wanted.includes(name));
  });
  return { exact: null, near };
}

interface Converted {
  text: string;
  unit: SalaryUnit;
  currency: string;
}

function convert(
  meta: FieldMeta,
  value: QuickFillValue,
  options: QuickFillOptions,
): Converted | null {
  const base: Converted = { text: "", unit: "pa", currency: "INR" };
  switch (meta.kind) {
    case "text":
      return typeof value === "string" ? { ...base, text: value } : null;
    case "number":
      return typeof value === "number" || typeof value === "string"
        ? { ...base, text: String(value) }
        : null;
    case "salary": {
      const salary = asSalary(value);
      return salary
        ? { text: String(salary.amount), unit: salary.unit, currency: salary.currency }
        : null;
    }
    case "boolean":
      return typeof value === "boolean" ? { ...base, text: value ? "yes" : "no" } : null;
    case "tags":
      return Array.isArray(value) ? { ...base, text: value.map(String).join(", ") } : null;
    case "source":
      return typeof value === "string" ? { ...base, text: value } : null;
    case "department":
    case "job": {
      if (typeof value !== "string") return null;
      const pool = meta.kind === "department" ? options.departments : (options.jobs ?? []);
      const match = matchOption(value, pool);
      return match.exact ? { ...base, text: match.exact.id } : null;
    }
  }
}

function convertCandidate(
  meta: FieldMeta,
  c: QuickParseCandidate,
  options: QuickFillOptions,
): PreviewCandidate | null {
  const converted = convert(meta, c.value, options);
  return converted ? { ...converted, display: c.display, reason: c.reason } : null;
}

function rowFromField(
  meta: FieldMeta,
  field: QuickParseField,
  options: QuickFillOptions,
): PreviewRow {
  const row: PreviewRow = {
    ...emptyRow(meta),
    found: true,
    confidence: field.confidence,
    reason: field.reason,
    warning: field.warning,
  };
  let candidates = field.candidates
    .map((c) => convertCandidate(meta, c, options))
    .filter((c): c is PreviewCandidate => c !== null);
  const value = convert(meta, field.value, options);
  if (meta.kind === "source") {
    candidates = candidates.filter((c) => options.sources.includes(c.text as CandidateSource));
  }
  row.candidates = candidates;

  if (meta.kind === "department" || meta.kind === "job") {
    const hint = typeof field.value === "string" ? field.value : "";
    const pool = meta.kind === "department" ? options.departments : options.jobs;
    if (meta.kind === "job" && options.jobs === null) {
      row.unsupported = "This form has no job picker.";
    } else if (meta.kind === "department" && options.departmentLocked) {
      row.unsupported = "The department is taken from the selected job.";
    } else if (!value) {
      const near = pool ? matchOption(hint, pool).near : [];
      row.candidates = near.map((o) => ({
        text: o.id,
        unit: "pa",
        currency: "INR",
        display: o.name,
        reason: `Similar to "${hint}"`,
      }));
      row.needsChoice = row.candidates.length > 0;
      row.unsupported = row.needsChoice
        ? null
        : `No ${meta.label.toLowerCase()} named "${hint}" in the list.`;
    }
  }

  if (value) {
    row.text = value.text;
    row.unit = value.unit;
    row.currency = value.currency;
  } else if (row.candidates.length > 0) {
    row.needsChoice = true;
  }

  if (meta.kind === "source" && value && !options.sources.includes(value.text as CandidateSource)) {
    row.unsupported = `This form has no "${CANDIDATE_SOURCE_LABELS[value.text as CandidateSource] ?? value.text}" source.`;
  }
  // High confidence is pre-ticked; medium and low are left for HR to decide.
  row.checked = field.confidence === "high" && row.text !== "" && row.unsupported === null;
  return row;
}

export function buildRows(result: QuickParseOut, options: QuickFillOptions): PreviewRow[] {
  const byKey = new Map(result.fields.map((f) => [f.field, f]));
  const rows: PreviewRow[] = [];
  for (const meta of FIELD_META) {
    const field = byKey.get(meta.key);
    if (field) rows.push(rowFromField(meta, field, options));
    else if (meta.showWhenMissing) rows.push(emptyRow(meta));
  }
  return rows;
}

// --- Choosing between readings ------------------------------------------------------------------

/** Use one of a row's other readings (range end, midpoint, or a choice for an ambiguous field). */
export function pickCandidate(
  rows: PreviewRow[],
  key: QuickFillFieldName,
  index: number,
): PreviewRow[] {
  const target = rows.find((r) => r.key === key);
  const chosen = target?.candidates[index];
  if (!target || !chosen) return rows;
  // First and last name candidates are written as pairs: picking one picks the other's match.
  const partner = key === "first_name" ? "last_name" : key === "last_name" ? "first_name" : null;
  return rows.map((row) => {
    const pick =
      row.key === key
        ? chosen
        : row.key === partner && row.candidates.length === target.candidates.length
          ? row.candidates[index]
          : undefined;
    if (!pick) return row;
    return {
      ...row,
      text: pick.text,
      unit: pick.unit,
      currency: pick.currency,
      needsChoice: false,
      checked: row.unsupported === null,
    };
  });
}

// --- Current form values and what a row would do ------------------------------------------------

export type FormValuesLike = Record<string, unknown>;

export function getPath(values: FormValuesLike, path: string): unknown {
  let node: unknown = values;
  for (const part of path.split(".")) {
    if (node === null || typeof node !== "object") return undefined;
    node = (node as Record<string, unknown>)[part];
  }
  return node;
}

export interface CurrentInfo {
  /** Text shown in the "Current form value" column. */
  display: string;
  /** Nothing the user typed (blank, or the form's own default). */
  empty: boolean;
}

function str(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

export function parseTags(text: string): string[] {
  return text
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

export function currentInfo(
  row: PreviewRow,
  values: FormValuesLike,
  options: QuickFillOptions,
): CurrentInfo {
  const meta = metaFor(row.key);
  const first = meta.paths[0] ?? "";
  switch (meta.kind) {
    case "text":
    case "number": {
      const text = str(getPath(values, first));
      return { display: text, empty: text === "" };
    }
    case "salary": {
      const amount = str(getPath(values, `${first.split(".")[0]}.amount`));
      if (!amount) return { display: "", empty: true };
      const unit =
        getPath(values, `${first.split(".")[0]}.unit`) === "pm" ? "per month" : "per annum";
      const currency = str(getPath(values, `${first.split(".")[0]}.currency`)) || "INR";
      return { display: `${amount} ${currency} ${unit}`, empty: false };
    }
    case "boolean": {
      const on = getPath(values, first) === true;
      return { display: on ? "Yes" : "", empty: !on };
    }
    case "tags": {
      const text = str(getPath(values, "tags"));
      return { display: text, empty: text === "" };
    }
    case "source": {
      const text = str(getPath(values, "source"));
      // "Manual" is the form's default, not something HR chose.
      const label = text ? (CANDIDATE_SOURCE_LABELS[text as CandidateSource] ?? text) : "";
      return { display: label, empty: text === "" || text === "manual" };
    }
    case "department":
    case "job": {
      const id = str(getPath(values, first));
      const pool = meta.kind === "department" ? options.departments : (options.jobs ?? []);
      const name = pool.find((o) => o.id === id)?.name ?? "";
      return { display: name, empty: id === "" };
    }
  }
}

export type RowEffect =
  /** Would fill an empty field. */
  | "fill"
  /** The form already holds the same value. */
  | "same"
  /** The form holds a different value: needs "Replace". */
  | "conflict"
  /** Nothing to apply (no value, unsupported, or invalid). */
  | "none";

export function rowValueDisplay(row: PreviewRow, options: QuickFillOptions): string {
  switch (row.kind) {
    case "salary":
      return row.text
        ? `${row.text} ${row.currency} ${row.unit === "pm" ? "per month" : "per annum"}`
        : "";
    case "boolean":
      return row.text === "yes" ? "Yes" : row.text === "no" ? "No" : "";
    case "source":
      return CANDIDATE_SOURCE_LABELS[row.text as CandidateSource] ?? row.text;
    case "department":
      return options.departments.find((o) => o.id === row.text)?.name ?? "";
    case "job":
      return (options.jobs ?? []).find((o) => o.id === row.text)?.name ?? "";
    default:
      return row.text;
  }
}

function sameText(a: string, b: string): boolean {
  return a.trim().toLowerCase() === b.trim().toLowerCase();
}

export function rowEffect(
  row: PreviewRow,
  values: FormValuesLike,
  options: QuickFillOptions,
): RowEffect {
  if (!row.found || row.unsupported || row.text.trim() === "" || rowProblem(row) !== null) {
    return "none";
  }
  const current = currentInfo(row, values, options);
  const meta = metaFor(row.key);
  if (row.kind === "boolean") {
    // "No" over an empty (unticked) box changes nothing.
    if (row.text === "no") return current.empty ? "same" : "conflict";
    return current.empty ? "fill" : "same";
  }
  if (current.empty) return "fill";
  switch (row.kind) {
    case "tags": {
      const have = new Set(parseTags(current.display).map((t) => t.toLowerCase()));
      const missing = parseTags(row.text).filter((t) => !have.has(t.toLowerCase()));
      return missing.length === 0 ? "same" : "fill"; // tags are added, never replaced
    }
    case "salary": {
      const base = (meta.paths[0] ?? "").split(".")[0] ?? "";
      const unit = getPath(values, `${base}.unit`) === "pm" ? "pm" : "pa";
      const sameAmount = Number(str(getPath(values, `${base}.amount`))) === Number(row.text);
      return sameAmount && unit === row.unit ? "same" : "conflict";
    }
    case "source":
    case "department":
    case "job":
      return str(getPath(values, meta.paths[0] ?? "")) === row.text ? "same" : "conflict";
    default:
      return sameText(current.display, row.text) ? "same" : "conflict";
  }
}

// --- Validation of the (editable) found value ---------------------------------------------------

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\+?[0-9 ()\-.]{6,40}$/;

/** Same rules as the form's own schema, so an applied value never fails validation by surprise. */
export function rowProblem(row: PreviewRow): string | null {
  const text = row.text.trim();
  if (!text) return null;
  switch (row.key) {
    case "email":
      return EMAIL_RE.test(text) ? null : "Not a valid email address";
    case "phone":
      return PHONE_RE.test(text) ? null : "Not a valid phone number";
    case "total_experience_years":
      return /^\d+(\.\d)?$/.test(text) && Number(text) <= 50
        ? null
        : "Use years such as 4 or 4.5 (max 50)";
    case "notice_period_days":
      return /^\d+$/.test(text) && Number(text) <= 365 ? null : "Use whole days from 0 to 365";
    case "linkedin_url":
      return linkedInUrlSchemaRefine(text) ? null : "Use a LinkedIn profile URL";
    case "portfolio_url":
      return /^https?:\/\/\S+$/i.test(text) ? null : "Use a full URL starting with https://";
    case "current_ctc":
    case "expected_ctc":
    case "offered_ctc":
      return /^\d+(\.\d{1,2})?$/.test(text) && Number(text) > 0 ? null : "Enter a valid amount";
    case "first_name":
    case "last_name":
      return text.length <= 100 ? null : "At most 100 characters";
    default:
      return row.kind === "text" && text.length > 200 ? "At most 200 characters" : null;
  }
}

// --- Selection helpers --------------------------------------------------------------------------

export function isHighConfidenceApplicable(row: PreviewRow): boolean {
  return (
    row.confidence === "high" &&
    row.text.trim() !== "" &&
    row.unsupported === null &&
    !row.needsChoice
  );
}

export function foundCount(rows: PreviewRow[]): number {
  return rows.filter((r) => r.found).length;
}

export function confidenceLabel(c: QuickFillConfidence): string {
  return c === "high" ? "High" : c === "medium" ? "Medium" : "Low";
}
