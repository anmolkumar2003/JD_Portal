"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { applicationKeys } from "@/hooks/use-applications";
import { api } from "@/lib/api";
import type { CandidatePatchInput, DocumentOut } from "@/types/api";

function invalidateAfterCandidateRemoval(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
  void queryClient.invalidateQueries({ queryKey: ["analytics"] });
  void queryClient.invalidateQueries({ queryKey: ["search"] });
}

export function useUpdateCandidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CandidatePatchInput }) =>
      api.candidates.update(id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}

export function useDeleteCandidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.candidates.delete(id),
    onSuccess: () => invalidateAfterCandidateRemoval(queryClient),
  });
}

export function useBulkDeleteCandidates() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (candidateIds: string[]) => api.candidates.bulkDelete(candidateIds),
    onSuccess: () => invalidateAfterCandidateRemoval(queryClient),
  });
}

export function useAnonymizeCandidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.candidates.anonymize(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}

export function useUploadCandidateDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      candidateId,
      file,
      applicationId,
    }: {
      candidateId: string;
      file: File;
      applicationId?: string;
    }): Promise<DocumentOut> => {
      const form = new FormData();
      form.append("file", file);
      form.append("doc_type", "cv");
      if (applicationId) form.append("application_id", applicationId);
      return api.candidates.uploadDocument(candidateId, form);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}
