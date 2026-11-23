"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  ApplicationDetail,
  ApplicationListParams,
  BoardOut,
  BulkActionInput,
  StagePatchInput,
} from "@/types/api";

export const applicationKeys = {
  all: ["applications"] as const,
  list: (params: ApplicationListParams) => ["applications", "list", params] as const,
  detail: (id: string) => ["applications", "detail", id] as const,
  stages: ["applications", "stages"] as const,
  board: (jobId: string) => ["applications", "board", jobId] as const,
  timeline: (candidateId: string) => ["candidates", "timeline", candidateId] as const,
};

export function useApplications(params: ApplicationListParams) {
  return useQuery({
    queryKey: applicationKeys.list(params),
    queryFn: () => api.applications.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useApplication(id: string | null) {
  return useQuery({
    queryKey: applicationKeys.detail(id ?? ""),
    queryFn: () => api.applications.get(id!),
    enabled: Boolean(id),
    retry: (count, error) => count < 1 && !("status" in error && error.status === 404),
  });
}

export function usePipelineStages() {
  return useQuery({
    queryKey: applicationKeys.stages,
    queryFn: () => api.applications.stages(),
    staleTime: 5 * 60_000,
  });
}

export function useJobBoard(jobId: string) {
  return useQuery({
    queryKey: applicationKeys.board(jobId),
    queryFn: () => api.jobs.board(jobId),
    enabled: Boolean(jobId),
  });
}

export function useCandidateTimeline(candidateId: string | null) {
  return useQuery({
    queryKey: applicationKeys.timeline(candidateId ?? ""),
    queryFn: () => api.candidates.timeline(candidateId!),
    enabled: Boolean(candidateId),
  });
}

export function useDocumentUrl(documentId: string | null) {
  return useQuery({
    queryKey: ["documents", "download-url", documentId],
    queryFn: () => api.documents.downloadUrl(documentId!),
    enabled: Boolean(documentId),
    staleTime: 60_000,
  });
}

interface MoveStageVars {
  applicationId: string;
  body: StagePatchInput;
  jobId?: string;
}

export function useMoveStage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ applicationId, body }: MoveStageVars) =>
      api.applications.moveStage(applicationId, body),
    onMutate: async ({ applicationId, body, jobId }) => {
      if (!jobId) return { previous: undefined as BoardOut | undefined };
      await queryClient.cancelQueries({ queryKey: applicationKeys.board(jobId) });
      const previous = queryClient.getQueryData<BoardOut>(applicationKeys.board(jobId));
      if (previous) {
        const stages = previous.stages.map((col) => ({
          ...col,
          cards: col.cards.filter((c) => c.id !== applicationId),
        }));
        const card = previous.stages.flatMap((c) => c.cards).find((c) => c.id === applicationId);
        const next = stages.map((col) => {
          if (col.stage.id !== body.stage_id || !card) return { ...col, count: col.cards.length };
          const cards = [{ ...card, stage_entered_at: new Date().toISOString() }, ...col.cards];
          return { ...col, cards, count: cards.length };
        });
        queryClient.setQueryData<BoardOut>(applicationKeys.board(jobId), {
          ...previous,
          stages: next,
        });
      }
      return { previous };
    },
    onError: (_err, vars, context) => {
      if (vars.jobId && context?.previous) {
        queryClient.setQueryData(applicationKeys.board(vars.jobId), context.previous);
      }
    },
    onSuccess: (detail: ApplicationDetail, vars) => {
      queryClient.setQueryData(applicationKeys.detail(detail.id), detail);
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
      if (vars.jobId) {
        void queryClient.invalidateQueries({ queryKey: applicationKeys.board(vars.jobId) });
      }
      void queryClient.invalidateQueries({
        queryKey: applicationKeys.timeline(detail.candidate.id),
      });
    },
  });
}

export function useShortlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      applicationId,
      shortlisted,
    }: {
      applicationId: string;
      shortlisted?: boolean;
    }) => api.applications.shortlist(applicationId, shortlisted),
    onSuccess: (result) => {
      queryClient.setQueryData<ApplicationDetail>(
        applicationKeys.detail(result.application_id),
        (prev) => (prev ? { ...prev, is_shortlisted: result.is_shortlisted } : prev),
      );
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}

export function useBulkAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: BulkActionInput) => api.applications.bulkAction(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}

export function useApplicationFinalScore(applicationId: string | null) {
  return useQuery({
    queryKey: ["applications", "final-score", applicationId ?? ""],
    queryFn: () => api.applications.finalScore(applicationId!),
    enabled: Boolean(applicationId),
    staleTime: 60_000,
  });
}
