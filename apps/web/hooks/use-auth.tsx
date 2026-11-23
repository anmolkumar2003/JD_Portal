"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useMemo, type ReactNode } from "react";

import { api, refreshSession } from "@/lib/api";
import type { ChangePasswordInput, LoginRequest, User } from "@/types/api";

const SESSION_KEY = ["auth", "session"] as const;

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<User>;
  logout: () => Promise<void>;
  changePassword: (input: ChangePasswordInput) => Promise<User>;
  isLoggingOut: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  // On first load, restore the session from the refresh cookie.
  const session = useQuery({
    queryKey: SESSION_KEY,
    queryFn: async () => (await refreshSession())?.user ?? null,
    staleTime: Infinity,
    retry: false,
  });

  const loginMutation = useMutation({
    mutationFn: api.auth.login,
    onSuccess: ({ user }) => queryClient.setQueryData(SESSION_KEY, user),
  });

  const changePasswordMutation = useMutation({
    mutationFn: api.auth.changePassword,
    onSuccess: ({ user }) => queryClient.setQueryData(SESSION_KEY, user),
  });

  const logoutMutation = useMutation({
    mutationFn: api.auth.logout,
    onSettled: () => {
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== SESSION_KEY[0] });
      queryClient.setQueryData(SESSION_KEY, null);
    },
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session.data ?? null,
      isLoading: session.isPending,
      login: async (credentials) => (await loginMutation.mutateAsync(credentials)).user,
      logout: () => logoutMutation.mutateAsync(),
      changePassword: async (input) => (await changePasswordMutation.mutateAsync(input)).user,
      isLoggingOut: logoutMutation.isPending,
    }),
    [session.data, session.isPending, loginMutation, logoutMutation, changePasswordMutation],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return context;
}
