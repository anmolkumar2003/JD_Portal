"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { TopBar } from "@/components/layout/top-bar";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";

const SIDEBAR_KEY = "hr-portal:sidebar-collapsed";

function PortalSkeleton() {
  return (
    <div className="flex h-screen" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-full w-60 rounded-none" />
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
      <AppSidebar collapsed={collapsed} onToggle={toggleSidebar} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main ref={mainRef} className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-6xl p-6 lg:p-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
