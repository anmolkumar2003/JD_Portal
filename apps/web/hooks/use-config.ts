"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { FeatureFlag, PublicConfig } from "@/types/api";

export const CONFIG_KEY = ["config"] as const;

const FALLBACK: PublicConfig = {
  org_name: "CA PLUS Tech Pvt. Ltd.",
  logo_data_url: null,
  features: {
    public_careers: false,
    interviews: false,
    offers: false,
    requisitions: false,
    audit_ui: false,
  },
};

/** Organization branding and enabled modules. Optional modules stay hidden until this loads. */
export function useConfig(): PublicConfig {
  const { data } = useQuery({
    queryKey: CONFIG_KEY,
    queryFn: api.config,
    staleTime: 5 * 60_000,
  });
  return data ?? FALLBACK;
}

export function useFeature(flag: FeatureFlag): boolean {
  return useConfig().features[flag];
}
