"use client";

import { Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CANDIDATE_SOURCE_LABELS } from "@/lib/labels";
import {
  confidenceLabel,
  currentInfo,
  isHighConfidenceApplicable,
  rowEffect,
  rowProblem,
  SALARY_CURRENCIES,
  type FormValuesLike,
  type PreviewCandidate,
  type PreviewRow,
  type QuickFillOptions,
} from "@/lib/quick-fill";
import type { QuickFillConfidence, QuickFillFieldName, SalaryUnit } from "@/types/api";

function isSource(options: QuickFillOptions, text: string): boolean {
  return (options.sources as readonly string[]).includes(text);
}

const CONFIDENCE_VARIANT: Record<QuickFillConfidence, "success" | "warning" | "secondary"> = {
  high: "success",
  medium: "warning",
  low: "secondary",
};

interface QuickFillPreviewProps {
  rows: PreviewRow[];
  values: FormValuesLike;
  options: QuickFillOptions;
  warnings: string[];
  ignored: string[];
  truncated: boolean;
  onRowChange: (key: QuickFillFieldName, patch: Partial<PreviewRow>) => void;
  onPick: (key: QuickFillFieldName, index: number) => void;
  onApplySelected: () => void;
  onApplyHighConfidence: () => void;
  onCancel: () => void;
}

function sameReading(row: PreviewRow, c: PreviewCandidate): boolean {
  return row.text === c.text && row.unit === c.unit && row.currency === c.currency;
}

function ValueEditor({
  row,
  options,
  problem,
  onRowChange,
  onPick,
}: {
  row: PreviewRow;
  options: QuickFillOptions;
  problem: string | null;
  onRowChange: QuickFillPreviewProps["onRowChange"];
  onPick: QuickFillPreviewProps["onPick"];
}) {
  const label = `${row.label}: found value`;
  const testId = `quick-fill-value-${row.key}`;
  const set = (patch: Partial<PreviewRow>) => onRowChange(row.key, patch);
  const invalid = problem !== null || undefined;

  if (row.unsupported && row.kind !== "source") {
    return <p className="text-sm text-muted-foreground">{row.unsupported}</p>;
  }
  if (row.needsChoice) {
    return (
      <Select
        aria-label={`${row.label}: choose one`}
        data-testid={`quick-fill-choice-${row.key}`}
        className="h-9"
        value=""
        onChange={(e) => {
          if (e.target.value !== "") onPick(row.key, Number(e.target.value));
        }}
      >
        <option value="">Choose…</option>
        {row.candidates.map((c, index) => (
          <option key={`${c.display}-${index}`} value={index}>
            {c.display}
          </option>
        ))}
      </Select>
    );
  }

  switch (row.kind) {
    case "boolean":
      return (
        <Select
          aria-label={label}
          data-testid={testId}
          className="h-9"
          value={row.text}
          onChange={(e) => set({ text: e.target.value })}
        >
          <option value="yes">Yes</option>
          <option value="no">No</option>
        </Select>
      );
    case "source":
      return (
        <div className="space-y-1">
          <Select
            aria-label={label}
            data-testid={testId}
            className="h-9"
            value={isSource(options, row.text) ? row.text : ""}
            onChange={(e) => set({ text: e.target.value, unsupported: null })}
          >
            {!isSource(options, row.text) && <option value="">Choose…</option>}
            {options.sources.map((s) => (
              <option key={s} value={s}>
                {CANDIDATE_SOURCE_LABELS[s]}
              </option>
            ))}
          </Select>
          {row.unsupported && <p className="text-xs text-muted-foreground">{row.unsupported}</p>}
        </div>
      );
    case "department":
    case "job": {
      const pool = row.kind === "department" ? options.departments : (options.jobs ?? []);
      return (
        <Select
          aria-label={label}
          data-testid={testId}
          className="h-9"
          value={row.text}
          onChange={(e) => set({ text: e.target.value })}
        >
          {row.text === "" && <option value="">—</option>}
          {pool.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </Select>
      );
    }
    case "salary":
      return (
        <div className="space-y-1">
          <Input
            aria-label={label}
            aria-invalid={invalid}
            data-testid={testId}
            inputMode="decimal"
            className="h-9"
            value={row.text}
            onChange={(e) => set({ text: e.target.value })}
          />
          <div className="flex gap-1.5">
            <Select
              aria-label={`${row.label}: currency`}
              className="h-8 text-xs"
              value={row.currency}
              onChange={(e) => set({ currency: e.target.value })}
            >
              {SALARY_CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
            <Select
              aria-label={`${row.label}: per annum or per month`}
              className="h-8 text-xs"
              value={row.unit}
              onChange={(e) => set({ unit: e.target.value as SalaryUnit })}
            >
              <option value="pa">Per annum</option>
              <option value="pm">Per month</option>
            </Select>
          </div>
        </div>
      );
    default:
      return (
        <Input
          aria-label={label}
          aria-invalid={invalid}
          data-testid={testId}
          className="h-9"
          value={row.text}
          onChange={(e) => set({ text: e.target.value })}
        />
      );
  }
}

export function QuickFillPreview({
  rows,
  values,
  options,
  warnings,
  ignored,
  truncated,
  onRowChange,
  onPick,
  onApplySelected,
  onApplyHighConfidence,
  onCancel,
}: QuickFillPreviewProps) {
  const selectable = rows.filter((r) => r.found).length;
  const ticked = rows.filter((r) => r.checked && rowEffect(r, values, options) !== "none").length;
  const highReady = rows.filter(
    (r) => isHighConfidenceApplicable(r) && rowEffect(r, values, options) !== "none",
  ).length;

  return (
    <section
      aria-label="Quick fill preview"
      data-testid="quick-fill-preview"
      className="space-y-3 rounded-xl border border-border/70 bg-background/40 p-3"
    >
      {(warnings.length > 0 || truncated) && (
        <ul
          role="status"
          data-testid="quick-fill-warnings"
          className="space-y-1 rounded-lg border border-warning/40 bg-warning/10 p-2 text-sm"
        >
          {warnings.map((w) => (
            <li key={w} className="flex gap-2">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
              <span>{w}</span>
            </li>
          ))}
        </ul>
      )}

      <Table className="min-w-[660px]">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-12 px-2">Apply</TableHead>
            <TableHead className="px-2">Field</TableHead>
            <TableHead className="px-2">Found value</TableHead>
            <TableHead className="px-2">In the form now</TableHead>
            <TableHead className="px-2">Confidence</TableHead>
            <TableHead className="px-2">Replace</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => {
            const effect = rowEffect(row, values, options);
            const current = currentInfo(row, values, options);
            const problem = row.found ? rowProblem(row) : null;
            const canTick = row.found && effect !== "none";
            return (
              <TableRow
                key={row.key}
                data-testid={`quick-fill-row-${row.key}`}
                className="align-top"
              >
                <TableCell className="px-2 py-2">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-input"
                    aria-label={`Apply ${row.label}`}
                    data-testid={`quick-fill-check-${row.key}`}
                    checked={row.checked && canTick}
                    disabled={!canTick}
                    onChange={(e) => onRowChange(row.key, { checked: e.target.checked })}
                  />
                </TableCell>
                <TableCell className="px-2 py-2 font-medium">{row.label}</TableCell>
                <TableCell className="px-2 py-2">
                  {row.found ? (
                    <div className="space-y-1.5">
                      <ValueEditor
                        row={row}
                        options={options}
                        problem={problem}
                        onRowChange={onRowChange}
                        onPick={onPick}
                      />
                      {problem && (
                        <p role="alert" className="text-xs text-destructive">
                          {problem}
                        </p>
                      )}
                      {!row.needsChoice && row.candidates.length > 0 && row.kind !== "source" && (
                        <div
                          className="flex flex-wrap gap-1"
                          aria-label={`${row.label}: other readings`}
                        >
                          {row.candidates.map((c, index) => (
                            <button
                              key={`${c.reason}-${index}`}
                              type="button"
                              aria-pressed={sameReading(row, c)}
                              onClick={() => onPick(row.key, index)}
                              className="rounded-full border border-border/70 px-2 py-0.5 text-xs hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-pressed:border-primary aria-pressed:bg-primary/10"
                            >
                              {c.reason.replace(/ \(filled\)$/, "")}: {c.display}
                            </button>
                          ))}
                        </div>
                      )}
                      <p className="text-xs text-muted-foreground">{row.reason}</p>
                      {row.warning && (
                        <p
                          className="text-xs text-warning"
                          data-testid={`quick-fill-warning-${row.key}`}
                        >
                          {row.warning}
                        </p>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm text-muted-foreground">Not found</span>
                  )}
                </TableCell>
                <TableCell className="px-2 py-2 text-sm">
                  {current.display || <span className="text-muted-foreground">Empty</span>}
                </TableCell>
                <TableCell className="px-2 py-2">
                  {row.confidence ? (
                    <Badge
                      variant={CONFIDENCE_VARIANT[row.confidence]}
                      data-testid={`quick-fill-confidence-${row.key}`}
                    >
                      {confidenceLabel(row.confidence)}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell className="px-2 py-2 text-sm">
                  {effect === "conflict" ? (
                    <label className="flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-input"
                        aria-label={`Replace current ${row.label}`}
                        data-testid={`quick-fill-replace-${row.key}`}
                        checked={row.replace}
                        onChange={(e) => onRowChange(row.key, { replace: e.target.checked })}
                      />
                      Replace
                    </label>
                  ) : effect === "same" ? (
                    <span className="text-muted-foreground">Already there</span>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      {ignored.length > 0 && (
        <p className="text-xs text-muted-foreground" data-testid="quick-fill-ignored">
          Not understood (left out): {ignored.map((piece) => `“${piece}”`).join(", ")}
        </p>
      )}

      <div className="flex flex-wrap items-center justify-end gap-2">
        <span className="mr-auto text-xs text-muted-foreground">
          {selectable} found · {ticked} ticked
        </span>
        <Button type="button" variant="ghost" onClick={onCancel} data-testid="quick-fill-cancel">
          Cancel
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={onApplyHighConfidence}
          disabled={highReady === 0}
          data-testid="quick-fill-apply-high"
        >
          Apply all high confidence
        </Button>
        <Button
          type="button"
          onClick={onApplySelected}
          disabled={ticked === 0}
          data-testid="quick-fill-apply-selected"
        >
          Apply selected
        </Button>
      </div>
    </section>
  );
}
