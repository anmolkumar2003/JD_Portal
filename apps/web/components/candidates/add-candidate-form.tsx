"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent,
  type ReactNode,
} from "react";
import { FormProvider, useForm, type FieldPath } from "react-hook-form";
import { toast } from "sonner";

import {
  EMPTY_CANDIDATE_FORM,
  buildCommitRow,
  buildCreateFormData,
  candidateFormSchema,
  rowErrors,
  type AutofillKey,
  type CandidateFormValues,
} from "@/components/candidates/candidate-form-schema";
import { BudgetBadge } from "@/components/candidates/budget-badge";
import { MultiCvDropzone, type CvUploadItem } from "@/components/candidates/cv-dropzone";
import { QuickFillCard } from "@/components/candidates/quick-fill-card";
import { SalaryFields } from "@/components/candidates/salary-fields";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useAuth } from "@/hooks/use-auth";
import { applicationKeys } from "@/hooks/use-applications";
import { useJob, useJobs } from "@/hooks/use-jobs";
import { useDepartments } from "@/hooks/use-lookups";
import { ApiError, api } from "@/lib/api";
import { CANDIDATE_SOURCE_LABELS } from "@/lib/labels";
import { isAdmin } from "@/lib/permissions";
import { computeBudgetStatus } from "@/lib/salary";
import type {
  CommitRowError,
  CvParseOut,
  DraftCommitMode,
  DraftCommitRowOut,
  JobListItem,
  RowIssue,
} from "@/types/api";

function draftKey(userId: string): string {
  return `add-candidate-draft:${userId}`;
}

const FIELD_LABELS: Record<string, string> = {
  first_name: "first name",
  last_name: "last name",
  email: "email",
  phone: "phone",
  job_id: "job",
};

function FromCvBadge({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <Badge variant="secondary" className="ml-2 align-middle text-[10px] font-normal">
      from CV
    </Badge>
  );
}

function Field({
  id,
  label,
  fromCv,
  error,
  required,
  children,
}: {
  id: string;
  label: string;
  fromCv?: boolean;
  error?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>
        {/* The asterisk is CSS-only so the accessible label text stays "First name". */}
        <span className={required ? "after:ml-0.5 after:text-destructive after:content-['*']" : ""}>
          {label}
        </span>
        <FromCvBadge show={Boolean(fromCv)} />
      </Label>
      {children}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

function parseToFormPatch(data: CvParseOut): Partial<CandidateFormValues> {
  const patch: Partial<CandidateFormValues> = {};
  if (data.first_name) patch.first_name = data.first_name;
  if (data.last_name) patch.last_name = data.last_name;
  if (data.email) patch.email = data.email;
  if (data.phone) patch.phone = data.phone;
  if (data.current_location) patch.current_location = data.current_location;
  if (data.current_company) patch.current_company = data.current_company;
  if (data.current_title) patch.current_title = data.current_title;
  if (data.total_experience_years != null) {
    patch.total_experience_years = String(data.total_experience_years);
  }
  if (data.linkedin_url) patch.linkedin_url = data.linkedin_url;
  return patch;
}

type BatchRow = {
  itemId: string;
  fileName: string;
  draftFileId: string | null;
  values: CandidateFormValues;
  autofill: Set<AutofillKey>;
  /** True once the parsed CV fields have been merged into `values`. */
  seeded: boolean;
  /** Errors the server reported for this row on the last save attempt. */
  serverIssues: RowIssue[];
};

type SaveOutcome = { link: string; reused: boolean; referenceNo: string | null };

function focusFirstInvalid(): void {
  window.setTimeout(() => {
    const el = document.querySelector<HTMLElement>('[aria-invalid="true"]');
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.focus({ preventScroll: true });
  }, 60);
}

function isCommitRowErrors(details: unknown): details is CommitRowError[] {
  return (
    Array.isArray(details) &&
    details.every(
      (d) => typeof d === "object" && d !== null && "field" in d && "message" in d && "row" in d,
    )
  );
}

/** Field errors from `POST /candidates` (FastAPI style: loc = ["body", field]). */
function manualFieldErrors(details: unknown): { field: string; message: string }[] {
  if (!Array.isArray(details)) return [];
  const out: { field: string; message: string }[] = [];
  for (const d of details as unknown[]) {
    if (typeof d !== "object" || d === null) continue;
    const loc = (d as { loc?: unknown }).loc;
    const msg = (d as { msg?: unknown }).msg;
    if (Array.isArray(loc) && typeof loc[1] === "string" && typeof msg === "string") {
      out.push({ field: loc[1], message: msg });
    }
  }
  return out;
}

function linkOf(candidateId: string, applicationId: string | null): string {
  return applicationId
    ? `/candidates/${candidateId}?application=${applicationId}`
    : `/candidates/${candidateId}`;
}

interface AddCandidateFormProps {
  sharedJobId?: string;
  sharedDepartmentId?: string;
}

export function AddCandidateForm({ sharedJobId, sharedDepartmentId }: AddCandidateFormProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const departments = useDepartments();
  const jobs = useJobs({ page_size: 100, sort: "-created_at" });
  const [cvItems, setCvItems] = useState<CvUploadItem[]>([]);
  const [parsedByItem, setParsedByItem] = useState<Record<string, CvParseOut>>({});
  const [autofillKeys, setAutofillKeys] = useState<Set<AutofillKey>>(new Set());
  const [batchRows, setBatchRows] = useState<BatchRow[]>([]);
  const [attempted, setAttempted] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [debouncedEmail, setDebouncedEmail] = useState("");
  const [debouncedPhone, setDebouncedPhone] = useState("");
  const [duplicateConfirm, setDuplicateConfirm] = useState(false);
  const parsingRef = useRef<Set<string>>(new Set());
  const singleSeededRef = useRef<Set<string>>(new Set());
  const autofillRef = useRef<Set<AutofillKey>>(autofillKeys);
  const batchRowsRef = useRef<BatchRow[]>([]);
  const restoredRef = useRef(false);
  const confirmedEmailRef = useRef<string | null>(null);
  const duplicateBannerRef = useRef<HTMLDivElement>(null);
  // The draft is created on the first drop and shared by every file dropped after it.
  const draftPromiseRef = useRef<Promise<string> | null>(null);
  const draftIdRef = useRef<string | null>(null);

  const form = useForm<CandidateFormValues>({
    resolver: zodResolver(candidateFormSchema),
    defaultValues: {
      ...EMPTY_CANDIDATE_FORM,
      job_id: sharedJobId ?? "",
      department_id: sharedDepartmentId ?? "",
    },
  });

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    reset,
    formState: { errors, isDirty, dirtyFields },
  } = form;

  const values = watch();
  const jobId = values.job_id;
  const jobDetail = useJob(jobId || "");
  const jobItems: JobListItem[] = useMemo(() => jobs.data?.items ?? [], [jobs.data]);
  const jobDepartment = jobItems.find((j) => j.id === jobId)?.department ?? null;

  const isBatchMode = cvItems.filter((i) => i.status !== "error").length > 1;
  const uploading = cvItems.some((i) => i.status === "ready" || i.status === "parsing");
  const readyItem = cvItems.find((i) => i.status === "done" && i.draftFileId);
  // Drag-drop flow: dropping files means a CV is expected. If every file failed, Save stays off
  // until a valid CV is added (or the failed files are removed to enter the details by hand).
  const cvBlocked = cvItems.length > 0 && !readyItem;
  const formValid = useMemo(() => candidateFormSchema.safeParse(values).success, [values]);
  const hasUnsaved = isDirty || cvItems.some((i) => i.status !== "error") || batchRows.length > 0;

  useEffect(() => {
    autofillRef.current = autofillKeys;
  }, [autofillKeys]);

  useEffect(() => {
    batchRowsRef.current = batchRows;
  }, [batchRows]);

  // --- Draft lifecycle -----------------------------------------------------------------------

  const ensureDraft = useCallback((): Promise<string> => {
    draftPromiseRef.current ??= api.candidates
      .createDraft()
      .then((draft) => {
        draftIdRef.current = draft.id;
        return draft.id;
      })
      .catch((error: unknown) => {
        draftPromiseRef.current = null;
        throw error;
      });
    return draftPromiseRef.current;
  }, []);

  /** The server already deleted the draft (fully committed): just forget it. */
  const forgetDraft = useCallback(() => {
    draftPromiseRef.current = null;
    draftIdRef.current = null;
  }, []);

  /** Cancel/leave: delete the draft and its stored CVs. Best effort; the 24h expiry backs it. */
  const discardDraft = useCallback((keepalive: boolean) => {
    const pending = draftPromiseRef.current;
    const id = draftIdRef.current;
    draftPromiseRef.current = null;
    draftIdRef.current = null;
    if (id) {
      void api.candidates.deleteDraft(id, { keepalive }).catch(() => undefined);
    } else if (pending) {
      void pending
        .then((newId) => api.candidates.deleteDraft(newId, { keepalive }))
        .catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    const onPageHide = () => discardDraft(true);
    window.addEventListener("pagehide", onPageHide);
    return () => {
      window.removeEventListener("pagehide", onPageHide);
      // In-app navigation away from the page (not a save: saving forgets the draft first).
      discardDraft(true);
    };
  }, [discardDraft]);

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsaved) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [hasUnsaved]);

  // --- Local draft of the form fields (survives a reload) ------------------------------------

  useEffect(() => {
    if (!user?.id || restoredRef.current) return;
    restoredRef.current = true;
    try {
      const raw = localStorage.getItem(draftKey(user.id));
      if (!raw) return;
      const parsed = JSON.parse(raw) as CandidateFormValues;
      reset({ ...EMPTY_CANDIDATE_FORM, ...parsed });
    } catch {
      /* ignore corrupt draft */
    }
  }, [user?.id, reset]);

  useEffect(() => {
    if (!user?.id) return;
    const id = window.setInterval(() => {
      try {
        localStorage.setItem(draftKey(user.id), JSON.stringify(values));
      } catch {
        /* quota */
      }
    }, 3000);
    return () => window.clearInterval(id);
  }, [user?.id, values]);

  // Department follows the job (the API does the same); shown read-only when the job has one.
  useEffect(() => {
    if (jobDepartment) setValue("department_id", jobDepartment.id);
  }, [jobDepartment, setValue]);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedEmail(values.email.trim()), 450);
    return () => window.clearTimeout(t);
  }, [values.email]);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedPhone(values.phone.trim()), 450);
    return () => window.clearTimeout(t);
  }, [values.phone]);

  const duplicates = useQuery({
    queryKey: ["candidates", "duplicates", debouncedEmail, debouncedPhone],
    queryFn: () =>
      api.candidates.duplicates({
        email: debouncedEmail || undefined,
        phone: debouncedPhone || undefined,
      }),
    enabled: Boolean(debouncedEmail.length >= 3 || debouncedPhone.length >= 6),
  });

  // --- Dropped CVs: upload to the draft, never create a candidate ---------------------------

  const runUpload = useCallback(
    async (item: CvUploadItem) => {
      if (parsingRef.current.has(item.id)) return;
      parsingRef.current.add(item.id);
      setCvItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, status: "parsing" } : i)));
      try {
        const draftId = await ensureDraft();
        const data = await api.candidates.uploadDraftFile(draftId, item.file);
        setParsedByItem((prev) => ({ ...prev, [item.id]: data }));
        setCvItems((prev) =>
          prev.map((i) =>
            i.id === item.id ? { ...i, status: "done", draftFileId: data.draft_file_id } : i,
          ),
        );
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "Could not upload this CV";
        setCvItems((prev) =>
          prev.map((i) => (i.id === item.id ? { ...i, status: "error", error: message } : i)),
        );
      } finally {
        parsingRef.current.delete(item.id);
      }
    },
    [ensureDraft],
  );

  useEffect(() => {
    for (const item of cvItems.filter((i) => i.status === "ready")) {
      void runUpload(item);
    }
  }, [cvItems, runUpload]);

  // Single CV: prefill the form (fields the user already typed are left alone). B2.
  useEffect(() => {
    if (isBatchMode) return;
    const item = cvItems.find((i) => i.status === "done");
    const data = item ? parsedByItem[item.id] : undefined;
    if (!item || !data || singleSeededRef.current.has(item.id)) return;
    singleSeededRef.current.add(item.id);
    const patch = parseToFormPatch(data);
    const added: AutofillKey[] = [];
    (Object.keys(patch) as AutofillKey[]).forEach((key) => {
      if (dirtyFields[key]) return;
      const value = patch[key];
      if (value !== undefined) {
        setValue(key, value as string, { shouldDirty: false, shouldValidate: attempted });
        added.push(key);
      }
    });
    setAutofillKeys((prev) => new Set([...prev, ...added]));
  }, [attempted, cvItems, dirtyFields, isBatchMode, parsedByItem, setValue]);

  useEffect(() => {
    if (!isBatchMode && cvItems.length === 0) setAutofillKeys(new Set());
  }, [cvItems.length, isBatchMode]);

  // Several CVs: one review row per file.
  useEffect(() => {
    if (!isBatchMode) {
      const last = batchRowsRef.current;
      const [only] = last;
      if (last.length === 1 && only && cvItems.some((i) => i.id === only.itemId)) {
        // Back to one file (others removed or saved): keep what was typed in its review row.
        reset({ ...only.values });
        if (only.seeded) singleSeededRef.current.add(only.itemId);
        setAutofillKeys(new Set(only.autofill));
      }
      if (last.length) setBatchRows([]);
      return;
    }
    const valid = cvItems.filter((i) => i.status !== "error");
    setBatchRows((prev) => {
      const byId = new Map(prev.map((r) => [r.itemId, r]));
      return valid.map((item) => {
        let row = byId.get(item.id);
        if (!row) {
          const fromForm = prev.length === 0 && valid[0]?.id === item.id;
          const alreadyApplied = singleSeededRef.current.has(item.id);
          row = {
            itemId: item.id,
            fileName: item.file.name,
            draftFileId: item.draftFileId ?? null,
            values: fromForm
              ? form.getValues()
              : {
                  ...EMPTY_CANDIDATE_FORM,
                  job_id: form.getValues("job_id") || sharedJobId || "",
                  department_id: sharedDepartmentId ?? "",
                },
            autofill: fromForm ? new Set(autofillRef.current) : new Set(),
            seeded: fromForm && alreadyApplied,
            serverIssues: [],
          };
        }
        const data = parsedByItem[item.id];
        if (!row.seeded && data) {
          const patch = parseToFormPatch(data);
          const nextValues = { ...row.values };
          const autofill = new Set(row.autofill);
          (Object.keys(patch) as AutofillKey[]).forEach((k) => {
            if (patch[k] !== undefined && !String(nextValues[k] ?? "").trim()) {
              nextValues[k] = patch[k] as string;
              autofill.add(k);
            }
          });
          row = { ...row, values: nextValues, autofill, seeded: true };
        }
        return row.draftFileId === (item.draftFileId ?? null)
          ? row
          : { ...row, draftFileId: item.draftFileId ?? null };
      });
    });
  }, [cvItems, form, isBatchMode, parsedByItem, reset, sharedDepartmentId, sharedJobId]);

  const jobMax = jobDetail.data?.salary_max ? Number(jobDetail.data.salary_max) : null;
  const expectedAmount = values.expected_ctc.amount.trim()
    ? Number(values.expected_ctc.amount)
    : null;
  const previewBudget = computeBudgetStatus(expectedAmount, values.expected_ctc.unit, jobMax);

  // --- Saving ---------------------------------------------------------------------------------

  const finishSave = useCallback(
    (outcomes: SaveOutcome[], candidateIds: string[]) => {
      if (user?.id) localStorage.removeItem(draftKey(user.id));
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
      void queryClient.invalidateQueries({ queryKey: ["candidates"] });
      if (outcomes.length === 1) {
        const [only] = outcomes;
        if (!only) return;
        toast.success(only.reused ? "Existing candidate updated" : "Candidate saved", {
          description: only.referenceNo ? `Ref ${only.referenceNo}` : undefined,
          action: { label: "View candidate", onClick: () => router.push(only.link) },
          duration: 10_000,
        });
        router.push(only.link);
        return;
      }
      const updated = outcomes.filter((o) => o.reused).length;
      toast.success(`Saved ${outcomes.length} candidates`, {
        description: (
          <span className="flex flex-col gap-1">
            {outcomes.slice(0, 5).map((o, index) => (
              <Link
                key={candidateIds[index] ?? o.link}
                href={o.link}
                className="underline underline-offset-2"
              >
                View candidate {index + 1}
              </Link>
            ))}
            {outcomes.length > 5 && <span>and {outcomes.length - 5} more in Candidates</span>}
            {updated > 0 && <span>{updated} matched an existing email and was updated.</span>}
          </span>
        ),
        duration: 15_000,
      });
      router.push("/candidates");
    },
    [queryClient, router, user?.id],
  );

  const applyServerFieldErrors = useCallback(
    (items: { field: string; message: string }[]): boolean => {
      let applied = false;
      for (const item of items) {
        if (item.field in EMPTY_CANDIDATE_FORM) {
          setError(item.field as FieldPath<CandidateFormValues>, {
            type: "server",
            message: item.message,
          });
          applied = true;
        }
      }
      if (applied) focusFirstInvalid();
      return applied;
    },
    [setError],
  );

  const saveMutation = useMutation({
    mutationFn: async (data: CandidateFormValues): Promise<SaveOutcome> => {
      const draftId = draftIdRef.current;
      if (readyItem?.draftFileId && draftId) {
        const result = await api.candidates.commitDraft(draftId, {
          mode: "all",
          rows: [buildCommitRow(data, readyItem.draftFileId)],
        });
        const saved = result.results.find((r) => r.status === "saved");
        if (!saved?.candidate_id) {
          throw new ApiError(
            422,
            "validation_error",
            result.results[0]?.issues[0]?.message ?? "Could not save",
          );
        }
        if (result.draft_deleted) forgetDraft();
        else discardDraft(false); // other (removed) files may linger in the draft
        return {
          link: saved.link ?? linkOf(saved.candidate_id, saved.application_id),
          reused: saved.reused,
          referenceNo: saved.reference_no,
        };
      }
      const created = await api.candidates.create(buildCreateFormData(data, null));
      return {
        link: linkOf(created.candidate_id, created.application_id),
        reused: created.reused,
        referenceNo: created.reference_no,
      };
    },
    onSuccess: (outcome) => finishSave([outcome], []),
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.status === 422) {
        const fromCommit = isCommitRowErrors(error.details) ? error.details : [];
        const fields = [...fromCommit, ...manualFieldErrors(error.details)];
        if (applyServerFieldErrors(fields)) {
          toast.error("Fix the highlighted fields");
          return;
        }
      }
      toast.error(error instanceof ApiError ? error.message : "Could not save candidate");
    },
  });

  const canSaveSingle =
    formValid && !uploading && !cvBlocked && !committing && !saveMutation.isPending;

  const submitSingle = useCallback(
    async (data: CandidateFormValues) => {
      if (uploading) {
        toast.info("Wait for the CV to finish uploading");
        return;
      }
      if (cvBlocked) {
        toast.error("Add a valid CV, or remove the failed files to enter details by hand");
        return;
      }
      // B4 at save: an email match means saving updates that existing candidate, so ask first.
      const email = data.email.trim().toLowerCase();
      if (confirmedEmailRef.current !== email) {
        try {
          const found = await api.candidates.duplicates({
            email: data.email.trim(),
            phone: data.phone.trim(),
          });
          if (found.matches.some((m) => m.matched_on.includes("email"))) {
            setDuplicateConfirm(true);
            toast.warning("A candidate with this email already exists");
            window.setTimeout(
              () => duplicateBannerRef.current?.scrollIntoView({ behavior: "smooth" }),
              60,
            );
            return;
          }
        } catch {
          /* the check is advisory; the server still reuses by email */
        }
      }
      setDuplicateConfirm(false);
      saveMutation.mutate(data);
    },
    [cvBlocked, saveMutation, uploading],
  );

  const onSaveSingle = handleSubmit(submitSingle, () => {
    setAttempted(true);
    focusFirstInvalid();
  });

  const confirmDuplicateAndSave = () => {
    confirmedEmailRef.current = values.email.trim().toLowerCase();
    setDuplicateConfirm(false);
    void onSaveSingle();
  };

  // --- Batch (review table) -------------------------------------------------------------------

  const rowStates = useMemo(
    () =>
      batchRows.map((row) => {
        const errs = rowErrors(row.values);
        const parsing = cvItems.find((i) => i.id === row.itemId)?.status !== "done";
        return { row, errs, complete: Object.keys(errs).length === 0, parsing };
      }),
    [batchRows, cvItems],
  );
  const completeCount = rowStates.filter((r) => r.complete && !r.parsing).length;
  const allComplete = rowStates.length > 0 && rowStates.every((r) => r.complete && !r.parsing);

  const commitBatch = async (mode: DraftCommitMode) => {
    setAttempted(true);
    const draftId = draftIdRef.current;
    if (!draftId) return;
    const sendable = rowStates.filter((r) =>
      mode === "all" ? true : r.complete && !r.parsing && r.row.draftFileId,
    );
    if (mode === "all" && !allComplete) {
      toast.error("Complete every row before using Save all");
      focusFirstInvalid();
      return;
    }
    if (sendable.length === 0) {
      toast.error("No complete rows to save yet");
      return;
    }
    setCommitting(true);
    try {
      const result = await api.candidates.commitDraft(draftId, {
        mode,
        rows: sendable.map((r) => buildCommitRow(r.row.values, r.row.draftFileId)),
      });
      const savedRows: { item: string; out: DraftCommitRowOut }[] = [];
      const issuesByItem = new Map<string, RowIssue[]>();
      for (const out of result.results) {
        const source = sendable[out.index]?.row;
        if (!source) continue;
        if (out.status === "saved") savedRows.push({ item: source.itemId, out });
        else issuesByItem.set(source.itemId, out.issues);
      }
      const savedItemIds = new Set(savedRows.map((s) => s.item));
      setBatchRows((prev) =>
        prev
          .filter((r) => !savedItemIds.has(r.itemId))
          .map((r) => ({ ...r, serverIssues: issuesByItem.get(r.itemId) ?? [] })),
      );
      setCvItems((prev) => prev.filter((i) => !savedItemIds.has(i.id)));
      if (result.draft_deleted) forgetDraft();

      const outcomes: SaveOutcome[] = savedRows.map(({ out }) => ({
        link: out.link ?? (out.candidate_id ? linkOf(out.candidate_id, out.application_id) : ""),
        reused: out.reused,
        referenceNo: out.reference_no,
      }));
      const remaining = rowStates.length - savedRows.length;
      if (outcomes.length > 0 && remaining === 0) {
        if (!result.draft_deleted) discardDraft(false);
        finishSave(
          outcomes,
          savedRows.map((s) => s.out.candidate_id ?? ""),
        );
      } else if (outcomes.length > 0) {
        void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
        const [firstSaved] = outcomes;
        toast.success(
          `Saved ${outcomes.length} candidate${outcomes.length === 1 ? "" : "s"}; ${remaining} still ${remaining === 1 ? "needs" : "need"} attention`,
          {
            action: firstSaved
              ? { label: "View candidate", onClick: () => router.push(firstSaved.link) }
              : undefined,
            duration: 12_000,
          },
        );
      } else {
        toast.error("Nothing was saved. Check the highlighted rows.");
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 422 && isCommitRowErrors(error.details)) {
        const byIndex = new Map<string, RowIssue[]>();
        for (const detail of error.details) {
          const itemId = sendable[detail.row]?.row.itemId;
          if (!itemId) continue;
          byIndex.set(itemId, [
            ...(byIndex.get(itemId) ?? []),
            { field: detail.field, message: detail.message },
          ]);
        }
        setBatchRows((prev) =>
          prev.map((r) => ({ ...r, serverIssues: byIndex.get(r.itemId) ?? [] })),
        );
        toast.error(error.message);
      } else {
        toast.error(error instanceof ApiError ? error.message : "Could not save candidates");
      }
    } finally {
      setCommitting(false);
    }
  };

  const updateBatchField = (itemId: string, key: keyof CandidateFormValues, value: string) => {
    setBatchRows((prev) =>
      prev.map((row) =>
        row.itemId === itemId
          ? {
              ...row,
              values: { ...row.values, [key]: value },
              autofill: new Set([...row.autofill].filter((k) => k !== key)),
              serverIssues: row.serverIssues.filter((i) => i.field !== key),
            }
          : row,
      ),
    );
  };

  const applyJobToAll = (nextJobId: string) => {
    setBatchRows((prev) =>
      prev.map((row) => ({ ...row, values: { ...row.values, job_id: nextJobId } })),
    );
    setValue("job_id", nextJobId);
  };

  // --- Cancel ---------------------------------------------------------------------------------

  const cancelAll = () => {
    if (user?.id) localStorage.removeItem(draftKey(user.id));
    discardDraft(false);
    reset(EMPTY_CANDIDATE_FORM);
    setCvItems([]);
    setParsedByItem({});
    setBatchRows([]);
    setAutofillKeys(new Set());
    singleSeededRef.current = new Set();
    confirmedEmailRef.current = null;
    setDuplicateConfirm(false);
    setAttempted(false);
  };

  const onCancel = () => {
    if (
      hasUnsaved &&
      !window.confirm(
        "Discard this candidate? Anything you entered and any uploaded CVs are deleted.",
      )
    ) {
      return;
    }
    cancelAll();
    router.push("/candidates");
  };

  const duplicateWarning = useMemo(() => {
    const matches = duplicates.data?.matches ?? [];
    return matches.length > 0 ? matches : null;
  }, [duplicates.data]);

  const onSaveClick = (event: MouseEvent<HTMLButtonElement>) => {
    // The button looks disabled (aria-disabled) while incomplete but stays clickable so the
    // click can scroll to the first problem instead of doing nothing.
    if (!canSaveSingle) {
      event.preventDefault();
      setAttempted(true);
      if (!formValid) {
        void form.trigger().then(() => focusFirstInvalid());
      } else if (uploading) {
        toast.info("Wait for the CV to finish uploading");
      } else if (cvBlocked) {
        toast.error("Add a valid CV, or remove the failed files to enter details by hand");
      }
    }
  };

  const showErrors = attempted || undefined;
  const cvAlert = cvBlocked && !uploading;

  return (
    <FormProvider {...form}>
      <form onSubmit={onSaveSingle} noValidate className="space-y-6">
        {/* Quick fill is HR-admin only (the API enforces it too) and is for one candidate. */}
        {isAdmin(user?.role) && !isBatchMode && <QuickFillCard />}

        <Card>
          <CardHeader>
            <CardTitle>CV upload</CardTitle>
            <CardDescription>
              Drop one CV to prefill the form, or several to review and save in bulk. Nothing is
              saved until you click Save.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <MultiCvDropzone items={cvItems} onChange={setCvItems} />
            {cvAlert && (
              <p role="alert" className="text-sm text-destructive">
                No CV was uploaded successfully. Add a valid PDF or DOCX, or remove the failed files
                to enter the details by hand.
              </p>
            )}
          </CardContent>
        </Card>

        {(duplicateWarning || duplicateConfirm) && !isBatchMode && (
          <div
            ref={duplicateBannerRef}
            role="status"
            data-testid="duplicate-warning"
            className="flex gap-3 rounded-lg border border-warning/40 bg-warning/10 p-4 text-sm"
          >
            <AlertTriangle className="h-5 w-5 shrink-0 text-warning" aria-hidden />
            <div className="space-y-2">
              <p className="font-medium">Possible duplicate</p>
              <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                {(duplicateWarning ?? []).map((m) => (
                  <li key={m.id}>
                    <Link
                      href={`/candidates/${m.id}`}
                      className="font-medium text-foreground underline underline-offset-2 hover:text-primary"
                    >
                      {m.first_name} {m.last_name}
                    </Link>{" "}
                    ({m.email})
                    {m.matched_on.length > 0 && ` — matched on ${m.matched_on.join(", ")}`}
                  </li>
                ))}
              </ul>
              {duplicateConfirm && (
                <div className="space-y-2">
                  <p>
                    Saving will update this existing candidate with the details below and add the
                    application.
                  </p>
                  <Button type="button" size="sm" onClick={confirmDuplicateAndSave}>
                    Save anyway
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}

        {isBatchMode ? (
          <Card>
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-4">
              <div>
                <CardTitle>Review uploads</CardTitle>
                <CardDescription>
                  One row per CV. Every row needs first name, last name, email, phone and a job.
                </CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  disabled={completeCount === 0 || committing}
                  onClick={() => void commitBatch("complete_only")}
                >
                  Save complete rows
                  {completeCount > 0 && ` (${completeCount})`}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={!allComplete || committing}
                  onClick={() => void commitBatch("all")}
                >
                  {committing && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
                  Save all
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 overflow-x-auto">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <Label htmlFor="batch-job-all">Job for all rows</Label>
                <Select
                  id="batch-job-all"
                  className="w-64"
                  value=""
                  onChange={(e) => e.target.value && applyJobToAll(e.target.value)}
                >
                  <option value="">Choose a job…</option>
                  {jobItems.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title}
                    </option>
                  ))}
                </Select>
              </div>
              <table className="w-full min-w-[960px] text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="pb-2 pr-3 font-medium">CV</th>
                    <th className="pb-2 pr-3 font-medium">First name *</th>
                    <th className="pb-2 pr-3 font-medium">Last name *</th>
                    <th className="pb-2 pr-3 font-medium">Email *</th>
                    <th className="pb-2 pr-3 font-medium">Phone *</th>
                    <th className="pb-2 pr-3 font-medium">Job *</th>
                    <th className="pb-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rowStates.map(({ row, errs, complete, parsing }) => {
                    const serverIssue = (field: string) =>
                      row.serverIssues.find((i) => i.field === field)?.message;
                    const invalid = (field: string): boolean =>
                      Boolean((attempted && errs[field]) || serverIssue(field));
                    const rowProblems = [
                      ...Object.keys(errs).map((f) => FIELD_LABELS[f] ?? f),
                      ...row.serverIssues.filter((i) => !i.field).map((i) => i.message),
                    ];
                    return (
                      <tr
                        key={row.itemId}
                        data-testid="review-row"
                        data-complete={complete ? "true" : "false"}
                        className="border-b align-top"
                      >
                        <td className="py-3 pr-3">
                          <span className="block max-w-[120px] truncate font-medium">
                            {row.fileName}
                          </span>
                        </td>
                        {(
                          [
                            ["first_name", "First name"],
                            ["last_name", "Last name"],
                            ["email", "Email"],
                            ["phone", "Phone"],
                          ] as const
                        ).map(([field, label]) => (
                          <td key={field} className="py-3 pr-3">
                            <Input
                              value={row.values[field]}
                              onChange={(e) => updateBatchField(row.itemId, field, e.target.value)}
                              aria-label={`${label} for ${row.fileName}`}
                              aria-required="true"
                              aria-invalid={invalid(field)}
                              title={serverIssue(field) ?? (attempted ? errs[field] : undefined)}
                            />
                          </td>
                        ))}
                        <td className="py-3 pr-3">
                          <Select
                            value={row.values.job_id}
                            onChange={(e) => updateBatchField(row.itemId, "job_id", e.target.value)}
                            aria-label={`Job for ${row.fileName}`}
                            aria-required="true"
                            aria-invalid={invalid("job_id")}
                          >
                            <option value="">Select a job</option>
                            {jobItems.map((j) => (
                              <option key={j.id} value={j.id}>
                                {j.title}
                              </option>
                            ))}
                          </Select>
                        </td>
                        <td className="py-3">
                          {parsing ? (
                            <Badge variant="secondary">Parsing…</Badge>
                          ) : complete && row.serverIssues.length === 0 ? (
                            <Badge variant="success">Ready</Badge>
                          ) : (
                            <Badge
                              variant="warning"
                              title={`Needs: ${rowProblems.join(", ")}`}
                              data-testid="incomplete-badge"
                            >
                              Incomplete
                            </Badge>
                          )}
                          {!parsing && rowProblems.length > 0 && (
                            <p className="mt-1 max-w-[160px] text-xs text-muted-foreground">
                              {rowProblems.join(", ")}
                            </p>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {batchRows.length === 0 && (
                <p className="text-sm text-muted-foreground">Parsing CVs… rows will appear here.</p>
              )}
              {!allComplete && batchRows.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Save all is available once every row is complete. Use Save complete rows to save
                  the ready ones now; incomplete rows stay in the draft.
                </p>
              )}
            </CardContent>
          </Card>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Profile</CardTitle>
                <CardDescription>Fields marked * are required.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2">
                <Field
                  id="first_name"
                  label="First name"
                  required
                  fromCv={autofillKeys.has("first_name")}
                  error={errors.first_name?.message}
                >
                  <Input
                    id="first_name"
                    aria-required="true"
                    {...register("first_name")}
                    aria-invalid={Boolean(errors.first_name)}
                  />
                </Field>
                <Field
                  id="last_name"
                  label="Last name"
                  required
                  fromCv={autofillKeys.has("last_name")}
                  error={errors.last_name?.message}
                >
                  <Input
                    id="last_name"
                    aria-required="true"
                    {...register("last_name")}
                    aria-invalid={Boolean(errors.last_name)}
                  />
                </Field>
                <Field
                  id="email"
                  label="Email"
                  required
                  fromCv={autofillKeys.has("email")}
                  error={errors.email?.message}
                >
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    aria-required="true"
                    {...register("email")}
                    aria-invalid={Boolean(errors.email)}
                  />
                </Field>
                <Field
                  id="phone"
                  label="Phone"
                  required
                  fromCv={autofillKeys.has("phone")}
                  error={errors.phone?.message}
                >
                  <Input
                    id="phone"
                    type="tel"
                    autoComplete="tel"
                    aria-required="true"
                    {...register("phone")}
                    aria-invalid={Boolean(errors.phone)}
                  />
                </Field>
                <Field
                  id="current_location"
                  label="Location"
                  fromCv={autofillKeys.has("current_location")}
                  error={errors.current_location?.message}
                >
                  <Input id="current_location" {...register("current_location")} />
                </Field>
                <Field
                  id="current_company"
                  label="Company"
                  fromCv={autofillKeys.has("current_company")}
                >
                  <Input id="current_company" {...register("current_company")} />
                </Field>
                <Field id="current_title" label="Title" fromCv={autofillKeys.has("current_title")}>
                  <Input id="current_title" {...register("current_title")} />
                </Field>
                <Field
                  id="total_experience_years"
                  label="Experience (years)"
                  fromCv={autofillKeys.has("total_experience_years")}
                  error={errors.total_experience_years?.message}
                >
                  <Input id="total_experience_years" {...register("total_experience_years")} />
                </Field>
                <Field
                  id="notice_period_days"
                  label="Notice period (days)"
                  error={errors.notice_period_days?.message}
                >
                  <Input id="notice_period_days" {...register("notice_period_days")} />
                </Field>
                <Field id="linkedin_url" label="LinkedIn" fromCv={autofillKeys.has("linkedin_url")}>
                  <Input id="linkedin_url" {...register("linkedin_url")} />
                </Field>
                <Field id="portfolio_url" label="Portfolio">
                  <Input id="portfolio_url" {...register("portfolio_url")} />
                </Field>
                <Field id="job_id" label="Job" required error={errors.job_id?.message}>
                  <Select
                    id="job_id"
                    aria-required="true"
                    {...register("job_id")}
                    aria-invalid={Boolean(errors.job_id)}
                  >
                    <option value="">—</option>
                    {jobItems.map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.title}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field id="department_id" label="Department">
                  {jobDepartment ? (
                    <>
                      <Input
                        id="department_id"
                        value={jobDepartment.name}
                        readOnly
                        disabled
                        aria-describedby="department-hint"
                      />
                      <p id="department-hint" className="text-xs text-muted-foreground">
                        Taken from the selected job.
                      </p>
                    </>
                  ) : (
                    <Select id="department_id" {...register("department_id")}>
                      <option value="">—</option>
                      {(departments.data ?? []).map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </Select>
                  )}
                </Field>
                <Field id="source" label="Source">
                  <Select id="source" {...register("source")}>
                    {(["manual", "referral", "linkedin", "agency"] as const).map((s) => (
                      <option key={s} value={s}>
                        {CANDIDATE_SOURCE_LABELS[s]}
                      </option>
                    ))}
                  </Select>
                </Field>
                <div className="space-y-2 sm:col-span-2">
                  <Field id="tags" label="Tags">
                    <Input id="tags" placeholder="e.g. senior, react" {...register("tags")} />
                  </Field>
                  <p className="text-xs text-muted-foreground">Comma-separated</p>
                </div>
              </CardContent>
            </Card>

            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-semibold">Compensation</h2>
                {jobId && expectedAmount != null && <BudgetBadge status={previewBudget} />}
              </div>
              <SalaryFields title="Current CTC" prefix="current_ctc" />
              <SalaryFields
                title="Expected CTC"
                prefix="expected_ctc"
                description="Used for budget comparison when a job is selected."
              />
              <SalaryFields title="Offered CTC" prefix="offered_ctc" />
            </div>

            <div className="flex flex-wrap items-center justify-end gap-3">
              {showErrors && !canSaveSingle && (
                <p role="status" className="mr-auto text-sm text-muted-foreground">
                  {uploading
                    ? "Waiting for the CV to finish uploading…"
                    : cvBlocked
                      ? "A valid CV is required."
                      : "Complete the required fields (*) to save."}
                </p>
              )}
              <Button type="button" variant="ghost" onClick={onCancel}>
                Cancel
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  if (user?.id) localStorage.removeItem(draftKey(user.id));
                  cancelAll();
                }}
              >
                Clear draft
              </Button>
              <Button
                type="submit"
                aria-disabled={!canSaveSingle}
                data-testid="save-candidate"
                className={canSaveSingle ? undefined : "cursor-not-allowed opacity-50"}
                onClick={onSaveClick}
              >
                {saveMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                )}
                Save candidate
              </Button>
            </div>
          </>
        )}
      </form>
    </FormProvider>
  );
}
