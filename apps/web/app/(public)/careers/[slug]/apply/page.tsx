import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ApplyForm } from "@/components/careers/apply-form";
import { serverApi } from "@/lib/server-api";

interface Props {
  params: { slug: string };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const job = await serverApi.getPublicJob(params.slug);
  if (!job) notFound();
  return { title: `Apply: ${job.title}` };
}

export default async function ApplyPage({ params }: Props) {
  const [job, config] = await Promise.all([
    serverApi.getPublicJob(params.slug),
    serverApi.config(),
  ]);
  if (!job) notFound();

  return (
    <div className="container max-w-3xl py-8 sm:py-12">
      <Link
        href={`/careers/${job.slug}`}
        className="mb-6 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden />
        Back to role
      </Link>
      <div className="mb-8 space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Apply for {job.title}</h1>
        <p className="text-muted-foreground">
          It takes about 3 minutes. Fields marked optional can be left blank.
        </p>
      </div>
      <ApplyForm slug={job.slug} jobTitle={job.title} orgName={config.org_name} />
    </div>
  );
}
