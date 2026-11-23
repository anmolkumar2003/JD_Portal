"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/hooks/use-auth";
import { isAdmin } from "@/lib/permissions";

export default function SettingsIndexPage() {
  const router = useRouter();
  const { user } = useAuth();
  useEffect(() => {
    router.replace(isAdmin(user?.role) ? "/settings/users" : "/settings/account");
  }, [router, user?.role]);
  return null;
}
