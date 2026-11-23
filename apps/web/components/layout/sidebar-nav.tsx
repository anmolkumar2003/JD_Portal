"use client";

import { Briefcase, Globe, LayoutDashboard, Settings, Users, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useConfig } from "@/hooks/use-config";
import { cn } from "@/lib/utils";
import type { FeatureFlag } from "@/types/api";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  feature?: FeatureFlag;
  external?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/candidates", label: "Candidates", icon: Users },
  {
    href: "/careers",
    label: "Careers site",
    icon: Globe,
    feature: "public_careers",
    external: true,
  },
  { href: "/settings", label: "Settings", icon: Settings },
];

interface SidebarNavProps {
  collapsed?: boolean;
  onNavigate?: () => void;
  className?: string;
}

export function SidebarNav({ collapsed = false, onNavigate, className }: SidebarNavProps) {
  const pathname = usePathname();
  const { features } = useConfig();
  const items = NAV_ITEMS.filter((item) => !item.feature || features[item.feature]);

  return (
    <nav aria-label="Main" className={cn("flex-1 space-y-1 p-2", className)}>
      {items.map(({ href, label, icon: Icon, external }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            target={external ? "_blank" : undefined}
            rel={external ? "noopener" : undefined}
            title={collapsed ? label : undefined}
            aria-current={active ? "page" : undefined}
            onClick={() => onNavigate?.()}
            className={cn(
              "group flex min-h-11 items-center gap-3 rounded-2xl px-3 text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              active
                ? "bg-primary/15 text-primary shadow-sm"
                : "text-muted-foreground hover:bg-white/40 hover:text-foreground dark:hover:bg-white/5",
              collapsed && "justify-center px-0",
            )}
          >
            <Icon
              className={cn(
                "h-4 w-4 shrink-0 transition-colors",
                active ? "text-primary" : "text-muted-foreground group-hover:text-foreground",
              )}
              aria-hidden
            />
            {collapsed ? <span className="sr-only">{label}</span> : label}
          </Link>
        );
      })}
    </nav>
  );
}
