"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SavedFilterIn } from "@/types/api";

export const savedFilterKeys = {
  all: ["saved-filters"] as const,
};

export function useSavedFilters() {
  return useQuery({
    queryKey: savedFilterKeys.all,
    queryFn: () => api.savedFilters.list(),
  });
}

export function useCreateSavedFilter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: SavedFilterIn) => api.savedFilters.create(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: savedFilterKeys.all });
    },
  });
}

export function useUpdateSavedFilter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: SavedFilterIn }) =>
      api.savedFilters.update(id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: savedFilterKeys.all });
    },
  });
}

export function useDeleteSavedFilter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.savedFilters.delete(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: savedFilterKeys.all });
    },
  });
}
