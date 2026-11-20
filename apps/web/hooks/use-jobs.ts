"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  Job,
  JobCreateInput,
  JobFieldsInput,
  JobListParams,
  RequirementsInput,
} from "@/types/api";

export const jobKeys = {
  all: ["jobs"] as const,
  list: (params: JobListParams) => ["jobs", "list", params] as const,
  detail: (id: string) => ["jobs", "detail", id] as const,
};

export function useJobs(params: JobListParams) {
  return useQuery({
    queryKey: jobKeys.list(params),
    queryFn: () => api.jobs.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useJob(id: string) {
  return useQuery({
    queryKey: jobKeys.detail(id),
    queryFn: () => api.jobs.get(id),
    retry: (count, error) => count < 1 && !("status" in error && error.status === 404),
  });
}

function useJobCacheUpdate() {
  const queryClient = useQueryClient();
  return (job: Job) => {
    queryClient.setQueryData(jobKeys.detail(job.id), job);
    void queryClient.invalidateQueries({ queryKey: [...jobKeys.all, "list"] });
  };
}

interface SaveJobInput {
  /** Omit to create a new job. */
  jobId?: string;
  fields: JobFieldsInput;
  requirements: RequirementsInput;
  publish: boolean;
}

/** The job was saved, but publishing it failed. Carries the saved job so callers can retry. */
export class JobPublishError extends Error {
  constructor(
    readonly job: Job,
    override readonly cause: unknown,
  ) {
    super("The job was saved as a draft, but could not be published.");
    this.name = "JobPublishError";
  }
}

/** Create a job, or update fields and requirements of an existing one; optionally publish. */
export function useSaveJob() {
  const onSaved = useJobCacheUpdate();
  return useMutation({
    mutationFn: async ({ jobId, fields, requirements, publish }: SaveJobInput): Promise<Job> => {
      let job: Job;
      if (jobId) {
        await api.jobs.update(jobId, fields);
        job = await api.jobs.replaceRequirements(jobId, requirements);
      } else {
        const body: JobCreateInput = { ...fields, requirements };
        job = await api.jobs.create(body);
      }
      if (!publish) return job;
      try {
        return await api.jobs.publish(job.id);
      } catch (cause) {
        onSaved(job);
        throw new JobPublishError(job, cause);
      }
    },
    onSuccess: onSaved,
  });
}

export function usePublishJob() {
  const onSaved = useJobCacheUpdate();
  return useMutation({ mutationFn: api.jobs.publish, onSuccess: onSaved });
}

export function useCloseJob() {
  const onSaved = useJobCacheUpdate();
  return useMutation({ mutationFn: api.jobs.close, onSuccess: onSaved });
}
