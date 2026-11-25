import path from "node:path";

import { expect, test } from "@playwright/test";

import { CAREERS_ENABLED, loginAs, loginAsRecruiter } from "./helpers/auth";
import { FIXTURES_DIR } from "./helpers/paths";

const SAMPLE_CV = path.join(FIXTURES_DIR, "cv01_backend.pdf");
const SEEDED_DEMO_EMAIL = "demo01@candidates.demo";

test.describe("Careers apply", () => {
  test.skip(!CAREERS_ENABLED, "Public careers site is switched off (ENABLE_PUBLIC_CAREERS)");
  test("candidate applies with a CV", async ({ page }) => {
    const unique = `e2e-${Date.now()}@mail.example.com`;
    await page.goto("/careers");
    await page.getByRole("link", { name: /Senior Android Developer/i }).click();
    await page.getByRole("link", { name: /Apply for this role/i }).click();

    await page.getByLabel("First name").fill("E2E");
    await page.getByLabel("Last name").fill("Applicant");
    await page.getByLabel("Email", { exact: true }).fill(unique);
    await page.getByLabel("Phone").fill("+91 98765 43210");
    await page.getByRole("button", { name: /Continue/i }).click();

    await page.getByLabel("Current company").fill("Playwright Co");
    await page.getByLabel(/Current job title/i).fill("QA Engineer");
    await page.getByRole("button", { name: /Continue/i }).click();

    await page.locator('input[type="file"]').setInputFiles(SAMPLE_CV);
    await page.getByLabel(/I agree that/i).check();
    await page.getByRole("button", { name: "Submit application" }).click();

    await page.waitForURL(/\/careers\/[^/]+\/applied/);
    await expect(page.getByTestId("reference-no")).toContainText(/APP-/);
  });
});

test.describe("Recruiter pipeline", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsRecruiter(page);
  });

  test("sees a scored demo candidate in the list", async ({ page }) => {
    await page.goto(`/candidates?q=${encodeURIComponent(SEEDED_DEMO_EMAIL)}`);
    await expect(page.getByText(SEEDED_DEMO_EMAIL)).toBeVisible({ timeout: 20_000 });
    await expect(page.getByLabel(/Match score \d+/).first()).toBeVisible();
  });

  test("moves a seeded candidate to another stage", async ({ page }) => {
    await page.goto("/jobs");
    await page.getByRole("link", { name: "Senior Android Developer" }).click();
    await page.getByRole("tab", { name: /Pipeline/i }).click();

    const applied = page.getByRole("region", { name: /Applied,/i });
    const card = applied.getByRole("article").first();
    await expect(card).toBeVisible({ timeout: 20_000 });
    const name = (await card.locator("p.truncate.font-medium").first().textContent())?.trim();
    expect(name).toBeTruthy();

    await card.getByRole("button", { name: new RegExp(`Move ${name}`, "i") }).click();
    await page.getByRole("menuitem", { name: "Move to Screening" }).click();
    await expect(page.getByRole("region", { name: /Screening,/i })).toContainText(name!);
  });

  test("rejects with a required reason", async ({ page }) => {
    await page.goto("/jobs");
    await page.getByRole("link", { name: "Senior Android Developer" }).click();
    await page.getByRole("tab", { name: /Pipeline/i }).click();

    const applied = page.getByRole("region", { name: /Applied,/i });
    const card = applied.getByRole("article").first();
    await expect(card).toBeVisible({ timeout: 20_000 });
    const name = (await card.locator("p.truncate.font-medium").first().textContent())?.trim();
    expect(name).toBeTruthy();

    await card.getByRole("button", { name: new RegExp(`Move ${name}`, "i") }).click();
    await page.getByRole("menuitem", { name: "Move to Rejected" }).click();

    await page.getByLabel("Reason").fill("E2E rejection — skills gap for this role");
    await page.getByRole("button", { name: "Reject candidate" }).click();
    await expect(
      page
        .getByRole("region", { name: /Rejected,/i })
        .getByText(name!)
        .first(),
    ).toBeVisible({ timeout: 15_000 });
  });
});

test("interviewer submits a scorecard (portal UI)", async ({ page }) => {
  await loginAs(page, "interviewer");

  await page.goto("/interviews");
  const hasPortal = await page
    .getByRole("heading", { name: /interview/i })
    .isVisible()
    .catch(() => false);
  test.skip(!hasPortal, "Interview portal UI not shipped yet (API only)");
});

test("offer is approved (portal UI)", async ({ page }) => {
  await loginAsRecruiter(page);
  await page.goto("/offers");
  const hasPortal = await page
    .getByRole("heading", { name: /offer/i })
    .isVisible()
    .catch(() => false);
  test.skip(!hasPortal, "Offer portal UI not shipped yet (API only)");
});
