import type { Metadata } from "next";
import type { CSSProperties, ReactNode } from "react";

import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "HR Portal",
  description: "HR Recruitment Portal (ATS)",
};

const fontVars = {
  "--font-inter":
    'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  "--font-mono":
    '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
} as CSSProperties;

export default function RootLayout({ children }: { children: ReactNode }) {
  // System stacks avoid blocking on fonts.googleapis.com inside Docker.
  return (
    <html lang="en" className="font-sans" style={fontVars}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
