"use client";

import { useFormContext, useWatch } from "react-hook-form";

import { QuickFillBadge } from "@/components/candidates/quick-fill-context";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { SalaryUnit } from "@/types/api";

const CURRENCIES = ["INR", "USD", "EUR", "GBP"] as const;

export type SalaryFormSlice = {
  amount: string;
  currency: string;
  unit: SalaryUnit;
  negotiable: boolean;
};

export function defaultSalaryForm(): SalaryFormSlice {
  return { amount: "", currency: "INR", unit: "pa", negotiable: false };
}

type SalaryPrefix = "current_ctc" | "expected_ctc" | "offered_ctc";

interface SalaryFieldsProps {
  title: string;
  prefix: SalaryPrefix;
  description?: string;
}

export function SalaryFields({ title, prefix, description }: SalaryFieldsProps) {
  const { register, setValue } = useFormContext();
  const negotiable = useWatch({ name: `${prefix}.negotiable` }) as boolean;

  return (
    <fieldset className="glass space-y-3 rounded-xl p-4">
      <legend className="px-1 text-sm font-medium">
        {title}
        <QuickFillBadge path={`${prefix}.amount`} />
      </legend>
      {description && <p className="text-xs text-muted-foreground">{description}</p>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor={`${prefix}.amount`}>Amount</Label>
          <Input
            id={`${prefix}.amount`}
            inputMode="decimal"
            placeholder="e.g. 1200000"
            {...register(`${prefix}.amount`)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${prefix}.currency`}>Currency</Label>
          <Select id={`${prefix}.currency`} {...register(`${prefix}.currency`)}>
            {CURRENCIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${prefix}.unit`}>Unit</Label>
          <Select id={`${prefix}.unit`} {...register(`${prefix}.unit`)}>
            <option value="pa">Per annum</option>
            <option value="pm">Per month</option>
          </Select>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <input
          id={`${prefix}.negotiable`}
          type="checkbox"
          className="h-4 w-4 rounded border-input"
          checked={Boolean(negotiable)}
          onChange={(e) =>
            setValue(`${prefix}.negotiable`, e.target.checked, { shouldDirty: true })
          }
        />
        <Label htmlFor={`${prefix}.negotiable`} className="font-normal">
          Negotiable
          <QuickFillBadge path={`${prefix}.negotiable`} />
        </Label>
      </div>
    </fieldset>
  );
}
