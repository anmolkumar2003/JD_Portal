"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { FormAlert } from "@/components/form-alert";
import { NewPasswordFields, newPasswordSchema } from "@/components/new-password-fields";
import { PasswordInput } from "@/components/password-field";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";
import { ApiError } from "@/lib/api";

interface ChangePasswordFormProps {
  email: string;
  submitLabel?: string;
  onDone?: () => void;
}

export function ChangePasswordForm({
  email,
  submitLabel = "Change password",
  onDone,
}: ChangePasswordFormProps) {
  const { changePassword } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const schema = newPasswordSchema(email).and(
    z.object({ current_password: z.string().min(1, "Enter your current password") }),
  );
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async ({ current_password, new_password }) => {
    setError(null);
    try {
      await changePassword({ current_password, new_password });
      reset();
      toast.success("Password changed");
      onDone?.();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Could not change the password.");
    }
  });

  return (
    <form className="space-y-4" onSubmit={onSubmit} noValidate>
      {error && <FormAlert>{error}</FormAlert>}
      <div className="space-y-2">
        <Label htmlFor="current_password">Current password</Label>
        <PasswordInput
          id="current_password"
          autoComplete="current-password"
          aria-invalid={errors.current_password ? true : undefined}
          aria-describedby={errors.current_password ? "current_password-error" : undefined}
          {...register("current_password")}
        />
        {errors.current_password && (
          <p id="current_password-error" className="text-sm text-destructive">
            {errors.current_password.message}
          </p>
        )}
      </div>
      <NewPasswordFields register={register} errors={errors} />
      <Button type="submit" className="w-full sm:w-auto" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
        {submitLabel}
      </Button>
    </form>
  );
}
