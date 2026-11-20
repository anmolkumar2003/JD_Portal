"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export const candidateKeys = {
  timeline: (id: string) => ["candidates", "timeline", id] as const,
};

export function useCandidateTimeline(candidateId: string | null) {
  return useQuery({
    queryKey: candidateKeys.timeline(candidateId ?? ""),
    queryFn: () => api.candidates.timeline(candidateId as string),
    enabled: Boolean(candidateId),
  });
}
