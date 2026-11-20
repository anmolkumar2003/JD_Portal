import Link from "next/link";
import type { ReactNode } from "react";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b bg-card">
        <div className="container flex h-14 items-center justify-between gap-4">
          <Link href="/careers" className="flex items-center gap-2 font-semibold">
            <span
              className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-sm text-primary-foreground"
              aria-hidden
            >
              HR
            </span>
            Acme Careers
          </Link>
          <nav aria-label="Site" className="flex items-center gap-4 text-sm">
            <Link href="/careers" className="text-muted-foreground hover:text-foreground">
              Open roles
            </Link>
            <Link href="/login" className="text-muted-foreground hover:text-foreground">
              Staff sign in
            </Link>
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t bg-card">
        <div className="container py-6 text-sm text-muted-foreground">
          © {new Date().getFullYear()} Acme Corp. Equal opportunity employer.
        </div>
      </footer>
    </div>
  );
}
