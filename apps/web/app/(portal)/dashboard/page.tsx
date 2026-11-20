"use client";

import { Loader2, LogOut } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import type { Role } from "@/types/api";

const ROLE_LABELS: Record<Role, string> = {
  super_admin: "Super Admin",
  hr_admin: "HR Admin",
  recruiter: "Recruiter",
  hiring_manager: "Hiring Manager",
  interviewer: "Interviewer",
};

export default function DashboardPage() {
  const { user, logout, isLoggingOut } = useAuth();
  if (!user) return null;

  return (
    <main className="container space-y-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <Button variant="outline" onClick={() => void logout()} disabled={isLoggingOut}>
          {isLoggingOut ? <Loader2 className="animate-spin" aria-hidden /> : <LogOut aria-hidden />}
          Log out
        </Button>
      </div>
      <Card className="max-w-md">
        <CardHeader>
          <CardTitle>Welcome, {user.full_name}</CardTitle>
          <CardDescription>{user.email}</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Role</span>
          <Badge variant="secondary">{ROLE_LABELS[user.role]}</Badge>
        </CardContent>
      </Card>
      <p className="text-sm text-muted-foreground">
        KPI cards and charts arrive with the dashboard slice (DASH-01, DASH-02).
      </p>
    </main>
  );
}
