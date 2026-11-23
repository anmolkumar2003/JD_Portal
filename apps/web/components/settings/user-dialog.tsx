"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ROLE_LABELS } from "@/lib/labels";
import type { AssignableRole, Role, User } from "@/types/api";

export const ASSIGNABLE_ROLES: AssignableRole[] = ["hr_admin", "recruiter", "super_admin"];
const ROLES = ASSIGNABLE_ROLES;

const schema = z.object({
  full_name: z.string().trim().min(1, "Enter a name").max(200),
  email: z.email("Enter a valid email address"),
  // Older accounts may still hold a retired role; it is kept unless the admin picks another.
  role: z.string(),
});

export type UserFormValues = z.infer<typeof schema>;

interface UserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Editing this user; creating a new one when undefined. */
  user?: User;
  canGrantSuperAdmin: boolean;
  busy: boolean;
  onSubmit: (values: UserFormValues) => void;
}

export function UserDialog({
  open,
  onOpenChange,
  user,
  canGrantSuperAdmin,
  busy,
  onSubmit,
}: UserDialogProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<UserFormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (!open) return;
    reset({
      full_name: user?.full_name ?? "",
      email: user?.email ?? "",
      role: user?.role ?? "recruiter",
    });
  }, [open, user, reset]);

  const roles: string[] = ROLES.filter(
    (r) => r !== "super_admin" || canGrantSuperAdmin || user?.role === r,
  );
  if (user && !roles.includes(user.role)) roles.push(user.role);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{user ? "Edit user" : "Add user"}</DialogTitle>
          <DialogDescription>
            {user
              ? "Changes apply the next time they sign in."
              : "They get a temporary password and must change it when they first sign in."}
          </DialogDescription>
        </DialogHeader>
        <form id="user-form" className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="space-y-2">
            <Label htmlFor="user-name">Full name</Label>
            <Input
              id="user-name"
              autoComplete="off"
              aria-invalid={errors.full_name ? true : undefined}
              {...register("full_name")}
            />
            {errors.full_name && (
              <p className="text-sm text-destructive">{errors.full_name.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="user-email">Work email</Label>
            <Input
              id="user-email"
              type="email"
              autoComplete="off"
              aria-invalid={errors.email ? true : undefined}
              {...register("email")}
            />
            {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="user-role">Role</Label>
            <Select id="user-role" {...register("role")}>
              {roles.map((role) => (
                <option key={role} value={role}>
                  {ROLE_LABELS[role as Role]}
                  {(ROLES as string[]).includes(role) ? "" : " (retired role)"}
                </option>
              ))}
            </Select>
            <p className="text-sm text-muted-foreground">
              HR Admins manage users and settings. Recruiters work with jobs and candidates.
            </p>
          </div>
        </form>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="user-form" disabled={busy}>
            {busy && <Loader2 className="animate-spin" aria-hidden />}
            {user ? "Save changes" : "Create user"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
