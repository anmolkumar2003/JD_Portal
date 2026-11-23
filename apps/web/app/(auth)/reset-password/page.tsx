"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";

import { FormAlert } from "@/components/form-alert";
import {
  NewPasswordFields,
  newPasswordSchema,
  type NewPasswordValues,
} from "@/components/new-password-fields";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";

function ResetForm() {
  const token = useSearchParams().get("token") ?? "";
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<NewPasswordValues>({ resolver: zodResolver(newPasswordSchema()) });

  const onSubmit = handleSubmit(async ({ new_password }) => {
    setError(null);
    try {
      await api.auth.resetPassword(token, new_password);
      setDone(true);
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.code !== "network_error"
          ? cause.code === "invalid_token"
            ? "This reset link has expired or was already used. Request a new one."
            : cause.message
          : "Could not reach the server. Please try again.",
      );
    }
  });

  if (!token) {
    return (
      <FormAlert>
        This page needs the link from your reset email.{" "}
        <Link href="/forgot-password" className="underline">
          Request a new link
        </Link>
        .
      </FormAlert>
    );
  }

  if (done) {
    return (
      <div className="space-y-4">
        <FormAlert tone="success">Your password has been changed.</FormAlert>
        <Button asChild className="w-full">
          <Link href="/login">Sign in</Link>
        </Button>
      </div>
    );
  }

  return (
    <form className="space-y-4" onSubmit={onSubmit} noValidate>
      {error && <FormAlert>{error}</FormAlert>}
      <NewPasswordFields register={register} errors={errors} />
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
        Set new password
      </Button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Choose a new password</CardTitle>
        <CardDescription>You will sign in with it from now on.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Suspense fallback={<div className="h-48 animate-pulse rounded-md bg-muted" />}>
          <ResetForm />
        </Suspense>
        <p className="text-center text-sm">
          <Link href="/login" className="text-primary underline-offset-4 hover:underline">
            Back to sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
