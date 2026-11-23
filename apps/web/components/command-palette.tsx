"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import {
  Briefcase,
  LayoutDashboard,
  Loader2,
  Plus,
  Search,
  Settings,
  User,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { SearchHit, SearchResult } from "@/types/api";

const SEARCH_DEBOUNCE_MS = 250;
const MIN_QUERY_LEN = 2;

interface NavCommand {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
  keywords?: string;
}

const NAV_COMMANDS: NavCommand[] = [
  { id: "dashboard", label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { id: "candidates", label: "Candidates", href: "/candidates", icon: Users },
  { id: "jobs", label: "Jobs", href: "/jobs", icon: Briefcase },
  { id: "settings", label: "Settings", href: "/settings", icon: Settings },
  { id: "add-candidate", label: "Add candidate", href: "/candidates/new", icon: Plus },
];

type PaletteItem =
  | { kind: "nav"; command: NavCommand }
  | { kind: "candidate"; hit: SearchHit }
  | { kind: "job"; hit: SearchHit };

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const requestId = useRef(0);

  const normalized = query.trim().toLowerCase();

  const navMatches = normalized
    ? NAV_COMMANDS.filter(
        (cmd) =>
          cmd.label.toLowerCase().includes(normalized) ||
          cmd.keywords?.toLowerCase().includes(normalized),
      )
    : NAV_COMMANDS;

  const items: PaletteItem[] = [
    ...navMatches.map((command) => ({ kind: "nav" as const, command })),
    ...(results?.candidates ?? []).map((hit) => ({ kind: "candidate" as const, hit })),
    ...(results?.jobs ?? []).map((hit) => ({ kind: "job" as const, hit })),
  ];

  useEffect(() => {
    setActiveIndex(0);
  }, [query, results]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setResults(null);
      setLoading(false);
      return;
    }
    const timer = window.setTimeout(() => inputRef.current?.focus(), 0);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    const q = query.trim();
    if (q.length < MIN_QUERY_LEN) {
      setResults(null);
      setLoading(false);
      return;
    }
    const id = ++requestId.current;
    setLoading(true);
    const timer = window.setTimeout(() => {
      void api
        .search(q)
        .then((data) => {
          if (requestId.current === id) {
            setResults(data);
            setLoading(false);
          }
        })
        .catch(() => {
          if (requestId.current === id) {
            setResults({ candidates: [], jobs: [] });
            setLoading(false);
          }
        });
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  const go = useCallback(
    (href: string) => {
      setOpen(false);
      router.push(href);
    },
    [router],
  );

  const onItemSelect = (item: PaletteItem) => {
    if (item.kind === "nav") go(item.command.href);
    else go(item.hit.href);
  };

  const onInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => (items.length ? (i + 1) % items.length : 0));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => (items.length ? (i - 1 + items.length) % items.length : 0));
    } else if (event.key === "Enter" && items[activeIndex]) {
      event.preventDefault();
      onItemSelect(items[activeIndex]);
    }
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content
          className="fixed left-1/2 top-[12%] z-50 flex w-full max-w-xl -translate-x-1/2 flex-col overflow-hidden rounded-lg border bg-background shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <DialogPrimitive.Title className="sr-only">Command palette</DialogPrimitive.Title>
          <div className="flex items-center gap-2 border-b px-3">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
            <input
              ref={inputRef}
              type="search"
              placeholder="Search candidates, jobs, or go to…"
              className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onInputKeyDown}
              aria-label="Command palette search"
              autoComplete="off"
            />
            {loading && (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden />
            )}
            <DialogPrimitive.Close className="rounded-sm p-1 opacity-70 hover:opacity-100">
              <X className="h-4 w-4" />
              <span className="sr-only">Close</span>
            </DialogPrimitive.Close>
          </div>
          <div className="max-h-[min(24rem,50vh)] overflow-y-auto p-2" role="listbox">
            {items.length === 0 && query.trim().length >= MIN_QUERY_LEN && !loading && (
              <p className="px-2 py-6 text-center text-sm text-muted-foreground">No results</p>
            )}
            {items.map((item, index) => {
              const active = index === activeIndex;
              if (item.kind === "nav") {
                const Icon = item.command.icon;
                return (
                  <button
                    key={item.command.id}
                    type="button"
                    role="option"
                    aria-selected={active}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm",
                      active && "bg-accent text-accent-foreground",
                    )}
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => onItemSelect(item)}
                  >
                    <Icon className="h-4 w-4 text-muted-foreground" aria-hidden />
                    <span className="font-medium">{item.command.label}</span>
                    <span className="ml-auto text-xs text-muted-foreground">Go to</span>
                  </button>
                );
              }
              const isCandidate = item.kind === "candidate";
              return (
                <button
                  key={`${item.kind}-${item.hit.id}`}
                  type="button"
                  role="option"
                  aria-selected={active}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm",
                    active && "bg-accent text-accent-foreground",
                  )}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => onItemSelect(item)}
                >
                  {isCandidate ? (
                    <User className="h-4 w-4 text-muted-foreground" aria-hidden />
                  ) : (
                    <Briefcase className="h-4 w-4 text-muted-foreground" aria-hidden />
                  )}
                  <span>
                    <span className="block font-medium">{item.hit.label}</span>
                    <span className="block text-xs text-muted-foreground">
                      {isCandidate ? item.hit.email : item.hit.slug}
                    </span>
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {isCandidate ? "Candidate" : "Job"}
                  </span>
                </button>
              );
            })}
          </div>
          <p className="border-t px-3 py-2 text-xs text-muted-foreground">
            <kbd className="rounded border bg-muted px-1">↑</kbd>{" "}
            <kbd className="rounded border bg-muted px-1">↓</kbd> navigate ·{" "}
            <kbd className="rounded border bg-muted px-1">Enter</kbd> open ·{" "}
            <kbd className="rounded border bg-muted px-1">Esc</kbd> close ·{" "}
            <kbd className="rounded border bg-muted px-1">⌘</kbd>
            <kbd className="rounded border bg-muted px-1">K</kbd> toggle
          </p>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
