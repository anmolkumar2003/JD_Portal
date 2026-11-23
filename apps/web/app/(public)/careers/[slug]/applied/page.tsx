import { CheckCircle2, Mail } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Application received",
  robots: { index: false },
};

interface Props {
  params: { slug: string };
  searchParams: { ref?: string; title?: string };
}

export default function AppliedPage({ searchParams }: Props) {
  const reference = searchParams.ref;
  const title = searchParams.title;

  return (
    <div className="container flex justify-center py-12 sm:py-20">
      <Card className="w-full max-w-lg text-center">
        <CardContent className="space-y-6 pt-10">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-success/15">
            <CheckCircle2 className="h-8 w-8 text-success" aria-hidden />
          </div>
          <div className="space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight">Application received</h1>
            <p className="text-muted-foreground">
              Thank you for applying{title ? ` for ${title}` : ""}. Our recruiting team will review
              your application and get in touch.
            </p>
          </div>
          {reference && (
            <div className="rounded-lg border bg-muted/50 p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Your reference number
              </p>
              <p className="mt-1 font-mono text-xl font-semibold" data-testid="reference-no">
                {reference}
              </p>
            </div>
          )}
          <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Mail className="h-4 w-4" aria-hidden />
            We&apos;ve sent a confirmation to your email.
          </p>
          <Button asChild variant="outline" className="w-full sm:w-auto">
            <Link href="/careers">Browse more roles</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
