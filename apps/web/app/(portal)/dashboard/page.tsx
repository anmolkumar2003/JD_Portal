"use client";

import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { ROLE_LABELS } from "@/lib/labels";

export default function DashboardPage() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Breadcrumbs items={[{ label: "Dashboard" }]} />
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
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
    </div>
  );
}
