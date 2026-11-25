"use client";

import type { ReactNode } from "react";

import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { useConfig } from "@/hooks/use-config";

export default function AuthLayout({ children }: { children: ReactNode }) {
  const { org_name, logo_data_url } = useConfig();
  return (
    <div className="relative flex min-h-dvh flex-col items-center px-4 py-10 sm:py-16">
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
        <div className="absolute -left-24 top-0 h-72 w-72 rounded-full bg-primary/15 blur-3xl" />
        <div className="absolute -right-16 top-24 h-64 w-64 rounded-full bg-violet/20 blur-3xl" />
      </div>
      <div className="relative z-10 mb-8 flex w-full max-w-sm items-center justify-between">
        <Brand name={org_name} logoUrl={logo_data_url} className="text-lg" />
        <ThemeToggle />
      </div>
      <div className="relative z-10 flex w-full flex-1 flex-col items-center justify-center">
        {children}
      </div>
      <p className="relative z-10 mt-10 text-center text-xs text-muted-foreground">
        HR Portal · © {new Date().getFullYear()} {org_name}
      </p>
    </div>
  );
}
