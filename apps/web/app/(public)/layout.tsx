import Link from "next/link";
import type { ReactNode } from "react";

import { Brand } from "@/components/brand";
import { serverApi } from "@/lib/server-api";

export default async function PublicLayout({ children }: { children: ReactNode }) {
  const { org_name, logo_data_url } = await serverApi.config();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="glass sticky top-0 z-40 border-b border-border/40">
        <div className="container flex h-14 items-center justify-between gap-4">
          <Link href="/careers">
            <Brand name={`${org_name} Careers`} logoUrl={logo_data_url} />
          </Link>
          <nav aria-label="Site" className="flex items-center gap-4 text-sm">
            <Link
              href="/careers"
              className="rounded-lg px-3 py-2 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
            >
              Open roles
            </Link>
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="glass border-t border-border/40">
        <div className="container py-6 text-sm text-muted-foreground">
          © {new Date().getFullYear()} {org_name}. Equal opportunity employer.
        </div>
      </footer>
    </div>
  );
}
