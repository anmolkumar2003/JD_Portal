"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useEffect } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { candidateFormSchema, parseTagsInput } from "@/components/candidates/candidate-form-schema";
import { QuickFillBadge, QuickFillProvider } from "@/components/candidates/quick-fill-context";
import { CvDropzone, cvFileError } from "@/components/careers/cv-dropzone";
import { SalaryFields } from "@/components/candidates/salary-fields";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useUpdateCandidate, useUploadCandidateDocument } from "@/hooks/use-candidates";
import { useDepartments } from "@/hooks/use-lookups";
import { ApiError } from "@/lib/api";
import { CANDIDATE_SOURCE_LABELS } from "@/lib/labels";
import { normalizeLinkedInUrl } from "@/lib/linkedin";
import { formSalaryToIn, salaryOutToForm } from "@/lib/salary";
import type { ApplicationDetail, CandidatePatchInput } from "@/types/api";

const EDIT_SOURCES = ["manual", "referral", "linkedin", "agency", "career_site"] as const;

const editSchema = candidateFormSchema.extend({
  source: z.enum(["manual", "referral", "linkedin", "agency", "career_site"]),
});

type CandidateEditFormValues = z.infer<typeof editSchema>;

function toFormValues(application: ApplicationDetail): CandidateEditFormValues {
  const c = application.candidate;
  return {
    first_name: c.first_name,
    last_name: c.last_name,
    email: c.email,
    phone: c.phone ?? "",
    current_location: c.current_location ?? "",
    current_company: c.current_company ?? "",
    current_title: c.current_title ?? "",
    total_experience_years: c.total_experience_years ?? "",
    notice_period_days: c.notice_period_days != null ? String(c.notice_period_days) : "",
    linkedin_url: c.linkedin_url ?? "",
    portfolio_url: c.portfolio_url ?? "",
    department_id: c.department_id ?? "",
    job_id: application.job.id,
    source: c.source,
    tags: c.tags.join(", "),
    current_ctc: salaryOutToForm(c.current_salary),
    expected_ctc: salaryOutToForm(c.expected_salary),
    offered_ctc: salaryOutToForm(c.offered_salary),
  };
}

function toPatch(values: CandidateEditFormValues): CandidatePatchInput {
  const trim = (v: string) => (v.trim() === "" ? null : v.trim());
  return {
    first_name: values.first_name.trim(),
    last_name: values.last_name.trim(),
    email: values.email.trim(),
    phone: trim(values.phone),
    current_location: trim(values.current_location),
    current_company: trim(values.current_company),
    current_title: trim(values.current_title),
    total_experience_years: values.total_experience_years.trim()
      ? Number(values.total_experience_years)
      : null,
    notice_period_days: values.notice_period_days.trim() ? Number(values.notice_period_days) : null,
    linkedin_url: (() => {
      const raw = values.linkedin_url.trim();
      if (!raw) return null;
      try {
        return normalizeLinkedInUrl(raw);
      } catch {
        return raw;
      }
    })(),
    portfolio_url: trim(values.portfolio_url),
    department_id: values.department_id || null,
    source: values.source,
    tags: parseTagsInput(values.tags),
    current_ctc: formSalaryToIn(values.current_ctc),
    expected_ctc: formSalaryToIn(values.expected_ctc),
    offered_ctc: formSalaryToIn(values.offered_ctc),
  };
}

interface CandidateEditDialogProps {
  application: ApplicationDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Quick fill remembers which fields it wrote (for the "from quick fill" badges). */
export function CandidateEditDialog(props: CandidateEditDialogProps) {
  return (
    <QuickFillProvider>
      <CandidateEditDialogInner {...props} />
    </QuickFillProvider>
  );
}

function CandidateEditDialogInner({ application, open, onOpenChange }: CandidateEditDialogProps) {
  const departments = useDepartments();
  const update = useUpdateCandidate();
  const uploadDoc = useUploadCandidateDocument();

  const form = useForm<CandidateEditFormValues>({
    resolver: zodResolver(editSchema),
    defaultValues: toFormValues(application),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = form;

  useEffect(() => {
    if (open) reset(toFormValues(application));
  }, [open, application, reset]);

  const onSubmit = handleSubmit(async (values) => {
    try {
      await update.mutateAsync({
        id: application.candidate.id,
        body: toPatch(values),
      });
      toast.success("Profile updated");
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not update profile");
    }
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit candidate</DialogTitle>
          <DialogDescription>
            Changes are saved to the candidate profile and logged on the timeline.
          </DialogDescription>
        </DialogHeader>
        <FormProvider {...form}>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="edit-first_name">
                  First name
                  <QuickFillBadge path="first_name" />
                </Label>
                <Input id="edit-first_name" {...register("first_name")} />
                {errors.first_name && (
                  <p className="text-sm text-destructive">{errors.first_name.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-last_name">
                  Last name
                  <QuickFillBadge path="last_name" />
                </Label>
                <Input id="edit-last_name" {...register("last_name")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-email">
                  Email
                  <QuickFillBadge path="email" />
                </Label>
                <Input id="edit-email" type="email" {...register("email")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-phone">
                  Phone
                  <QuickFillBadge path="phone" />
                </Label>
                <Input id="edit-phone" {...register("phone")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-location">
                  Location
                  <QuickFillBadge path="current_location" />
                </Label>
                <Input id="edit-location" {...register("current_location")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-company">
                  Company
                  <QuickFillBadge path="current_company" />
                </Label>
                <Input id="edit-company" {...register("current_company")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-title">
                  Title
                  <QuickFillBadge path="current_title" />
                </Label>
                <Input id="edit-title" {...register("current_title")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-experience">
                  Experience (years)
                  <QuickFillBadge path="total_experience_years" />
                </Label>
                <Input id="edit-experience" {...register("total_experience_years")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-notice">
                  Notice (days)
                  <QuickFillBadge path="notice_period_days" />
                </Label>
                <Input id="edit-notice" {...register("notice_period_days")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-linkedin">
                  LinkedIn
                  <QuickFillBadge path="linkedin_url" />
                </Label>
                <Input id="edit-linkedin" {...register("linkedin_url")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-portfolio">
                  Portfolio
                  <QuickFillBadge path="portfolio_url" />
                </Label>
                <Input id="edit-portfolio" {...register("portfolio_url")} />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="edit-tags">
                  Tags
                  <QuickFillBadge path="tags" />
                </Label>
                <Input id="edit-tags" {...register("tags")} placeholder="Comma-separated" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-department_id">
                  Department
                  <QuickFillBadge path="department_id" />
                </Label>
                <Select id="edit-department_id" {...register("department_id")}>
                  <option value="">—</option>
                  {(departments.data ?? []).map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-source">
                  Source
                  <QuickFillBadge path="source" />
                </Label>
                <Select id="edit-source" {...register("source")}>
                  {EDIT_SOURCES.map((s) => (
                    <option key={s} value={s}>
                      {CANDIDATE_SOURCE_LABELS[s]}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <SalaryFields title="Current CTC" prefix="current_ctc" />
            <SalaryFields title="Expected CTC" prefix="expected_ctc" />
            <SalaryFields title="Offered CTC" prefix="offered_ctc" />
            <div className="space-y-2 border-t pt-4">
              <Label>Upload CV</Label>
              <CvDropzone
                value={null}
                onChange={async (file) => {
                  if (!file) return;
                  const err = cvFileError(file);
                  if (err) {
                    toast.error(err);
                    return;
                  }
                  try {
                    await uploadDoc.mutateAsync({
                      candidateId: application.candidate.id,
                      file,
                      applicationId: application.id,
                    });
                    toast.success("Document uploaded");
                  } catch (error) {
                    toast.error(error instanceof ApiError ? error.message : "Upload failed");
                  }
                }}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={update.isPending}>
                {update.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
                Save changes
              </Button>
            </DialogFooter>
          </form>
        </FormProvider>
      </DialogContent>
    </Dialog>
  );
}
