"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ApplicationListParams, StageChangeInput } from "@/types/api";

export const applicationKeys = {
  all: ["applications"] as const,
  list: (params: ApplicationListParams) => ["applications", "list", params] as const,
  detail: (id: string) => ["applications", "detail", id] as const,
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
    queryFn: () => api.applications.get(id as string),
    enabled: Boolean(id),
    retry: (count, error) => count < 1 && !("status" in error && error.status === 404),
  });
}

export function useChangeStage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: StageChangeInput }) =>
      api.applications.changeStage(id, body),
    onSuccess: (detail) => {
      queryClient.setQueryData(applicationKeys.detail(detail.id), detail);
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
      void queryClient.invalidateQueries({ queryKey: ["pipeline"] });
      void queryClient.invalidateQueries({
        queryKey: ["candidates", "timeline", detail.candidate.id],
      });
    },
  });
}
