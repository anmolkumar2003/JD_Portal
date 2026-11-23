"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { toast } from "sonner";

import {
  EMPTY_CANDIDATE_FORM,
  buildCreateFormData,
  candidateFormSchema,
  type AutofillKey,
  type CandidateFormValues,
} from "@/components/candidates/candidate-form-schema";
import { BudgetBadge } from "@/components/candidates/budget-badge";
import { MultiCvDropzone, type CvUploadItem } from "@/components/candidates/cv-dropzone";
import { SalaryFields } from "@/components/candidates/salary-fields";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useAuth } from "@/hooks/use-auth";
import { useJob, useJobs } from "@/hooks/use-jobs";
import { useDepartments } from "@/hooks/use-lookups";
import { ApiError, api } from "@/lib/api";
import { CANDIDATE_SOURCE_LABELS } from "@/lib/labels";
import { computeBudgetStatus } from "@/lib/salary";
import type { CvParseOut } from "@/types/api";

function draftKey(userId: string): string {
  return `add-candidate-draft:${userId}`;
}

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
  children,
}: {
  id: string;
  label: string;
  fromCv?: boolean;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>
        {label}
        <FromCvBadge show={Boolean(fromCv)} />
      </Label>
      {children}
      {error && (
        <p id={`${id}-error`} className="text-sm text-destructive">
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
  file: File;
  values: CandidateFormValues;
  autofill: Set<AutofillKey>;
};

interface AddCandidateFormProps {
  sharedJobId?: string;
  sharedDepartmentId?: string;
}

export function AddCandidateForm({ sharedJobId, sharedDepartmentId }: AddCandidateFormProps) {
  const router = useRouter();
  const { user } = useAuth();
  const departments = useDepartments();
  const jobs = useJobs({ page_size: 100, sort: "-created_at" });
  const [cvItems, setCvItems] = useState<CvUploadItem[]>([]);
  const [autofillKeys, setAutofillKeys] = useState<Set<AutofillKey>>(new Set());
  const [batchRows, setBatchRows] = useState<BatchRow[]>([]);
  const [debouncedEmail, setDebouncedEmail] = useState("");
  const [debouncedPhone, setDebouncedPhone] = useState("");
  const parsingRef = useRef<Set<string>>(new Set());
  const restoredRef = useRef(false);

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
    reset,
    formState: { errors, isDirty, dirtyFields },
  } = form;

  const values = watch();
  const jobId = values.job_id;
  const jobDetail = useJob(jobId || "");

  const isBatchMode = cvItems.filter((i) => i.status !== "error").length > 1;

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

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [isDirty]);

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

  const applyParseToForm = useCallback(
    (data: CvParseOut) => {
      const patch = parseToFormPatch(data);
      const nextAutofill = new Set(autofillKeys);
      (Object.keys(patch) as AutofillKey[]).forEach((key) => {
        if (dirtyFields[key]) return;
        const value = patch[key];
        if (value !== undefined) {
          setValue(key, value as string, { shouldDirty: false });
          nextAutofill.add(key);
        }
      });
      setAutofillKeys(nextAutofill);
    },
    [autofillKeys, dirtyFields, setValue],
  );

  const runParse = useCallback(
    async (item: CvUploadItem, batch: boolean) => {
      if (parsingRef.current.has(item.id)) return;
      parsingRef.current.add(item.id);
      setCvItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, status: "parsing" } : i)));
      try {
        const data = await api.candidates.parseCv(item.file);
        setCvItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, status: "done" } : i)));
        if (batch) {
          setBatchRows((prev) => {
            const existing = prev.find((r) => r.itemId === item.id);
            if (existing) {
              const patch = parseToFormPatch(data);
              const autofill = new Set(existing.autofill);
              const values = { ...existing.values };
              (Object.keys(patch) as AutofillKey[]).forEach((k) => {
                if (patch[k] !== undefined) {
                  values[k] = patch[k] as string;
                  autofill.add(k);
                }
              });
              return prev.map((r) => (r.itemId === item.id ? { ...r, values, autofill } : r));
            }
            const values = {
              ...EMPTY_CANDIDATE_FORM,
              job_id: sharedJobId ?? "",
              department_id: sharedDepartmentId ?? "",
            };
            const patch = parseToFormPatch(data);
            const autofill = new Set<AutofillKey>();
            (Object.keys(patch) as AutofillKey[]).forEach((k) => {
              if (patch[k] !== undefined) {
                values[k] = patch[k] as string;
                autofill.add(k);
              }
            });
            return [
              ...prev,
              {
                itemId: item.id,
                fileName: item.file.name,
                file: item.file,
                values,
                autofill,
              },
            ];
          });
        } else {
          applyParseToForm(data);
        }
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "Could not parse this CV";
        setCvItems((prev) =>
          prev.map((i) => (i.id === item.id ? { ...i, status: "error", error: message } : i)),
        );
      } finally {
        parsingRef.current.delete(item.id);
      }
    },
    [applyParseToForm, sharedDepartmentId, sharedJobId],
  );

  useEffect(() => {
    const validItems = cvItems.filter((i) => i.status !== "error");
    const batch = validItems.length > 1;
    for (const item of cvItems.filter((i) => i.status === "ready")) {
      void runParse(item, batch);
    }
  }, [cvItems, runParse]);

  useEffect(() => {
    if (!isBatchMode) return;
    const valid = cvItems.filter((i) => i.status !== "error");
    setBatchRows((prev) => {
      const byId = new Map(prev.map((r) => [r.itemId, r]));
      for (const item of valid) {
        if (!byId.has(item.id)) {
          const seeded =
            valid[0]?.id === item.id && prev.length === 0
              ? form.getValues()
              : {
                  ...EMPTY_CANDIDATE_FORM,
                  job_id: sharedJobId ?? "",
                  department_id: sharedDepartmentId ?? "",
                };
          byId.set(item.id, {
            itemId: item.id,
            fileName: item.file.name,
            file: item.file,
            values: seeded,
            autofill: new Set(),
          });
        }
      }
      return valid.map((item) => byId.get(item.id)).filter((r): r is BatchRow => Boolean(r));
    });
  }, [isBatchMode, cvItems, form, sharedDepartmentId, sharedJobId]);

  useEffect(() => {
    if (isBatchMode) return;
    if (cvItems.length === 0) {
      setAutofillKeys(new Set());
    }
  }, [cvItems.length, isBatchMode]);

  const jobMax = jobDetail.data?.salary_max ? Number(jobDetail.data.salary_max) : null;
  const expectedAmount = values.expected_ctc.amount.trim()
    ? Number(values.expected_ctc.amount)
    : null;
  const previewBudget = computeBudgetStatus(expectedAmount, values.expected_ctc.unit, jobMax);

  const createMutation = useMutation({
    mutationFn: (payload: { values: CandidateFormValues; file: File | null }) =>
      api.candidates.create(buildCreateFormData(payload.values, payload.file)),
    onSuccess: (result) => {
      toast.success(
        result.reused ? "Existing candidate updated" : "Candidate saved",
        result.reference_no ? { description: `Ref ${result.reference_no}` } : undefined,
      );
      if (user?.id) localStorage.removeItem(draftKey(user.id));
      const href = result.application_id
        ? `/candidates/${result.candidate_id}?application=${result.application_id}`
        : `/candidates/${result.candidate_id}`;
      router.push(href);
    },
    onError: (error: unknown) => {
      const message = error instanceof ApiError ? error.message : "Could not save candidate";
      toast.error(message);
    },
  });

  const onSaveSingle = handleSubmit((data) => {
    const file = cvItems.find((i) => i.status !== "error")?.file ?? null;
    createMutation.mutate({ values: data, file });
  });

  const saveBatchRow = async (row: BatchRow) => {
    const parsed = candidateFormSchema.safeParse(row.values);
    if (!parsed.success) {
      toast.error(parsed.error.issues[0]?.message ?? "Fix validation errors in this row");
      return;
    }
    try {
      const result = await api.candidates.create(buildCreateFormData(parsed.data, row.file));
      toast.success(`Saved ${row.fileName}`);
      setBatchRows((prev) => prev.filter((r) => r.itemId !== row.itemId));
      setCvItems((prev) => prev.filter((i) => i.id !== row.itemId));
      if (batchRows.length <= 1) {
        const href = result.application_id
          ? `/candidates/${result.candidate_id}?application=${result.application_id}`
          : `/candidates/${result.candidate_id}`;
        router.push(href);
      }
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Could not save";
      toast.error(message);
    }
  };

  const saveAllBatch = async () => {
    for (const row of batchRows) {
      const parsed = candidateFormSchema.safeParse(row.values);
      if (!parsed.success) {
        toast.error(`${row.fileName}: ${parsed.error.issues[0]?.message ?? "Invalid row"}`);
        return;
      }
    }
    let lastHref: string | null = null;
    for (const row of batchRows) {
      const parsed = candidateFormSchema.parse(row.values);
      try {
        const result = await api.candidates.create(buildCreateFormData(parsed, row.file));
        lastHref = result.application_id
          ? `/candidates/${result.candidate_id}?application=${result.application_id}`
          : `/candidates/${result.candidate_id}`;
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "Save failed";
        toast.error(`${row.fileName}: ${message}`);
        return;
      }
    }
    toast.success(`Saved ${batchRows.length} candidates`);
    if (user?.id) localStorage.removeItem(draftKey(user.id));
    setBatchRows([]);
    setCvItems([]);
    if (lastHref) router.push(lastHref);
  };

  const updateBatchField = (itemId: string, key: keyof CandidateFormValues, value: string) => {
    setBatchRows((prev) =>
      prev.map((row) =>
        row.itemId === itemId
          ? {
              ...row,
              values: { ...row.values, [key]: value },
              autofill: new Set([...row.autofill].filter((k) => k !== key)),
            }
          : row,
      ),
    );
  };

  const duplicateWarning = useMemo(() => {
    const matches = duplicates.data?.matches ?? [];
    return matches.length > 0 ? matches : null;
  }, [duplicates.data]);

  return (
    <FormProvider {...form}>
      <form onSubmit={onSaveSingle} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>CV upload</CardTitle>
            <CardDescription>
              Drop one CV to prefill the form, or several to review and save in bulk.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <MultiCvDropzone items={cvItems} onChange={setCvItems} />
          </CardContent>
        </Card>

        {duplicateWarning && !isBatchMode && (
          <div
            role="status"
            className="flex gap-3 rounded-lg border border-warning/40 bg-warning/10 p-4 text-sm"
          >
            <AlertTriangle className="h-5 w-5 shrink-0 text-warning" aria-hidden />
            <div>
              <p className="font-medium">Possible duplicate</p>
              <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                {duplicateWarning.map((m) => (
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
            </div>
          </div>
        )}

        {isBatchMode ? (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-4">
              <div>
                <CardTitle>Review uploads</CardTitle>
                <CardDescription>
                  Edit each parsed profile, then save individually or all at once.
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="secondary"
                disabled={!batchRows.length}
                onClick={() => void saveAllBatch()}
              >
                Save all
              </Button>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="pb-2 pr-3 font-medium">CV</th>
                    <th className="pb-2 pr-3 font-medium">First name</th>
                    <th className="pb-2 pr-3 font-medium">Last name</th>
                    <th className="pb-2 pr-3 font-medium">Email</th>
                    <th className="pb-2 pr-3 font-medium">Phone</th>
                    <th className="pb-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {batchRows.map((row) => (
                    <tr key={row.itemId} className="border-b align-top">
                      <td className="py-3 pr-3">
                        <span className="block max-w-[120px] truncate font-medium">
                          {row.fileName}
                        </span>
                      </td>
                      <td className="py-3 pr-3">
                        <Input
                          value={row.values.first_name}
                          onChange={(e) =>
                            updateBatchField(row.itemId, "first_name", e.target.value)
                          }
                          aria-label={`First name for ${row.fileName}`}
                        />
                      </td>
                      <td className="py-3 pr-3">
                        <Input
                          value={row.values.last_name}
                          onChange={(e) =>
                            updateBatchField(row.itemId, "last_name", e.target.value)
                          }
                        />
                      </td>
                      <td className="py-3 pr-3">
                        <Input
                          value={row.values.email}
                          onChange={(e) => updateBatchField(row.itemId, "email", e.target.value)}
                        />
                      </td>
                      <td className="py-3 pr-3">
                        <Input
                          value={row.values.phone}
                          onChange={(e) => updateBatchField(row.itemId, "phone", e.target.value)}
                        />
                      </td>
                      <td className="py-3">
                        <Button type="button" size="sm" onClick={() => void saveBatchRow(row)}>
                          Save
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {batchRows.length === 0 && (
                <p className="text-sm text-muted-foreground">Parsing CVs… rows will appear here.</p>
              )}
            </CardContent>
          </Card>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Profile</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2">
                <Field
                  id="first_name"
                  label="First name"
                  fromCv={autofillKeys.has("first_name")}
                  error={errors.first_name?.message}
                >
                  <Input
                    id="first_name"
                    {...register("first_name")}
                    aria-invalid={Boolean(errors.first_name)}
                  />
                </Field>
                <Field
                  id="last_name"
                  label="Last name"
                  fromCv={autofillKeys.has("last_name")}
                  error={errors.last_name?.message}
                >
                  <Input id="last_name" {...register("last_name")} />
                </Field>
                <Field
                  id="email"
                  label="Email"
                  fromCv={autofillKeys.has("email")}
                  error={errors.email?.message}
                >
                  <Input id="email" type="email" autoComplete="email" {...register("email")} />
                </Field>
                <Field
                  id="phone"
                  label="Phone"
                  fromCv={autofillKeys.has("phone")}
                  error={errors.phone?.message}
                >
                  <Input id="phone" {...register("phone")} />
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
                <Field id="department_id" label="Department">
                  <Select id="department_id" {...register("department_id")}>
                    <option value="">—</option>
                    {(departments.data ?? []).map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field id="job_id" label="Job">
                  <Select id="job_id" {...register("job_id")}>
                    <option value="">—</option>
                    {(jobs.data?.items ?? []).map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.title}
                      </option>
                    ))}
                  </Select>
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

            <div className="flex justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  if (user?.id) localStorage.removeItem(draftKey(user.id));
                  reset(EMPTY_CANDIDATE_FORM);
                  setCvItems([]);
                  setAutofillKeys(new Set());
                }}
              >
                Clear draft
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending && (
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
