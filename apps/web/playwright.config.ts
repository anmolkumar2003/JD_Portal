import { defineConfig, devices } from "@playwright/test";

/**
 * Run with `make test-e2e`: it starts an isolated stack (docker-compose.e2e.yml), seeds demo
 * data with a one-off password (E2E_PASSWORD) and runs these tests against http://web:3000.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  timeout: 60_000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
