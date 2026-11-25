"use client";

import { Bell, ChevronDown, Loader2, LogOut, Menu, Search, UserCog } from "lucide-react";
import Link from "next/link";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from "@/hooks/use-notifications";
import { ROLE_LABELS, formatDateTime } from "@/lib/labels";
import { cn } from "@/lib/utils";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function notificationText(type: string, payload: Record<string, unknown>): string {
  const title = payload.title ?? payload.subject ?? payload.message;
  if (typeof title === "string") return title;
  return type.replace(/_/g, " ");
}

function openCommandPalette() {
  window.dispatchEvent(new Event("hr-portal:open-command-palette"));
}

interface TopBarProps {
  onOpenNav?: () => void;
}

export function TopBar({ onOpenNav }: TopBarProps) {
  const { user, logout } = useAuth();
  const notifications = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();

  if (!user) return null;

  const unread = (notifications.data ?? []).filter((n) => !n.read_at).length;

  return (
    <header className="glass relative z-10 mb-2 flex h-14 shrink-0 items-center gap-2 rounded-[var(--radius)] px-3 sm:gap-3 sm:px-4">
      {onOpenNav && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label="Open navigation"
          onClick={onOpenNav}
        >
          <Menu className="h-5 w-5" aria-hidden />
        </Button>
      )}

      <button
        type="button"
        onClick={openCommandPalette}
        className="flex h-10 min-w-0 flex-1 items-center gap-2 rounded-pill border border-border/50 bg-background/70 px-3 text-sm text-muted-foreground transition-colors duration-180 hover:bg-background hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:max-w-md"
        aria-label="Open search (Command or Control K)"
      >
        <Search className="h-4 w-4 shrink-0" aria-hidden />
        <span className="truncate">Search candidates, jobs…</span>
        <kbd className="ml-auto hidden rounded-control border border-border/60 bg-muted/80 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground sm:inline-block">
          ⌘K
        </kbd>
      </button>

      <div className="ml-auto flex items-center gap-1 sm:gap-2">
        <ThemeToggle />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
              <Bell className="h-5 w-5" aria-hidden />
              {unread > 0 && (
                <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-pill bg-gradient-brand px-1 text-[10px] font-semibold text-primary-foreground">
                  {unread > 9 ? "9+" : unread}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel className="flex items-center justify-between gap-2">
              <span>Notifications</span>
              {unread > 0 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-auto px-2 py-0 text-xs"
                  disabled={markAll.isPending}
                  onClick={() => markAll.mutate()}
                >
                  Mark all read
                </Button>
              )}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {notifications.isPending && (
              <div className="flex justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden />
              </div>
            )}
            {notifications.isSuccess && notifications.data.length === 0 && (
              <p className="px-2 py-4 text-center text-sm text-muted-foreground">No notifications</p>
            )}
            {notifications.data?.map((item) => (
              <DropdownMenuItem
                key={item.id}
                className={cn(
                  "flex flex-col items-start gap-0.5 py-2",
                  !item.read_at && "bg-muted/50",
                )}
                onSelect={() => {
                  if (!item.read_at) markRead.mutate(item.id);
                }}
              >
                <span className="text-sm font-medium">
                  {notificationText(item.type, item.payload)}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatDateTime(item.created_at)}
                </span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center gap-2 rounded-pill px-2 py-1.5 text-sm transition-colors duration-180 hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <span
              className="flex h-8 w-8 items-center justify-center rounded-pill bg-gradient-brand text-xs font-semibold text-primary-foreground"
              aria-hidden
            >
              {initials(user.full_name)}
            </span>
            <span className="hidden text-left sm:block">
              <span className="block font-medium leading-tight">{user.full_name}</span>
              <span className="block text-xs text-muted-foreground">{ROLE_LABELS[user.role]}</span>
            </span>
            <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden />
            <span className="sr-only">Open user menu</span>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>
              <span className="block font-medium">{user.full_name}</span>
              <span className="block text-xs font-normal text-muted-foreground">{user.email}</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/settings/account">
                <UserCog aria-hidden />
                My account
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => void logout()}>
              <LogOut aria-hidden />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
