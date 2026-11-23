"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { AdminOnly } from "@/components/settings/admin-only";
import { LookupManager } from "@/components/settings/lookup-manager";
import { api, ApiError } from "@/lib/api";

const fail = (error: unknown) =>
  toast.error(error instanceof ApiError ? error.message : "Something went wrong");

function Departments() {
  const queryClient = useQueryClient();
  const list = useQuery({
    queryKey: ["departments", "all"],
    queryFn: () => api.org.departments(true),
  });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["departments"] });

  const create = useMutation({
    mutationFn: api.org.createDepartment,
    onSuccess: (d) => {
      toast.success(`Added ${d.name}`);
      refresh();
    },
    onError: fail,
  });
  const update = useMutation({
    mutationFn: ({ id, ...body }: { id: string; name?: string; is_active?: boolean }) =>
      api.org.updateDepartment(id, body),
    onSuccess: (d, vars) => {
      toast.success(
        vars.is_active === undefined
          ? "Department renamed"
          : `${d.name} ${d.is_active ? "activated" : "deactivated"}`,
      );
      refresh();
    },
    onError: fail,
  });

  return (
    <LookupManager
      title="Departments"
      description="Used on jobs, candidates and filters."
      noun="department"
      items={list.data}
      isPending={list.isPending}
      error={list.error}
      onRetry={() => void list.refetch()}
      busy={create.isPending}
      onCreate={(name) => create.mutateAsync(name)}
      onRename={(id, name) => update.mutateAsync({ id, name })}
      onToggle={(id, is_active) => update.mutate({ id, is_active })}
    />
  );
}

function Locations() {
  const queryClient = useQueryClient();
  const list = useQuery({
    queryKey: ["locations", "all"],
    queryFn: () => api.org.locations(true),
  });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["locations"] });

  const create = useMutation({
    mutationFn: (name: string) => api.org.createLocation({ name }),
    onSuccess: (l) => {
      toast.success(`Added ${l.name}`);
      refresh();
    },
    onError: fail,
  });
  const update = useMutation({
    mutationFn: ({ id, ...body }: { id: string; name?: string; is_active?: boolean }) =>
      api.org.updateLocation(id, body),
    onSuccess: (l, vars) => {
      toast.success(
        vars.is_active === undefined
          ? "Location renamed"
          : `${l.name} ${l.is_active ? "activated" : "deactivated"}`,
      );
      refresh();
    },
    onError: fail,
  });

  return (
    <LookupManager
      title="Locations"
      description="Offices or cities shown on jobs."
      noun="location"
      items={list.data?.map((l) => ({
        ...l,
        detail: [l.city, l.country].filter(Boolean).join(", ") || null,
      }))}
      isPending={list.isPending}
      error={list.error}
      onRetry={() => void list.refetch()}
      busy={create.isPending}
      onCreate={(name) => create.mutateAsync(name)}
      onRename={(id, name) => update.mutateAsync({ id, name })}
      onToggle={(id, is_active) => update.mutate({ id, is_active })}
    />
  );
}

export default function DepartmentsSettingsPage() {
  return (
    <AdminOnly>
      <div className="grid gap-6 lg:grid-cols-2">
        <Departments />
        <Locations />
      </div>
    </AdminOnly>
  );
}
