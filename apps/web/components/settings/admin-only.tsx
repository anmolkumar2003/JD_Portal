"use client";

import { ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";

import { EmptyState } from "@/components/empty-state";
import { useAuth } from "@/hooks/use-auth";
import { isAdmin } from "@/lib/permissions";

/** UI guard only; the API enforces the same rule. */
export function AdminOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (!isAdmin(user?.role)) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="Admins only"
        description="Ask an HR admin if you need something changed here."
      />
    );
  }
  return <>{children}</>;
}
