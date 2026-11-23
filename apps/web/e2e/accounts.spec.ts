import { expect, test } from "@playwright/test";

import { CAREERS_ENABLED, loginAsHrAdmin, open, signIn } from "./helpers/auth";

test.describe("Accounts and settings", () => {
  test("admin adds a user who must set a password on first sign-in", async ({ page, browser }) => {
    const email = `new.hire.${Date.now()}@example.com`;
    await loginAsHrAdmin(page);
    await page.goto("/settings/users");
    await page.getByRole("button", { name: "Add user" }).click();
    await page.getByLabel("Full name").fill("New Hire");
    await page.getByLabel("Work email").fill(email);
    await page.getByLabel("Role").selectOption("recruiter");
    await page.getByRole("button", { name: "Create user" }).click();

    const temporary = (await page.getByTestId("temp-password").textContent())?.trim() ?? "";
    expect(temporary.length).toBeGreaterThanOrEqual(12);
    await page.getByRole("button", { name: "Done" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(page.locator("tbody").getByText(email)).toBeVisible();
    await expect(page.getByText("Awaiting first sign-in").first()).toBeVisible();

    const context = await browser.newContext();
    const fresh = await context.newPage();
    await signIn(fresh, email, temporary);
    await fresh.waitForURL("**/change-password**");
    await fresh.getByLabel("Current password").fill(temporary);
    await fresh.getByLabel("New password", { exact: true }).fill("Brand-New-Pass-2026");
    await fresh.getByLabel("Confirm new password").fill("Brand-New-Pass-2026");
    await fresh.getByRole("button", { name: "Save and continue" }).click();
    await fresh.waitForURL("**/dashboard");
    await context.close();
  });

  test("admin renames the organization and the sidebar follows", async ({ page }) => {
    await loginAsHrAdmin(page);
    await page.goto("/settings/organization");
    const name = `Pixel Works ${Date.now() % 1000}`;
    await page.getByLabel("Name").fill(name);
    await page.getByRole("button", { name: "Save name" }).click();
    await expect(page.getByText("Organization name saved")).toBeVisible();
    await expect(page.getByRole("complementary").getByText(name)).toBeVisible();
  });

  test("admin adds and deactivates a department", async ({ page }) => {
    await loginAsHrAdmin(page);
    await page.goto("/settings/departments");
    await expect(page.getByText("Quality Analyst")).toBeVisible();
    const department = `Growth ${Date.now() % 1000}`;
    await page.getByLabel("New department name").fill(department);
    await page.getByRole("button", { name: "Add" }).first().click();
    const row = page.getByRole("main").getByRole("listitem").filter({ hasText: department });
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "Deactivate" }).click();
    await expect(row.getByText("Inactive")).toBeVisible();
  });

  test("forgot password always answers the same way", async ({ page }) => {
    await open(page, "/login");
    await expect(page.getByRole("link", { name: "Forgot password?" })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
    await open(page, "/forgot-password");
    await page.getByLabel("Email").fill("nobody@example.com");
    await page.getByRole("button", { name: "Send reset link" }).click();
    await expect(page.getByText(/If an account exists for that email/)).toBeVisible();
  });

  test("careers site is hidden while its module is off", async ({ page }) => {
    test.skip(CAREERS_ENABLED, "Careers module is switched on for this run");
    const response = await page.goto("/careers");
    expect(response?.status()).toBe(404);
  });
});
