import { expect, test } from "@playwright/test";

import { loginAsHrAdmin, loginAsRecruiter, open } from "./helpers/auth";

function toast(page: import("@playwright/test").Page, pattern: RegExp) {
  return page.getByText(pattern).first();
}

test.describe("Permanent candidate delete", () => {
  test("recruiter does not see Delete on the profile actions menu", async ({ page }) => {
    await loginAsRecruiter(page);
    await open(page, "/candidates");
    const row = page.getByRole("row").nth(1);
    await expect(row).toBeVisible({ timeout: 20_000 });
    await row.click();
    await page.waitForURL(/\/candidates\//, { timeout: 20_000 });
    await expect(page.getByTestId("candidate-actions-menu")).toHaveCount(0);
    await expect(page.getByTestId("delete-candidate-action")).toHaveCount(0);
  });

  test("hr_admin permanently deletes a candidate end to end", async ({ page }) => {
    const stamp = Date.now();
    const first = "Delete";
    const last = `Me${stamp}`;
    const fullName = `${first} ${last}`;
    const email = `delete.me.${stamp}@example.com`;

    await loginAsHrAdmin(page);
    await open(page, "/candidates/new");
    await page.getByLabel("First name", { exact: true }).fill(first);
    await page.getByLabel("Last name", { exact: true }).fill(last);
    await page.getByLabel("Email", { exact: true }).fill(email);
    await page.getByLabel("Phone", { exact: true }).fill("+91 90000 22233");
    const job = page.getByLabel("Job", { exact: true });
    if (await job.count()) {
      await job.selectOption({ index: 1 });
    }
    await page.getByRole("button", { name: /Save candidate/i }).click();
    await expect(toast(page, /Candidate saved|saved/i)).toBeVisible({ timeout: 30_000 });
    await page.waitForURL(/\/candidates\/[^/?]+/, { timeout: 30_000 });

    await page.getByTestId("candidate-actions-menu").click();
    await page.getByTestId("delete-candidate-action").click();
    await expect(page.getByTestId("delete-candidate-dialog")).toBeVisible();
    await expect(page.getByText(/permanent and cannot be undone/i)).toBeVisible();
    await expect(page.getByTestId("delete-candidate-confirm")).toBeDisabled();
    await page.getByTestId("delete-confirm-input").fill(fullName);
    await expect(page.getByTestId("delete-candidate-confirm")).toBeEnabled();
    await page.getByTestId("delete-candidate-confirm").click();

    await expect(toast(page, /permanently deleted/i)).toBeVisible({ timeout: 20_000 });
    await page.waitForURL("**/candidates", { timeout: 20_000 });
    await expect(page.getByText(email)).toHaveCount(0);
    await expect(page.getByText(fullName)).toHaveCount(0);
  });
});
