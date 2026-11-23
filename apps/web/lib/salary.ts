import type { BudgetStatus, SalaryIn, SalaryUnit } from "@/types/api";

/** Convert a salary amount to per-annum for comparison with job bands. */
export function annualizeSalary(amount: number | null, unit: SalaryUnit | null): number | null {
  if (amount === null || Number.isNaN(amount)) return null;
  return unit === "pm" ? amount * 12 : amount;
}

export function computeBudgetStatus(
  expectedAmount: number | null,
  expectedUnit: SalaryUnit | null,
  jobSalaryMax: number | null,
): BudgetStatus {
  const annual = annualizeSalary(expectedAmount, expectedUnit);
  if (annual === null || jobSalaryMax === null) return "unknown";
  return annual > jobSalaryMax ? "above" : "within";
}

export function salaryOutToForm(
  salary:
    | {
        amount: string | null;
        currency: string;
        unit: SalaryUnit;
        negotiable: boolean;
      }
    | null
    | undefined,
): {
  amount: string;
  currency: string;
  unit: SalaryUnit;
  negotiable: boolean;
} {
  if (!salary) {
    return { amount: "", currency: "INR", unit: "pa", negotiable: false };
  }
  return {
    amount: salary.amount !== null ? Number(salary.amount).toString() : "",
    currency: salary.currency || "INR",
    unit: salary.unit ?? "pa",
    negotiable: salary.negotiable,
  };
}

export function formSalaryToIn(values: {
  amount: string;
  currency: string;
  unit: SalaryUnit;
  negotiable: boolean;
}): SalaryIn | null {
  const trimmed = values.amount.trim();
  if (!trimmed) return null;
  return {
    amount: Number(trimmed),
    currency: values.currency.toUpperCase(),
    unit: values.unit,
    negotiable: values.negotiable,
  };
}
