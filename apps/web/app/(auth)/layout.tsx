"use client";

import type { ReactNode } from "react";

import { Brand } from "@/components/brand";
import { useConfig } from "@/hooks/use-config";

export default function AuthLayout({ children }: { children: ReactNode }) {
  const { org_name, logo_data_url } = useConfig();
  return (
    <div className="flex min-h-dvh flex-col items-center bg-muted/40 px-4 py-10 sm:py-16">
      <Brand name={org_name} logoUrl={logo_data_url} className="mb-8 text-lg" />
      <div className="flex w-full justify-center">{children}</div>
    </div>
  );
}
