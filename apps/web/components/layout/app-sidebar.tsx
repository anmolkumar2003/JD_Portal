"use client";

import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { Brand } from "@/components/brand";
import { SidebarNav } from "@/components/layout/sidebar-nav";
import { useConfig } from "@/hooks/use-config";
import { cn } from "@/lib/utils";

interface AppSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  className?: string;
}

export function AppSidebar({ collapsed, onToggle, className }: AppSidebarProps) {
  const { org_name, logo_data_url } = useConfig();

  return (
    <aside
      className={cn(
        "glass relative z-20 flex h-full shrink-0 flex-col rounded-[var(--radius)] transition-[width] duration-200 ease-out",
        collapsed ? "w-16" : "w-64",
        className,
      )}
    >
      <div
        className={cn(
          "flex items-center border-b border-border/40 px-3",
          collapsed ? "h-14 justify-center" : "min-h-14 py-2.5",
        )}
      >
        <Brand name={org_name} logoUrl={logo_data_url} showName={!collapsed} className="w-full" />
      </div>

      <SidebarNav collapsed={collapsed} className="flex-1" />

      <div className="border-t border-border/40 p-2">
        <button
          type="button"
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          className={cn(
            "flex h-10 w-full items-center gap-3 rounded-pill px-3 text-sm text-muted-foreground transition-colors duration-180 hover:bg-muted/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            collapsed && "justify-center px-0",
          )}
        >
          {collapsed ? (
            <PanelLeftOpen className="h-4 w-4" aria-hidden />
          ) : (
            <>
              <PanelLeftClose className="h-4 w-4" aria-hidden />
              Collapse
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
