import type { ReactNode } from "react";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b bg-card">
        <div className="container flex h-14 items-center">
          <span className="font-semibold">HR Portal</span>
        </div>
      </header>
      <main className="container flex-1 py-10">{children}</main>
    </div>
  );
}
