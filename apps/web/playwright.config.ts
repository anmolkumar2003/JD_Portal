import { defineConfig, devices } from "@playwright/test";

/**
 * Run with `make test-e2e`: isolated stack (docker-compose.e2e.yml), seeded demo data,
 * password via E2E_PASSWORD. Screenshots run as a separate job (`make test-e2e-screenshots`)
 * so the long viewport matrix cannot time out the main suite.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  testIgnore: /screenshots\.spec\.ts$/,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      testIgnore: [/screenshots\.spec\.ts$/, /final-screenshots\.spec\.ts$/],
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "screenshots",
      testMatch: [/screenshots\.spec\.ts$/, /final-screenshots\.spec\.ts$/],
      timeout: 180_000,
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
