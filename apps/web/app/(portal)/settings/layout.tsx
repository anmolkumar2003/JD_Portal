"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "@/hooks/use-auth";
import { isAdmin } from "@/lib/permissions";
import { cn } from "@/lib/utils";

const SECTIONS = [
  { href: "/settings/account", label: "My account", adminOnly: false },
  { href: "/settings/organization", label: "Organization", adminOnly: true },
  { href: "/settings/scoring", label: "Scoring", adminOnly: true },
  { href: "/settings/users", label: "Users", adminOnly: true },
  { href: "/settings/departments", label: "Departments & locations", adminOnly: true },
] as const;

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const sections = SECTIONS.filter((s) => !s.adminOnly || isAdmin(user?.role));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      <nav aria-label="Settings sections" className="-mx-1 overflow-x-auto">
        <ul className="glass flex min-w-max gap-1 rounded-xl border border-border/50 p-1">
          {sections.map(({ href, label }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex h-11 items-center rounded-lg px-3 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    active
                      ? "bg-background/80 text-foreground shadow-sm ring-1 ring-border/60"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      {children}
    </div>
  );
}
