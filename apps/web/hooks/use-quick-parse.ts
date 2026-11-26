"use client";

import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api";

/**
 * Quick fill extraction. A mutation (not a query) on purpose: the pasted text is personal data,
 * so it must never become part of a cache key or be refetched in the background.
 */
export function useQuickParse() {
  return useMutation({
    mutationFn: (text: string) => api.candidates.quickParse(text),
    gcTime: 0,
  });
}
