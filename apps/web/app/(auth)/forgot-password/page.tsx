"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormAlert } from "@/components/form-alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

const schema = z.object({ email: z.email("Enter a valid email address") });

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async ({ email }) => {
    setError(null);
    try {
      await api.auth.forgotPassword(email);
      setSent(true);
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.status === 429
          ? "Too many requests. Please wait a while and try again."
          : "Could not send the email. Please try again.",
      );
    }
  });

  return (
    <Card className="glass-strong w-full max-w-sm shadow-glass-lg">
      <CardHeader>
        <CardTitle>Reset your password</CardTitle>
        <CardDescription>
          Enter your work email and we will send you a link to choose a new password.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {sent ? (
          <FormAlert tone="success">
            If an account exists for that email, a reset link is on its way. The link works for a
            limited time. Check your spam folder if it does not arrive.
          </FormAlert>
        ) : (
          <form className="space-y-4" onSubmit={onSubmit} noValidate>
            {error && <FormAlert>{error}</FormAlert>}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                autoFocus
                aria-invalid={errors.email ? true : undefined}
                aria-describedby={errors.email ? "email-error" : undefined}
                {...register("email")}
              />
              {errors.email && (
                <p id="email-error" className="text-sm text-destructive">
                  {errors.email.message}
                </p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
              Send reset link
            </Button>
          </form>
        )}
        <p className="text-center text-sm">
          <Link
            href="/login"
            className="inline-flex min-h-11 items-center text-primary underline-offset-4 hover:underline"
          >
            Back to sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
