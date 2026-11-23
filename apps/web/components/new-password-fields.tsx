"use client";

import type { FieldErrors, UseFormRegister } from "react-hook-form";
import { z } from "zod";

import { PasswordInput } from "@/components/password-field";
import { Label } from "@/components/ui/label";
import { MIN_PASSWORD_LENGTH, passwordProblems } from "@/lib/password";

export interface NewPasswordValues {
  new_password: string;
  confirm_password: string;
}

/** New + confirm password, checked with the same rules as the API. */
export function newPasswordSchema(email?: string) {
  return z
    .object({
      new_password: z.string(),
      confirm_password: z.string(),
    })
    .superRefine((values, ctx) => {
      const problems = passwordProblems(values.new_password, email);
      if (problems.length) {
        ctx.addIssue({ code: "custom", path: ["new_password"], message: problems.join(" ") });
      }
      if (values.confirm_password !== values.new_password) {
        ctx.addIssue({
          code: "custom",
          path: ["confirm_password"],
          message: "Passwords do not match.",
        });
      }
    });
}

interface NewPasswordFieldsProps<T extends NewPasswordValues> {
  register: UseFormRegister<T>;
  errors: FieldErrors<NewPasswordValues>;
}

export function NewPasswordFields<T extends NewPasswordValues>({
  register,
  errors,
}: NewPasswordFieldsProps<T>) {
  const reg = register as unknown as UseFormRegister<NewPasswordValues>;
  return (
    <>
      <div className="space-y-2">
        <Label htmlFor="new_password">New password</Label>
        <PasswordInput
          id="new_password"
          autoComplete="new-password"
          aria-invalid={errors.new_password ? true : undefined}
          aria-describedby="new_password-help"
          {...reg("new_password")}
        />
        <p
          id="new_password-help"
          className={
            errors.new_password ? "text-sm text-destructive" : "text-sm text-muted-foreground"
          }
        >
          {errors.new_password?.message ??
            `At least ${MIN_PASSWORD_LENGTH} characters, mixing upper and lower case, numbers or symbols.`}
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="confirm_password">Confirm new password</Label>
        <PasswordInput
          id="confirm_password"
          autoComplete="new-password"
          aria-invalid={errors.confirm_password ? true : undefined}
          aria-describedby={errors.confirm_password ? "confirm_password-error" : undefined}
          {...reg("confirm_password")}
        />
        {errors.confirm_password && (
          <p id="confirm_password-error" className="text-sm text-destructive">
            {errors.confirm_password.message}
          </p>
        )}
      </div>
    </>
  );
}
