"use client";

import { ChangePasswordForm } from "@/components/settings/change-password-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { ROLE_LABELS } from "@/lib/labels";

export default function AccountSettingsPage() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>An admin can change your name, email or role.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-3 text-sm sm:grid-cols-[8rem_1fr]">
            <dt className="text-muted-foreground">Name</dt>
            <dd className="font-medium">{user.full_name}</dd>
            <dt className="text-muted-foreground">Email</dt>
            <dd className="break-all font-medium">{user.email}</dd>
            <dt className="text-muted-foreground">Role</dt>
            <dd className="font-medium">{ROLE_LABELS[user.role]}</dd>
          </dl>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Change password</CardTitle>
          <CardDescription>Other devices will be signed out.</CardDescription>
        </CardHeader>
        <CardContent>
          <ChangePasswordForm email={user.email} />
        </CardContent>
      </Card>
    </div>
  );
}
