"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

const LOOKUP_STALE_MS = 5 * 60_000;

export function useDepartments() {
  return useQuery({
    queryKey: ["departments"],
    queryFn: api.org.departments,
    staleTime: LOOKUP_STALE_MS,
  });
}

export function useLocations() {
  return useQuery({
    queryKey: ["locations"],
    queryFn: api.org.locations,
    staleTime: LOOKUP_STALE_MS,
  });
}
