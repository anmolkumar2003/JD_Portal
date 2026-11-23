"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { InterviewRatingIn } from "@/types/api";
import { applicationKeys } from "@/hooks/use-applications";

const ratingsKey = (applicationId: string) => ["applications", "ratings", applicationId] as const;

export function useInterviewRatings(applicationId: string | null) {
  return useQuery({
    queryKey: ratingsKey(applicationId ?? ""),
    queryFn: () => api.applications.listRatings(applicationId!),
    enabled: Boolean(applicationId),
  });
}

export function useCreateRating(applicationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: InterviewRatingIn) => api.applications.createRating(applicationId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ratingsKey(applicationId) });
      void queryClient.invalidateQueries({
        queryKey: ["applications", "final-score", applicationId],
      });
    },
  });
}

export function useUpdateRating(applicationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: InterviewRatingIn }) =>
      api.ratings.update(id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ratingsKey(applicationId) });
      void queryClient.invalidateQueries({
        queryKey: ["applications", "final-score", applicationId],
      });
    },
  });
}

export function useDeleteRating(applicationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.ratings.delete(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ratingsKey(applicationId) });
      void queryClient.invalidateQueries({
        queryKey: ["applications", "final-score", applicationId],
      });
      void queryClient.invalidateQueries({ queryKey: applicationKeys.detail(applicationId) });
    },
  });
}
