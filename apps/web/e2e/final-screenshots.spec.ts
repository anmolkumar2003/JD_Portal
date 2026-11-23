import fs from "node:fs";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { DEMO_PASSWORD, loginAsRecruiter, open } from "./helpers/auth";

// Under `make test-e2e-screenshots`, repo docs/ is mounted at /work/docs (cwd = apps/web).
const OUTPUT_DIR = path.resolve(__dirname, "../docs/final-screenshots");

const VIEWPORTS: { name: string; width: number; height: number }[] = [
  { name: "390x844", width: 390, height: 844 },
  { name: "844x390", width: 844, height: 390 },
  { name: "820x1180", width: 820, height: 1180 },
  { name: "1280x800", width: 1280, height: 800 },
  { name: "1920x1080", width: 1920, height: 1080 },
];

async function capture(page: Page, file: string): Promise<void> {
  await page.screenshot({ path: path.join(OUTPUT_DIR, file), fullPage: true });
}

async function setDark(page: Page): Promise<void> {
  await page.evaluate(() => {
    document.documentElement.classList.add("dark");
    localStorage.setItem("theme", "dark");
  });
}

test.describe("final screenshots — kanban + dark mode", () => {
  test.beforeAll(() => {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  });

  test("kanban and dark mode at five viewports", async ({ page }) => {
    test.skip(!DEMO_PASSWORD, "E2E_PASSWORD not set — run via make test-e2e-screenshots");
    test.setTimeout(180_000);

    await loginAsRecruiter(page);
    const issues: string[] = [];

    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.width, height: vp.height });

      await open(page, "/jobs");
      const jobLink = page.getByRole("link", { name: /Senior Android Developer/i }).first();
      await expect(jobLink).toBeVisible({ timeout: 20_000 });
      await jobLink.click();
      await page.getByRole("tab", { name: /Pipeline/i }).click();
      await page.waitForLoadState("networkidle").catch(() => undefined);
      await capture(page, `${vp.name}-kanban.png`);

      await setDark(page);
      await open(page, "/dashboard");
      await page.waitForLoadState("networkidle").catch(() => undefined);
      await capture(page, `${vp.name}-dashboard-dark.png`);

      await open(page, "/candidates");
      await page.waitForLoadState("networkidle").catch(() => undefined);
      await capture(page, `${vp.name}-candidates-dark.png`);

      await open(page, "/jobs");
      await page.getByRole("link", { name: /Senior Android Developer/i }).first().click();
      await page.getByRole("tab", { name: /Pipeline/i }).click();
      await page.waitForLoadState("networkidle").catch(() => undefined);
      await capture(page, `${vp.name}-kanban-dark.png`);
    }

    const files = fs
      .readdirSync(OUTPUT_DIR)
      .filter((f) => f.includes("kanban") || f.includes("dark"));
    expect(files.length).toBeGreaterThan(0);
    if (issues.length) {
      test.info().annotations.push({ type: "issues", description: issues.join("; ") });
    }
  });
});
