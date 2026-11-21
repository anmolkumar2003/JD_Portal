import type { Role } from "@/types/api";

/** Mirrors the API's JobEditor dependency; the backend remains the source of truth. */
const JOB_EDITORS: ReadonlySet<Role> = new Set(["super_admin", "hr_admin", "recruiter"]);

export function canManageJobs(role: Role | undefined): boolean {
  return role !== undefined && JOB_EDITORS.has(role);
}

/** Stage moves use the same editor roles as job publish/close. */
export function canMoveStages(role: Role | undefined): boolean {
  return canManageJobs(role);
}
