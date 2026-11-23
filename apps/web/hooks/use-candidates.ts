"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { applicationKeys } from "@/hooks/use-applications";
import { api } from "@/lib/api";
import type { CandidatePatchInput, DocumentOut } from "@/types/api";

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
