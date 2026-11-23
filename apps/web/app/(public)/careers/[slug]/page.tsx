import { ArrowLeft, Briefcase, Building2, CalendarDays, MapPin, Users } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EMPLOYMENT_TYPE_LABELS, WORK_MODE_LABELS, formatDate } from "@/lib/labels";
import { serverApi } from "@/lib/server-api";

interface Props {
  params: { slug: string };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const job = await serverApi.getPublicJob(params.slug);
  // Resolved before streaming starts, so a missing job still gets a real 404 status.
  if (!job) notFound();
  return {
    title: job.title,
    description: job.description.slice(0, 160),
  };
}

function Section({ title, text }: { title: string; text: string | null }) {
  if (!text?.trim()) return null;
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="whitespace-pre-line leading-relaxed text-muted-foreground">{text}</p>
    </section>
  );
}

function Fact({ icon, label, value }: { icon: ReactNode; label: string; value: ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 text-muted-foreground">{icon}</span>
      <div>
        <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
        <dd className="text-sm font-medium">{value}</dd>
      </div>
    </div>
  );
}

function SkillList({ title, skills }: { title: string; skills: string[] }) {
  if (skills.length === 0) return null;
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      <ul className="flex flex-wrap gap-2">
        {skills.map((skill) => (
          <li
            key={skill}
            className="rounded-full border bg-secondary px-3 py-1 text-xs font-medium"
          >
            {skill}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default async function CareerJobPage({ params }: Props) {
  const job = await serverApi.getPublicJob(params.slug);
  if (!job) notFound();

  const applyHref = `/careers/${job.slug}/apply`;
  const experience = job.min_experience ? `${Number(job.min_experience)}+ years` : null;

  return (
    <div className="container py-8 sm:py-12">
      <Link
        href="/careers"
        className="mb-6 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden />
        All open roles
      </Link>

      <div className="grid gap-8 lg:grid-cols-3">
        <article className="space-y-8 lg:col-span-2">
          <header className="space-y-3">
            <h1 className="text-3xl font-semibold tracking-tight">{job.title}</h1>
            <p className="text-muted-foreground">
              {[job.department?.name, job.location?.name, WORK_MODE_LABELS[job.work_mode]]
                .filter(Boolean)
                .join(" · ")}
            </p>
            <Button asChild size="lg" className="lg:hidden">
              <Link href={applyHref}>Apply for this role</Link>
            </Button>
          </header>
          <Section title="About the role" text={job.description} />
          <Section title="What you'll do" text={job.responsibilities} />
          <Section title="What we're looking for" text={job.qualifications} />
          {(job.required_skills.length > 0 || job.preferred_skills.length > 0) && (
            <section className="space-y-4">
              <h2 className="text-lg font-semibold">Skills</h2>
              <SkillList title="Must have" skills={job.required_skills} />
              <SkillList title="Nice to have" skills={job.preferred_skills} />
            </section>
          )}
        </article>

        <aside>
          <Card className="lg:sticky lg:top-6">
            <CardContent className="space-y-6 pt-6">
              <dl className="space-y-4">
                {job.department && (
                  <Fact
                    icon={<Building2 className="h-4 w-4" />}
                    label="Department"
                    value={job.department.name}
                  />
                )}
                {job.location && (
                  <Fact
                    icon={<MapPin className="h-4 w-4" />}
                    label="Location"
                    value={job.location.name}
                  />
                )}
                <Fact
                  icon={<Briefcase className="h-4 w-4" />}
                  label="Employment"
                  value={`${EMPLOYMENT_TYPE_LABELS[job.employment_type]} · ${WORK_MODE_LABELS[job.work_mode]}`}
                />
                {experience && (
                  <Fact
                    icon={<Users className="h-4 w-4" />}
                    label="Experience"
                    value={experience}
                  />
                )}
                <Fact
                  icon={<CalendarDays className="h-4 w-4" />}
                  label={job.closes_at ? "Apply by" : "Posted"}
                  value={formatDate(job.closes_at ?? job.published_at)}
                />
              </dl>
              <Button asChild size="lg" className="w-full">
                <Link href={applyHref}>Apply for this role</Link>
              </Button>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}
