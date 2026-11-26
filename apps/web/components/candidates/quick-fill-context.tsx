"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { useWatch } from "react-hook-form";

import { Badge } from "@/components/ui/badge";

/**
 * Remembers which form fields Quick fill wrote, so the form can show a small "from quick fill"
 * badge next to them. The badge goes away as soon as HR changes the value by hand.
 */

interface QuickFillContextValue {
  applied: Readonly<Record<string, string>>;
  mark: (entries: Record<string, string>) => void;
  clear: (paths: string[]) => void;
  reset: () => void;
}

const QuickFillContext = createContext<QuickFillContextValue>({
  applied: {},
  mark: () => undefined,
  clear: () => undefined,
  reset: () => undefined,
});

export function QuickFillProvider({ children }: { children: ReactNode }) {
  const [applied, setApplied] = useState<Record<string, string>>({});
  const mark = useCallback(
    (entries: Record<string, string>) => setApplied((prev) => ({ ...prev, ...entries })),
    [],
  );
  const clear = useCallback(
    (paths: string[]) =>
      setApplied((prev) => {
        const next = { ...prev };
        for (const path of paths) delete next[path];
        return next;
      }),
    [],
  );
  const reset = useCallback(() => setApplied({}), []);
  const value = useMemo(() => ({ applied, mark, clear, reset }), [applied, mark, clear, reset]);
  return <QuickFillContext.Provider value={value}>{children}</QuickFillContext.Provider>;
}

export function useQuickFillMarks(): QuickFillContextValue {
  return useContext(QuickFillContext);
}

export function QuickFillBadge({ path }: { path: string }) {
  const { applied } = useQuickFillMarks();
  const current = useWatch({ name: path }) as unknown;
  const written = applied[path];
  if (written === undefined || String(current ?? "") !== written) return null;
  return (
    <Badge
      variant="secondary"
      className="ml-2 align-middle text-[10px] font-normal"
      data-testid={`quick-fill-badge-${path}`}
    >
      from quick fill
    </Badge>
  );
}
