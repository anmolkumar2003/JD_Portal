import {
  getPath,
  isHighConfidenceApplicable,
  metaFor,
  parseTags,
  rowEffect,
  rowProblem,
  type FormValuesLike,
  type PreviewRow,
  type QuickFillOptions,
} from "@/lib/quick-fill";

/**
 * Quick fill apply rules (pure). Applying only decides which form fields to write; it never
 * saves anything. A value HR already has in the form is kept unless the row is ticked AND marked
 * "Replace".
 */

export interface WriteOp {
  /** react-hook-form field name, e.g. "first_name" or "current_ctc.amount". */
  path: string;
  value: string | boolean;
  /** What the field held before, for Undo. */
  previous: string | boolean;
}

export interface ApplyPlan {
  writes: WriteOp[];
  /** Labels of the rows that fill or replace something. */
  filled: string[];
  /** Rows ticked but kept as they were because the form already had a different value. */
  kept: string[];
  /** Rows ticked but not applied because their value is invalid. */
  invalid: string[];
}

export type ApplyMode = "selected" | "high";

function previousOf(values: FormValuesLike, path: string): string | boolean {
  const current = getPath(values, path);
  return typeof current === "boolean" ? current : typeof current === "string" ? current : "";
}

function mergeTags(existing: string, added: string[]): string {
  const have = parseTags(existing);
  const seen = new Set(have.map((t) => t.toLowerCase()));
  for (const tag of added) {
    if (!seen.has(tag.toLowerCase())) {
      seen.add(tag.toLowerCase());
      have.push(tag);
    }
  }
  return have.join(", ");
}

export function planApply(
  rows: PreviewRow[],
  values: FormValuesLike,
  options: QuickFillOptions,
  mode: ApplyMode,
): ApplyPlan {
  const plan: ApplyPlan = { writes: [], filled: [], kept: [], invalid: [] };
  const byPath = new Map<string, WriteOp>();
  const put = (path: string, value: string | boolean) => {
    const known = byPath.get(path);
    if (known) {
      known.value = value;
      return;
    }
    const op: WriteOp = { path, value, previous: previousOf(values, path) };
    byPath.set(path, op);
    plan.writes.push(op);
  };

  for (const row of rows) {
    if (!row.found) continue;
    const wanted = mode === "selected" ? row.checked : isHighConfidenceApplicable(row);
    if (!wanted) continue;
    if (rowProblem(row) !== null) {
      plan.invalid.push(row.label);
      continue;
    }
    const effect = rowEffect(row, values, options);
    if (effect === "none" || effect === "same") continue;
    if (effect === "conflict" && !row.replace) {
      plan.kept.push(row.label);
      continue;
    }
    const meta = metaFor(row.key);
    switch (row.kind) {
      case "salary": {
        const [amount, currency, unit] = meta.paths;
        if (amount) put(amount, row.text.trim());
        if (currency) put(currency, row.currency);
        if (unit) put(unit, row.unit);
        break;
      }
      case "boolean":
        put(meta.paths[0] ?? "", row.text === "yes");
        break;
      case "tags": {
        // Tags are added to what is there; skills and tags rows share the one field.
        const start = byPath.get("tags")?.value;
        const base = typeof start === "string" ? start : String(getPath(values, "tags") ?? "");
        put("tags", mergeTags(base, parseTags(row.text)));
        break;
      }
      case "text":
      case "number":
        put(meta.paths[0] ?? "", row.text.trim());
        break;
      default:
        put(meta.paths[0] ?? "", row.text);
    }
    plan.filled.push(row.label);
  }
  return plan;
}

export interface UndoResult {
  restored: string[];
  /** Fields HR changed after applying: left alone. */
  skipped: string[];
}

/** Which writes can be undone safely: the field still holds what quick fill wrote. */
export function planUndo(
  writes: WriteOp[],
  values: FormValuesLike,
): UndoResult & { ops: WriteOp[] } {
  const ops: WriteOp[] = [];
  const skipped: string[] = [];
  for (const op of [...writes].reverse()) {
    const current = getPath(values, op.path);
    const same =
      typeof op.value === "boolean" ? current === op.value : String(current ?? "") === op.value;
    if (same) ops.push(op);
    else skipped.push(op.path);
  }
  return { ops, restored: ops.map((o) => o.path), skipped };
}
