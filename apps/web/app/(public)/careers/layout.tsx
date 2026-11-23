import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { serverApi } from "@/lib/server-api";

export async function generateMetadata(): Promise<Metadata> {
  const { org_name } = await serverApi.config();
  return {
    title: { template: `%s · ${org_name} Careers`, default: `Careers at ${org_name}` },
    description: `Explore open roles at ${org_name} and apply online.`,
  };
}

/** The public careers site is optional (ENABLE_PUBLIC_CAREERS); when off it does not exist. */
export default async function CareersLayout({ children }: { children: ReactNode }) {
  const { features } = await serverApi.config();
  if (!features.public_careers) notFound();
  return children;
}
