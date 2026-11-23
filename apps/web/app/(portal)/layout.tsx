"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Brand } from "@/components/brand";
import { CommandPalette } from "@/components/command-palette";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { SidebarNav } from "@/components/layout/sidebar-nav";
import { TopBar } from "@/components/layout/top-bar";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useConfig } from "@/hooks/use-config";
import { useAuth } from "@/hooks/use-auth";

const SIDEBAR_KEY = "hr-portal:sidebar-collapsed";

function PortalSkeleton() {
  return (
    <div className="flex h-screen" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-full w-72 rounded-none" />
      <div className="flex-1 space-y-4 p-8">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}

export default function PortalLayout({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const { org_name, logo_data_url } = useConfig();
  const mainRef = useRef<HTMLElement>(null);
  // A session that ends while the portal is open (logout) should not deep-link the next user.
  const hadUser = useRef(false);
  if (user) hadUser.current = true;

  useEffect(() => {
    setCollapsed(window.localStorage.getItem(SIDEBAR_KEY) === "1");
  }, []);

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace(hadUser.current ? "/login" : `/login?next=${encodeURIComponent(pathname)}`);
    } else if (user.must_change_password) {
      router.replace(`/change-password?next=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, user, pathname, router]);

  useEffect(() => {
    mainRef.current?.scrollTo({ top: 0 });
  }, [pathname]);

  const toggleSidebar = () => {
    setCollapsed((value) => {
      window.localStorage.setItem(SIDEBAR_KEY, value ? "0" : "1");
      return !value;
    });
  };

  if (isLoading || !user || user.must_change_password) {
    return <PortalSkeleton />;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <CommandPalette />
      <AppSidebar collapsed={collapsed} onToggle={toggleSidebar} className="hidden md:flex" />
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-[min(100vw,16rem)] gap-0 p-0 sm:max-w-xs">
          <div className="flex h-14 items-center border-b px-4">
            <Brand name={org_name} logoUrl={logo_data_url} />
          </div>
          <SidebarNav onNavigate={() => setMobileNavOpen(false)} className="p-3" />
        </SheetContent>
      </Sheet>
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onOpenNav={() => setMobileNavOpen(true)} />
        <main ref={mainRef} className="flex-1 overflow-y-auto overflow-x-hidden">
          <div className="mx-auto max-w-6xl p-4 sm:p-6 lg:p-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
