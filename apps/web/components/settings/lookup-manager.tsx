"use client";

import { Check, Loader2, Pencil, Plus, X } from "lucide-react";
import { useState, type FormEvent } from "react";

import { ErrorState } from "@/components/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

export interface LookupItem {
  id: string;
  name: string;
  is_active: boolean;
  detail?: string | null;
}

interface LookupManagerProps {
  title: string;
  description: string;
  noun: string;
  items: LookupItem[] | undefined;
  isPending: boolean;
  error: unknown;
  onRetry: () => void;
  busy: boolean;
  onCreate: (name: string) => Promise<unknown>;
  onRename: (id: string, name: string) => Promise<unknown>;
  onToggle: (id: string, active: boolean) => void;
}

function RenameRow({
  item,
  onSave,
  onCancel,
}: {
  item: LookupItem;
  onSave: (name: string) => Promise<unknown>;
  onCancel: () => void;
}) {
  const [value, setValue] = useState(item.name);
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const name = value.trim();
    if (!name || name === item.name) return onCancel();
    setSaving(true);
    try {
      await onSave(name);
      onCancel();
    } catch {
      setSaving(false);
    }
  };
  return (
    <form onSubmit={(e) => void submit(e)} className="flex flex-1 items-center gap-2">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        aria-label={`New name for ${item.name}`}
        maxLength={200}
        autoFocus
        onKeyDown={(e) => e.key === "Escape" && onCancel()}
      />
      <Button type="submit" size="icon" aria-label="Save name" disabled={saving}>
        {saving ? <Loader2 className="animate-spin" aria-hidden /> : <Check aria-hidden />}
      </Button>
      <Button type="button" size="icon" variant="ghost" aria-label="Cancel" onClick={onCancel}>
        <X aria-hidden />
      </Button>
    </form>
  );
}

export function LookupManager({
  title,
  description,
  noun,
  items,
  isPending,
  error,
  onRetry,
  busy,
  onCreate,
  onRename,
  onToggle,
}: LookupManagerProps) {
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<string | null>(null);

  const add = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    try {
      await onCreate(trimmed);
      setName("");
    } catch {
      // The caller shows the error toast; keep the typed name for correction.
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={(e) => void add(e)} className="flex gap-2">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={`New ${noun}`}
            aria-label={`New ${noun} name`}
            maxLength={200}
          />
          <Button type="submit" disabled={!name.trim() || busy}>
            <Plus aria-hidden />
            Add
          </Button>
        </form>

        {isPending ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-11" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={onRetry} />
        ) : items && items.length > 0 ? (
          <ul className="divide-y rounded-md border">
            {items.map((item) => (
              <li key={item.id} className="flex min-h-12 items-center gap-2 px-3 py-1.5">
                {editing === item.id ? (
                  <RenameRow
                    item={item}
                    onSave={(value) => onRename(item.id, value)}
                    onCancel={() => setEditing(null)}
                  />
                ) : (
                  <>
                    <div className="min-w-0 flex-1">
                      <span className={item.is_active ? "font-medium" : "text-muted-foreground"}>
                        {item.name}
                      </span>
                      {item.detail && (
                        <span className="ml-2 text-sm text-muted-foreground">{item.detail}</span>
                      )}
                    </div>
                    {!item.is_active && <Badge variant="secondary">Inactive</Badge>}
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Rename ${item.name}`}
                      onClick={() => setEditing(item.id)}
                    >
                      <Pencil aria-hidden />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-10"
                      onClick={() => onToggle(item.id, !item.is_active)}
                    >
                      {item.is_active ? "Deactivate" : "Activate"}
                    </Button>
                  </>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No {noun}s yet.</p>
        )}
        <p className="text-xs text-muted-foreground">
          Deactivated {noun}s disappear from dropdowns but stay on existing records.
        </p>
      </CardContent>
    </Card>
  );
}
