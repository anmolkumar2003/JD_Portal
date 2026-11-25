import fs from "node:fs";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { DEMO_PASSWORD, loginAsRecruiter, open } from "./helpers/auth";
import { DOCS_DIR } from "./helpers/paths";

// Run via `make test-e2e-screenshots` (docs/ mounted at /work/docs in the container).
const OUTPUT_DIR = path.join(DOCS_DIR, "screenshots");

const VIEWPORTS: { name: string; width: number; height: number }[] = [
  { name: "390x844", width: 390, height: 844 },
  { name: "844x390", width: 844, height: 390 },
  { name: "820x1180", width: 820, height: 1180 },
  { name: "1280x800", width: 1280, height: 800 },
  { name: "1920x1080", width: 1920, height: 1080 },
];

const PAGES = [
  { slug: "dashboard", path: "/dashboard" },
  { slug: "candidates", path: "/candidates" },
] as const;

const SEEDED_DEMO_EMAIL = "demo01@candidates.demo";

async function capture(page: Page, viewport: string, name: string): Promise<void> {
  const file = path.join(OUTPUT_DIR, `${viewport}-${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
}

test.describe("responsive screenshots", () => {
  test.beforeAll(() => {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  });

  test("portal pages at standard viewports", async ({ page }) => {
    test.skip(!DEMO_PASSWORD, "E2E_PASSWORD not set — run via `make test-e2e-screenshots`");
    // Separate job: 5 viewports x several full-page captures need far more than the suite default.
    test.setTimeout(180_000);

    await loginAsRecruiter(page);

    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.width, height: vp.height });

      for (const { slug, path: route } of PAGES) {
        await open(page, route);
        await page.waitForLoadState("networkidle").catch(() => undefined);
        await capture(page, vp.name, slug);
      }

      await open(page, `/candidates?q=${encodeURIComponent(SEEDED_DEMO_EMAIL)}`);
      const row = page.getByText(SEEDED_DEMO_EMAIL);
      const hasSeed = await row.isVisible({ timeout: 8_000 }).catch(() => false);
      if (hasSeed) {
        await row.click();
        await page.waitForURL(/\/candidates\/[^/]+/, { timeout: 15_000 }).catch(() => undefined);
        await capture(page, vp.name, "candidate-detail");
      } else {
        test.info().annotations.push({
          type: "skip-detail",
          description: `No seeded candidate ${SEEDED_DEMO_EMAIL} at ${vp.name}`,
        });
      }
    }

    expect(fs.readdirSync(OUTPUT_DIR).length).toBeGreaterThan(0);
  });
});
