import type { Page } from "@playwright/test";

export const DEMO_RECRUITER = {
  email: "recruiter@acme.example.com",
  password: "Demo@2026!",
} as const;

export async function loginAsRecruiter(page: Page): Promise<void> {
  await page.goto("/login");
  await page.locator("#email").fill(DEMO_RECRUITER.email);
  await page.locator("#password").fill(DEMO_RECRUITER.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/dashboard", { timeout: 30_000 });
}