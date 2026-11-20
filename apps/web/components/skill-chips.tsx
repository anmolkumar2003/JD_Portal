"use client";

import { Plus, X } from "lucide-react";
import { useId, useState, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { Skill } from "@/types/api";

const WEIGHTS = [
  { value: 1, label: "High (1.0)" },
  { value: 0.75, label: "Medium (0.75)" },
  { value: 0.5, label: "Low (0.5)" },
  { value: 0.25, label: "Minor (0.25)" },
] as const;

type Tone = "required" | "preferred";

const TONE_CLASSES: Record<Tone, string> = {
  required: "border-primary/30 bg-accent text-accent-foreground",
  preferred: "border-border bg-secondary text-secondary-foreground",
};

function formatWeight(weight: number): string {
  return weight.toFixed(2).replace(/0$/, "");
}

interface SkillChipsProps {
  skills: Skill[];
  tone?: Tone;
  showWeights?: boolean;
  emptyLabel?: string;
}

/** Read-only list of skill chips, optionally with their weights. */
export function SkillChips({
  skills,
  tone = "required",
  showWeights = true,
  emptyLabel = "None",
}: SkillChipsProps) {
  if (skills.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>;
  }
  return (
    <ul className="flex flex-wrap gap-2">
      {skills.map((skill) => (
        <li
          key={skill.name}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
            TONE_CLASSES[tone],
          )}
        >
          {skill.name}
          {showWeights && (
            <span className="font-mono text-[11px] opacity-70">×{formatWeight(skill.weight)}</span>
          )}
        </li>
      ))}
    </ul>
  );
}

interface SkillChipsInputProps {
  label: string;
  value: Skill[];
  onChange: (skills: Skill[]) => void;
  tone?: Tone;
  /** Skill names (any case) that may not be added here, e.g. already listed elsewhere. */
  exclude?: string[];
  error?: string;
  placeholder?: string;
}

/** Editable chips: type a skill, choose its weight, press Enter or Add. */
export function SkillChipsInput({
  label,
  value,
  onChange,
  tone = "required",
  exclude = [],
  error,
  placeholder = "e.g. Python",
}: SkillChipsInputProps) {
  const id = useId();
  const [name, setName] = useState("");
  const [weight, setWeight] = useState<number>(1);
  const [localError, setLocalError] = useState<string | null>(null);

  const add = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    const key = trimmed.toLowerCase();
    if (value.some((s) => s.name.toLowerCase() === key)) {
      setLocalError(`${trimmed} is already in this list`);
      return;
    }
    if (exclude.some((s) => s.toLowerCase() === key)) {
      setLocalError(`${trimmed} is already listed in the other skills list`);
      return;
    }
    onChange([...value, { name: trimmed, weight }]);
    setName("");
    setLocalError(null);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      add();
    }
  };

  const message = localError ?? error;
  const errorId = `${id}-error`;

  return (
    <fieldset className="space-y-3">
      <legend className="text-sm font-medium">{label}</legend>
      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="flex-1">
          <label htmlFor={`${id}-name`} className="sr-only">
            Skill name
          </label>
          <Input
            id={`${id}-name`}
            value={name}
            placeholder={placeholder}
            maxLength={100}
            onChange={(e) => {
              setName(e.target.value);
              setLocalError(null);
            }}
            onKeyDown={onKeyDown}
            aria-invalid={message ? true : undefined}
            aria-describedby={message ? errorId : undefined}
          />
        </div>
        <div className="sm:w-44">
          <label htmlFor={`${id}-weight`} className="sr-only">
            Weight
          </label>
          <Select
            id={`${id}-weight`}
            value={weight}
            onChange={(e) => setWeight(Number(e.target.value))}
          >
            {WEIGHTS.map((w) => (
              <option key={w.value} value={w.value}>
                {w.label}
              </option>
            ))}
          </Select>
        </div>
        <Button type="button" variant="outline" onClick={add} disabled={!name.trim()}>
          <Plus aria-hidden />
          Add
        </Button>
      </div>
      {message && (
        <p id={errorId} className="text-sm text-destructive">
          {message}
        </p>
      )}
      {value.length > 0 ? (
        <ul className="flex flex-wrap gap-2" aria-label={`${label} added`}>
          {value.map((skill) => (
            <li
              key={skill.name}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border py-1 pl-2.5 pr-1 text-xs font-medium",
                TONE_CLASSES[tone],
              )}
            >
              {skill.name}
              <span className="font-mono text-[11px] opacity-70">
                ×{formatWeight(skill.weight)}
              </span>
              <button
                type="button"
                onClick={() => onChange(value.filter((s) => s.name !== skill.name))}
                className="rounded-full p-0.5 hover:bg-background/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label={`Remove ${skill.name}`}
              >
                <X className="h-3 w-3" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">No skills added yet.</p>
      )}
    </fieldset>
  );
}
