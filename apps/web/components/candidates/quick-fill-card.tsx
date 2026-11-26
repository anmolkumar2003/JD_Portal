"use client";

import { ChevronDown, History, Loader2, Sparkles } from "lucide-react";
import { useId, useMemo, useState } from "react";
import { useFormContext, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { QuickFillPreview } from "@/components/candidates/quick-fill-preview";
import { Textarea } from "@/components/ui/textarea";
import { useDepartments } from "@/hooks/use-lookups";
import { useQuickParse } from "@/hooks/use-quick-parse";
import { ApiError } from "@/lib/api";
import {
  buildRows,
  isHighConfidenceApplicable,
  pickCandidate,
  type FormValuesLike,
  type NamedOption,
  type PreviewRow,
  type QuickFillOptions,
} from "@/lib/quick-fill";
import { cn } from "@/lib/utils";
import type { CandidateSource, QuickFillFieldName, QuickParseOut } from "@/types/api";

/** Same limit as the API; the box stops accepting more so the request is never rejected. */
export const QUICK_FILL_MAX_CHARS = 2000;
/** How many earlier entries the on-page history keeps (this page only, never sent anywhere). */
const HISTORY_LIMIT = 5;

export const QUICK_FILL_PLACEHOLDER =
  "Rahul Sharma, Pune, 5 years, current 8 LPA, expected 12 LPA, 30 days notice, rahul@mail.com";

function snippet(text: string): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > 60 ? `${flat.slice(0, 57)}...` : flat;
}

const DEFAULT_SOURCES = ["manual", "referral", "linkedin", "agency"] as const;

interface QuickFillCardProps {
  /** The Add form starts open; the edit dialog starts closed to keep the form in view. */
  defaultOpen?: boolean;
  /** Jobs the form can pick from. Omit (null) when the form has no job picker. */
  jobs?: NamedOption[] | null;
  /** The department follows the selected job and cannot be filled by hand. */
  departmentLocked?: boolean;
  /** Sources the form's Source select offers. */
  sources?: readonly CandidateSource[];
}

export function QuickFillCard({
  defaultOpen = true,
  jobs = null,
  departmentLocked = false,
  sources = DEFAULT_SOURCES,
}: QuickFillCardProps) {
  const uid = useId();
  const panelId = `${uid}-panel`;
  const [open, setOpen] = useState(defaultOpen);
  const [text, setText] = useState("");
  // Session-only: lives in this component's state, so it is gone on reload or navigation.
  const [history, setHistory] = useState<string[]>([]);
  const [result, setResult] = useState<QuickParseOut | null>(null);
  const [rows, setRows] = useState<PreviewRow[] | null>(null);
  const parse = useQuickParse();
  const departments = useDepartments();
  const { control } = useFormContext();
  const values = useWatch({ control }) as FormValuesLike;

  const options: QuickFillOptions = useMemo(
    () => ({
      departments: (departments.data ?? []).map((d) => ({ id: d.id, name: d.name })),
      jobs,
      sources,
      departmentLocked,
    }),
    [departments.data, jobs, sources, departmentLocked],
  );

  const trimmed = text.trim();

  const extract = () => {
    if (!trimmed) {
      toast.error("Paste or type some candidate details first");
      return;
    }
    parse.mutate(trimmed, {
      onSuccess: (data) => {
        setResult(data);
        setRows(buildRows(data, options));
        setHistory((prev) =>
          [trimmed, ...prev.filter((h) => h !== trimmed)].slice(0, HISTORY_LIMIT),
        );
      },
      onError: (error: unknown) => {
        setResult(null);
        setRows(null);
        toast.error(error instanceof ApiError ? error.message : "Could not read that text");
      },
    });
  };

  const patchRow = (key: QuickFillFieldName, patch: Partial<PreviewRow>) =>
    setRows((prev) => prev?.map((r) => (r.key === key ? { ...r, ...patch } : r)) ?? prev);

  const cancelPreview = () => {
    setRows(null);
    setResult(null);
  };

  // Step 5 wires these to the form.
  const applySelected = () => toast.info("Applying is added in the next step");
  const applyHigh = () => {
    if (rows?.some(isHighConfidenceApplicable)) toast.info("Applying is added in the next step");
  };

  return (
    <Card data-testid="quick-fill-card">
      <CardHeader className="p-4 pb-2">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between gap-3 rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" aria-hidden />
            <CardTitle className="text-base">Quick fill</CardTitle>
          </span>
          <ChevronDown
            className={cn(
              "h-4 w-4 text-muted-foreground transition-transform",
              open && "rotate-180",
            )}
            aria-hidden
          />
        </button>
        {open && (
          <CardDescription>
            Paste a few lines or a sentence. Nothing is saved until you click Save.
          </CardDescription>
        )}
      </CardHeader>
      {/* Kept mounted while collapsed so the typed text and history survive a collapse. */}
      <CardContent id={panelId} hidden={!open} className="space-y-3 p-4 pt-2">
        <label htmlFor={`${uid}-text`} className="sr-only">
          Candidate details to extract
        </label>
        <Textarea
          id={`${uid}-text`}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={QUICK_FILL_PLACEHOLDER}
          maxLength={QUICK_FILL_MAX_CHARS}
          rows={4}
          spellCheck={false}
          autoComplete="off"
        />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs text-muted-foreground" aria-live="polite">
            {text.length}/{QUICK_FILL_MAX_CHARS}
          </span>
          <Button
            type="button"
            onClick={extract}
            disabled={parse.isPending || !trimmed}
            data-testid="quick-fill-extract"
          >
            {parse.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
            Extract
          </Button>
        </div>

        {history.length > 0 && (
          <div className="space-y-1.5" data-testid="quick-fill-history">
            <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
              <History className="h-3 w-3" aria-hidden /> Recent entries (this page only)
            </p>
            <ul className="flex flex-wrap gap-2">
              {history.map((entry) => (
                <li key={entry}>
                  <button
                    type="button"
                    title={entry}
                    onClick={() => setText(entry)}
                    className="max-w-[16rem] truncate rounded-full border border-border/70 bg-background/60 px-3 py-1 text-xs hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {snippet(entry)}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {result && rows && (
          <QuickFillPreview
            rows={rows}
            values={values}
            options={options}
            warnings={result.warnings}
            ignored={result.ignored}
            truncated={result.truncated}
            onRowChange={patchRow}
            onPick={(key, index) =>
              setRows((prev) => (prev ? pickCandidate(prev, key, index) : prev))
            }
            onApplySelected={applySelected}
            onApplyHighConfidence={applyHigh}
            onCancel={cancelPreview}
          />
        )}
      </CardContent>
    </Card>
  );
}
