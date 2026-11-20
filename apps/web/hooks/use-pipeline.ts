"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Board, StageChangeInput } from "@/types/api";

import { applicationKeys } from "./use-applications";

export const pipelineKeys = {
  all: ["pipeline"] as const,
  board: (jobId: string) => ["pipeline", "board", jobId] as const,
};

export function useJobBoard(jobId: string) {
  return useQuery({
    queryKey: pipelineKeys.board(jobId),
    queryFn: () => api.jobs.board(jobId),
    enabled: Boolean(jobId),
  });
}

function moveCardLocally(
  board: Board,
  applicationId: string,
  toStageId: string,
): Board | undefined {
  const fromCol = board.stages.find((col) => col.cards.some((c) => c.id === applicationId));
  const toCol = board.stages.find((col) => col.stage.id === toStageId);
  if (!fromCol || !toCol) return undefined;
  const card = fromCol.cards.find((c) => c.id === applicationId);
  if (!card) return undefined;
  if (fromCol.stage.id === toStageId) return board;

  return {
    ...board,
    stages: board.stages.map((col) => {
      if (col.stage.id === fromCol.stage.id) {
        const cards = col.cards.filter((c) => c.id !== applicationId);
        return { ...col, cards, count: cards.length };
      }
      if (col.stage.id === toStageId) {
        const cards = [...col.cards, { ...card, stage_entered_at: new Date().toISOString() }];
        return { ...col, cards, count: cards.length };
      }
      return col;
    }),
  };
}

export function useMoveApplicationStage(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: StageChangeInput }) =>
      api.applications.changeStage(id, body),
    onMutate: async ({ id, body }) => {
      await queryClient.cancelQueries({ queryKey: pipelineKeys.board(jobId) });
      const previous = queryClient.getQueryData<Board>(pipelineKeys.board(jobId));
      if (previous) {
        const next = moveCardLocally(previous, id, body.stage_id);
        if (next) queryClient.setQueryData(pipelineKeys.board(jobId), next);
      }
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(pipelineKeys.board(jobId), context.previous);
      }
    },
    onSuccess: (detail) => {
      queryClient.setQueryData(applicationKeys.detail(detail.id), detail);
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
      void queryClient.invalidateQueries({
        queryKey: ["candidates", "timeline", detail.candidate.id],
      });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: pipelineKeys.board(jobId) });
    },
  });
}
