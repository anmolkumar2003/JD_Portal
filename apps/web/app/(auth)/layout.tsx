"use client";

import type { ReactNode } from "react";

import { Brand } from "@/components/brand";
import { useConfig } from "@/hooks/use-config";

export default function AuthLayout({ children }: { children: ReactNode }) {
  const { org_name, logo_data_url } = useConfig();
  return (
    <div className="flex min-h-dvh flex-col items-center bg-muted/40 px-4 py-10 sm:py-16">
      <Brand name={org_name} logoUrl={logo_data_url} className="mb-8 text-lg" />
      <div className="flex w-full flex-1 flex-col items-center justify-center">{children}</div>
      <p className="mt-10 text-center text-xs text-muted-foreground">
        HR Portal · © {new Date().getFullYear()} {org_name}
      </p>
    </div>
  );
}
