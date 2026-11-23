import { expect, type Page } from "@playwright/test";

/**
 * Accounts created by `python -m app.seed_demo` in the throwaway e2e stack. The password is
 * generated for each run by `make test-e2e` and passed in as E2E_PASSWORD.
 */
export const DEMO_PASSWORD = process.env.E2E_PASSWORD ?? "";
export const demoEmail = (handle: string) => `${handle}@demo.example.com`;

export const CAREERS_ENABLED = process.env.E2E_ENABLE_PUBLIC_CAREERS === "true";

/** Full page load that waits until React has hydrated, so typed input is not discarded. */
export async function open(page: Page, path: string): Promise<void> {
  await page.goto(path);
  await page.locator("html[data-hydrated]").waitFor({ state: "attached" });
}

export async function signIn(page: Page, email: string, password: string): Promise<void> {
  await open(page, "/login");
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

export async function loginAs(page: Page, handle: string): Promise<void> {
  expect(DEMO_PASSWORD, "E2E_PASSWORD must be set (run `make test-e2e`)").not.toBe("");
  await signIn(page, demoEmail(handle), DEMO_PASSWORD);
  await page.waitForURL("**/dashboard", { timeout: 30_000 });
}

export const loginAsRecruiter = (page: Page) => loginAs(page, "recruiter");
export const loginAsHrAdmin = (page: Page) => loginAs(page, "hradmin");
