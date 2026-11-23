"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImageUp, Loader2, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Brand } from "@/components/brand";
import { ErrorState } from "@/components/error-state";
import { AdminOnly } from "@/components/settings/admin-only";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { CONFIG_KEY } from "@/hooks/use-config";
import { api, ApiError } from "@/lib/api";
import type { OrgSettings } from "@/types/api";

const SETTINGS_KEY = ["org", "settings"] as const;
const MAX_LOGO_KB = 256;

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

function OrganizationForm({ settings }: { settings: OrgSettings }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(settings.name);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => setName(settings.name), [settings.name]);

  const onSaved = (updated: OrgSettings) => {
    queryClient.setQueryData(SETTINGS_KEY, updated);
    void queryClient.invalidateQueries({ queryKey: CONFIG_KEY });
  };

  const rename = useMutation({
    mutationFn: () => api.org.updateSettings({ name: name.trim() }),
    onSuccess: (updated) => {
      onSaved(updated);
      toast.success("Organization name saved");
    },
    onError: (error) => toast.error(errorMessage(error, "Could not save the name")),
  });

  const upload = useMutation({
    mutationFn: api.org.uploadLogo,
    onSuccess: (updated) => {
      onSaved(updated);
      toast.success("Logo updated");
    },
    onError: (error) => toast.error(errorMessage(error, "Could not upload the logo")),
  });

  const remove = useMutation({
    mutationFn: api.org.removeLogo,
    onSuccess: (updated) => {
      onSaved(updated);
      toast.success("Logo removed");
    },
    onError: (error) => toast.error(errorMessage(error, "Could not remove the logo")),
  });

  const onFile = (file: File | undefined) => {
    if (!file) return;
    if (file.size > MAX_LOGO_KB * 1024) {
      toast.error(`The logo must be ${MAX_LOGO_KB} KB or smaller.`);
      return;
    }
    upload.mutate(file);
  };

  const trimmed = name.trim();

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Company name</CardTitle>
          <CardDescription>Shown in the portal, emails and the careers site.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (trimmed) rename.mutate();
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="org-name">Name</Label>
              <Input
                id="org-name"
                value={name}
                maxLength={200}
                onChange={(event) => setName(event.target.value)}
                aria-invalid={!trimmed ? true : undefined}
              />
              {!trimmed && <p className="text-sm text-destructive">Enter a name.</p>}
            </div>
            <Button
              type="submit"
              disabled={!trimmed || trimmed === settings.name || rename.isPending}
            >
              {rename.isPending && <Loader2 className="animate-spin" aria-hidden />}
              Save name
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Logo</CardTitle>
          <CardDescription>
            PNG, JPEG or WebP, up to {MAX_LOGO_KB} KB. A square image works best.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3 rounded-md border bg-muted/40 p-4">
            <Brand name={settings.name} logoUrl={settings.logo_data_url} />
          </div>
          <input
            ref={fileInput}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            aria-label="Choose a logo file"
            onChange={(event) => {
              onFile(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => fileInput.current?.click()}
              disabled={upload.isPending}
            >
              {upload.isPending ? (
                <Loader2 className="animate-spin" aria-hidden />
              ) : (
                <ImageUp aria-hidden />
              )}
              {settings.logo_data_url ? "Replace logo" : "Upload logo"}
            </Button>
            {settings.logo_data_url && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => remove.mutate()}
                disabled={remove.isPending}
              >
                <Trash2 aria-hidden />
                Remove
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function OrganizationSettings() {
  const settings = useQuery({ queryKey: SETTINGS_KEY, queryFn: api.org.settings });
  if (settings.isPending) {
    return (
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-56" />
        <Skeleton className="h-56" />
      </div>
    );
  }
  if (settings.isError) {
    return <ErrorState error={settings.error} onRetry={() => void settings.refetch()} />;
  }
  return <OrganizationForm settings={settings.data} />;
}

export default function OrganizationSettingsPage() {
  return (
    <AdminOnly>
      <OrganizationSettings />
    </AdminOnly>
  );
}
