"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

import { ChangePasswordForm } from "@/components/settings/change-password-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";

function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";
}

function ChangePassword() {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const { user, isLoading, logout } = useAuth();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (!user) return <div className="h-80 w-full max-w-sm animate-pulse rounded-lg bg-muted" />;

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Set your own password</CardTitle>
        <CardDescription>
          {user.must_change_password
            ? "You signed in with a temporary password. Choose a new one to continue."
            : "Choose a new password for your account."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ChangePasswordForm
          email={user.email}
          submitLabel="Save and continue"
          onDone={() => router.replace(next)}
        />
        <Button variant="ghost" className="w-full" onClick={() => void logout()}>
          Sign out instead
        </Button>
      </CardContent>
    </Card>
  );
}

export default function ChangePasswordPage() {
  return (
    <Suspense fallback={<div className="h-80 w-full max-w-sm animate-pulse rounded-lg bg-muted" />}>
      <ChangePassword />
    </Suspense>
  );
}
