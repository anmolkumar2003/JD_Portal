"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, MoreHorizontal, Pencil, Plus, UserCheck, UserX, Users } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog, type ConfirmRequest } from "@/components/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { AdminOnly } from "@/components/settings/admin-only";
import { TemporaryPasswordDialog } from "@/components/settings/temporary-password-dialog";
import {
  ASSIGNABLE_ROLES,
  UserDialog,
  type UserFormValues,
} from "@/components/settings/user-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/hooks/use-auth";
import { api, ApiError } from "@/lib/api";
import { ROLE_LABELS } from "@/lib/labels";
import type { AssignableRole, User, UserPatchInput } from "@/types/api";

const USERS_KEY = ["users", "admin-list"] as const;

function formatDate(value: string | null): string {
  return value
    ? new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })
    : "Never";
}

function StatusBadge({ user }: { user: User }) {
  if (!user.is_active) return <Badge variant="secondary">Deactivated</Badge>;
  if (user.must_change_password) return <Badge variant="warning">Awaiting first sign-in</Badge>;
  return <Badge variant="success">Active</Badge>;
}

function UsersAdmin() {
  const { user: me } = useAuth();
  const queryClient = useQueryClient();
  const users = useQuery({ queryKey: USERS_KEY, queryFn: api.users.list });
  const [dialog, setDialog] = useState<{ open: boolean; user?: User }>({ open: false });
  const [secret, setSecret] = useState<{ email: string; password: string } | null>(null);
  const [confirm, setConfirm] = useState<ConfirmRequest | null>(null);

  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["users"] });
  const fail = (error: unknown) =>
    toast.error(error instanceof ApiError ? error.message : "Something went wrong");

  const create = useMutation({
    mutationFn: api.users.create,
    onSuccess: ({ user, temporary_password }) => {
      setDialog({ open: false });
      setSecret({ email: user.email, password: temporary_password });
      toast.success(`${user.full_name} added`);
      refresh();
    },
    onError: fail,
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: UserPatchInput }) => api.users.update(id, body),
    onSuccess: (user, { body }) => {
      setDialog({ open: false });
      toast.success(
        body.is_active === false
          ? `${user.full_name} deactivated`
          : body.is_active === true
            ? `${user.full_name} reactivated`
            : "User saved",
      );
      refresh();
    },
    onError: fail,
  });

  const resetPassword = useMutation({
    mutationFn: api.users.resetPassword,
    onSuccess: ({ user, temporary_password }) => {
      setSecret({ email: user.email, password: temporary_password });
      refresh();
    },
    onError: fail,
  });

  const onSubmit = (values: UserFormValues) => {
    const target = dialog.user;
    const role = (ASSIGNABLE_ROLES as string[]).includes(values.role)
      ? (values.role as AssignableRole)
      : undefined;
    if (!target) {
      create.mutate({
        full_name: values.full_name,
        email: values.email,
        role: role ?? "recruiter",
      });
      return;
    }
    const body: UserPatchInput = {};
    if (values.full_name !== target.full_name) body.full_name = values.full_name;
    if (values.email.toLowerCase() !== target.email) body.email = values.email;
    if (role && role !== target.role) body.role = role;
    if (Object.keys(body).length === 0) {
      setDialog({ open: false });
      return;
    }
    update.mutate({ id: target.id, body });
  };

  const canTouch = (user: User) => me?.role === "super_admin" || user.role !== "super_admin";

  const actions = (user: User) => {
    const self = user.id === me?.id;
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" aria-label={`Actions for ${user.full_name}`}>
            <MoreHorizontal aria-hidden />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem
            onSelect={() => setDialog({ open: true, user })}
            disabled={!canTouch(user)}
          >
            <Pencil aria-hidden />
            Edit
          </DropdownMenuItem>
          <DropdownMenuItem
            onSelect={() =>
              setConfirm({
                title: `Reset password for ${user.full_name}?`,
                description:
                  "Their current password stops working and they get a new temporary one.",
                confirmLabel: "Reset password",
                onConfirm: () => resetPassword.mutate(user.id),
              })
            }
            disabled={!canTouch(user) || self}
          >
            <KeyRound aria-hidden />
            Reset password
          </DropdownMenuItem>
          {user.is_active ? (
            <DropdownMenuItem
              onSelect={() =>
                setConfirm({
                  title: `Deactivate ${user.full_name}?`,
                  description:
                    "They can no longer sign in. Their notes and history stay. You can reactivate them later.",
                  confirmLabel: "Deactivate",
                  destructive: true,
                  onConfirm: () => update.mutate({ id: user.id, body: { is_active: false } }),
                })
              }
              disabled={!canTouch(user) || self}
              className="text-destructive focus:text-destructive"
            >
              <UserX aria-hidden />
              Deactivate
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem
              onSelect={() => update.mutate({ id: user.id, body: { is_active: true } })}
              disabled={!canTouch(user)}
            >
              <UserCheck aria-hidden />
              Reactivate
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {users.data ? `${users.data.total} ${users.data.total === 1 ? "user" : "users"}` : " "}
        </p>
        <Button onClick={() => setDialog({ open: true })}>
          <Plus aria-hidden />
          Add user
        </Button>
      </div>

      {users.isPending ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : users.isError ? (
        <ErrorState error={users.error} onRetry={() => void users.refetch()} />
      ) : users.data.items.length === 0 ? (
        <EmptyState icon={Users} title="No users yet" />
      ) : (
        <>
          <div className="hidden rounded-lg border bg-card md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last sign-in</TableHead>
                  <TableHead className="w-12">
                    <span className="sr-only">Actions</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.data.items.map((user) => (
                  <TableRow key={user.id} className={user.is_active ? undefined : "opacity-60"}>
                    <TableCell>
                      <div className="font-medium">
                        {user.full_name}
                        {user.id === me?.id && (
                          <span className="ml-2 text-xs text-muted-foreground">(you)</span>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground">{user.email}</div>
                    </TableCell>
                    <TableCell>{ROLE_LABELS[user.role]}</TableCell>
                    <TableCell>
                      <StatusBadge user={user} />
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(user.last_login_at)}
                    </TableCell>
                    <TableCell>{actions(user)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <ul className="space-y-3 md:hidden">
            {users.data.items.map((user) => (
              <li key={user.id} className="flex items-start gap-3 rounded-lg border bg-card p-4">
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="font-medium">{user.full_name}</p>
                  <p className="break-all text-sm text-muted-foreground">{user.email}</p>
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-sm">
                    <span>{ROLE_LABELS[user.role]}</span>
                    <StatusBadge user={user} />
                  </div>
                </div>
                {actions(user)}
              </li>
            ))}
          </ul>
        </>
      )}

      <UserDialog
        open={dialog.open}
        onOpenChange={(open) => setDialog((d) => ({ ...d, open }))}
        user={dialog.user}
        canGrantSuperAdmin={me?.role === "super_admin"}
        busy={create.isPending || update.isPending}
        onSubmit={onSubmit}
      />
      <TemporaryPasswordDialog value={secret} onClose={() => setSecret(null)} />
      <ConfirmDialog request={confirm} onClose={() => setConfirm(null)} />
    </div>
  );
}

export default function UsersSettingsPage() {
  return (
    <AdminOnly>
      <UsersAdmin />
    </AdminOnly>
  );
}
