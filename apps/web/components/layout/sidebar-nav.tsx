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

interface NavGroup {
  label: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Recruitment",
    items: [
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
    ],
  },
  {
    label: "Admin",
    items: [{ href: "/settings", label: "Settings", icon: Settings }],
  },
];

interface SidebarNavProps {
  collapsed?: boolean;
  onNavigate?: () => void;
  className?: string;
}

export function SidebarNav({ collapsed = false, onNavigate, className }: SidebarNavProps) {
  const pathname = usePathname();
  const { features } = useConfig();

  return (
    <nav aria-label="Main" className={cn("flex-1 space-y-5 overflow-y-auto p-2", className)}>
      {NAV_GROUPS.map((group) => {
        const items = group.items.filter((item) => !item.feature || features[item.feature]);
        if (items.length === 0) return null;
        return (
          <div key={group.label} className="space-y-1">
            {!collapsed && (
              <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {group.label}
              </p>
            )}
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
                    "group flex min-h-11 items-center gap-3 rounded-pill px-3 text-sm font-medium transition-all duration-180 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    active
                      ? "bg-gradient-brand-soft text-primary shadow-sm ring-1 ring-primary/15"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
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
          </div>
        );
      })}
    </nav>
  );
}
