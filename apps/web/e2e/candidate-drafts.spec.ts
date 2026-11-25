import fs from "node:fs";
import path from "node:path";

import { expect, test, type Locator, type Page, type Request } from "@playwright/test";

import { loginAsRecruiter, open } from "./helpers/auth";
import { FIXTURES_DIR } from "./helpers/paths";

/**
 * Add Candidate draft flow (B1-B6): dropped CVs go to a temporary draft, required fields block
 * saving, and nothing becomes a candidate until Save.
 */

const CV_BACKEND = path.join(FIXTURES_DIR, "cv01_backend.pdf");
const CV_FRONTEND = path.join(FIXTURES_DIR, "cv02_frontend.pdf");
const ANDROID_JOB = "Senior Android Developer";

type DropFile = { name: string; type: string; base64: string };

function fixtureFile(file: string, name = path.basename(file)): DropFile {
  return {
    name,
    type: "application/pdf",
    base64: fs.readFileSync(file).toString("base64"),
  };
}

async function dropFiles(page: Page, files: DropFile[]): Promise<void> {
  const zone = page.getByTestId("cv-dropzone");
  await expect(zone).toBeVisible();
  const dataTransfer = await page.evaluateHandle((items) => {
    const dt = new DataTransfer();
    for (const item of items) {
      const bytes = Uint8Array.from(atob(item.base64), (c) => c.charCodeAt(0));
      dt.items.add(new File([bytes], item.name, { type: item.type }));
    }
    return dt;
  }, files);
  await zone.dispatchEvent("dragenter", { dataTransfer });
  await zone.dispatchEvent("dragover", { dataTransfer });
  await zone.dispatchEvent("drop", { dataTransfer });
}

const toast = (page: Page, text: string | RegExp): Locator =>
  page.locator("[data-sonner-toast]").filter({ hasText: text }).first();

const saveButton = (page: Page): Locator => page.getByTestId("save-candidate");

test.beforeEach(async ({ page }) => {
  // A dirty add-candidate form registers a beforeunload guard; accept it when navigating away.
  page.on("dialog", (dialog) => void dialog.accept().catch(() => undefined));
  await loginAsRecruiter(page);
});

test.describe("Required fields (B3/B6)", () => {
  test("an incomplete form cannot be saved and the click scrolls to the first error", async ({
    page,
  }) => {
    const stamp = Date.now();
    await open(page, "/candidates/new");

    // Required fields are marked and announced.
    for (const label of ["First name", "Last name", "Email", "Phone", "Job"]) {
      await expect(page.getByLabel(label, { exact: true })).toHaveAttribute(
        "aria-required",
        "true",
      );
    }
    await expect(saveButton(page)).toBeDisabled();

    await page.getByLabel("First name", { exact: true }).fill("Incomplete");
    await page.getByLabel("Last name", { exact: true }).fill(`Form${stamp}`);
    await page.getByLabel("Email", { exact: true }).fill(`incomplete.${stamp}@example.com`);
    // Phone and job are still missing: the button stays disabled.
    await expect(saveButton(page)).toBeDisabled();

    // The button is aria-disabled (not removed from the tab order), so a click explains why.
    const requests: Request[] = [];
    page.on("request", (r) => {
      if (r.method() === "POST" && /\/api\/v1\/candidates(\?|$)/.test(r.url())) requests.push(r);
    });
    await saveButton(page).click({ force: true });
    await expect(page.getByText("Enter phone number")).toBeVisible();
    await expect(page.getByText("Select a job")).toBeVisible();
    await expect(page.locator("#phone")).toBeFocused();
    expect(requests).toHaveLength(0);

    await page.getByLabel("Phone", { exact: true }).fill("+91 90000 77001");
    await expect(saveButton(page)).toBeDisabled();
    await page.getByLabel("Job", { exact: true }).selectOption({ label: ANDROID_JOB });
    await expect(saveButton(page)).toBeEnabled();
  });

  test("the server rejects an incomplete create even if the client check is bypassed", async ({
    page,
  }) => {
    await open(page, "/candidates/new");
    const result = await page.evaluate(async () => {
      const refresh = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        credentials: "include",
      });
      const { access_token: token } = (await refresh.json()) as { access_token: string };
      const body = new FormData();
      body.append("first_name", "No");
      body.append("last_name", "Phone");
      body.append("email", "no.phone@example.com");
      const response = await fetch("/api/v1/candidates", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body,
      });
      return { status: response.status, json: (await response.json()) as unknown };
    });
    expect(result.status).toBe(422);
    expect(JSON.stringify(result.json)).toContain("validation_error");
    expect(JSON.stringify(result.json)).toContain("phone");
    expect(JSON.stringify(result.json)).toContain("job_id");
  });
});

test.describe("Draft area (B1/B2/B5)", () => {
  test("dropping a CV stores a draft only; the candidate exists after Save", async ({
    page,
    context,
  }) => {
    const stamp = Date.now();
    const email = `draft.${stamp}@example.com`;
    const creates: string[] = [];
    const draftUploads: string[] = [];
    page.on("request", (r) => {
      if (r.method() !== "POST") return;
      if (/\/api\/v1\/candidates(\?|$)/.test(r.url())) creates.push(r.url());
      if (/\/api\/v1\/candidates\/drafts\/[^/]+\/files$/.test(r.url())) draftUploads.push(r.url());
    });

    await open(page, "/candidates/new");
    await dropFiles(page, [fixtureFile(CV_BACKEND)]);
    await expect(page.getByRole("listitem").filter({ hasText: "cv01_backend.pdf" })).toContainText(
      "Parsed",
      { timeout: 60_000 },
    );
    expect(draftUploads).toHaveLength(1);
    expect(creates).toHaveLength(0);

    // Prefilled from the CV, marked as such.
    await expect(page.getByLabel(/^First name/)).toHaveValue("Priya");
    await expect(page.getByText("from CV").first()).toBeVisible();

    await page.getByLabel(/^Email/).fill(email);
    await page.getByLabel(/^Phone/).fill(`+91 90000 5${String(stamp).slice(-4)}`);
    await page.getByLabel("Job", { exact: true }).selectOption({ label: ANDROID_JOB });

    // A second tab searching for that email finds nothing: the CV is only a draft.
    const other = await context.newPage();
    await open(other, `/candidates?q=${encodeURIComponent(email)}`);
    await other.waitForLoadState("networkidle");
    await expect(other.getByText(email)).toHaveCount(0);

    await saveButton(page).click();
    await expect(toast(page, /Candidate saved/)).toBeVisible({ timeout: 30_000 });
    await page.waitForURL(/\/candidates\/[^/?]+\?application=/, { timeout: 20_000 });
    // Saved through the draft commit, not the plain create endpoint.
    expect(creates).toHaveLength(0);

    await open(other, `/candidates?q=${encodeURIComponent(email)}`);
    await expect(other.getByText(email)).toBeVisible({ timeout: 20_000 });
    await other.close();
  });

  test("cancel deletes the draft", async ({ page }) => {
    const deletes: string[] = [];
    page.on("request", (r) => {
      if (r.method() === "DELETE" && /\/api\/v1\/candidates\/drafts\/[^/]+$/.test(r.url())) {
        deletes.push(r.url());
      }
    });
    await open(page, "/candidates/new");
    await dropFiles(page, [fixtureFile(CV_BACKEND)]);
    await expect(page.getByRole("listitem").filter({ hasText: "cv01_backend.pdf" })).toContainText(
      "Parsed",
      { timeout: 60_000 },
    );
    await page.getByRole("button", { name: "Cancel" }).click();
    await page.waitForURL("**/candidates", { timeout: 20_000 });
    await expect.poll(() => deletes.length, { timeout: 10_000 }).toBe(1);
  });
});

test.describe("Multi-CV review (B6)", () => {
  test("incomplete rows are flagged; complete rows save, the rest stay", async ({ page }) => {
    const stamp = Date.now();
    await open(page, "/candidates/new");
    await dropFiles(page, [fixtureFile(CV_BACKEND), fixtureFile(CV_FRONTEND)]);

    await expect(page.getByText("Review uploads")).toBeVisible({ timeout: 15_000 });
    const rows = page.getByTestId("review-row");
    await expect(rows).toHaveCount(2);
    await expect(page.getByLabel("First name for cv01_backend.pdf")).toHaveValue("Priya", {
      timeout: 60_000,
    });
    await expect(page.getByLabel("First name for cv02_frontend.pdf")).toHaveValue("Rahul");

    // Neither row has a job yet, so both are Incomplete and Save all is off.
    await expect(page.getByTestId("incomplete-badge")).toHaveCount(2);
    await expect(page.getByRole("button", { name: "Save all" })).toBeDisabled();
    await expect(page.getByRole("button", { name: /Save complete rows/ })).toBeDisabled();

    await page.getByLabel("Job for all rows").selectOption({ label: ANDROID_JOB });
    const first = "cv01_backend.pdf";
    const second = "cv02_frontend.pdf";
    await page.getByLabel(`Email for ${first}`).fill(`multi.one.${stamp}@example.com`);
    await page.getByLabel(`Phone for ${first}`).fill(`+91 90000 6${String(stamp).slice(-4)}`);
    await page.getByLabel(`Email for ${second}`).fill(`multi.two.${stamp}@example.com`);
    await page.getByLabel(`Phone for ${second}`).fill("");

    // Row one is complete, row two still lacks a phone.
    await expect(page.getByTestId("incomplete-badge")).toHaveCount(1);
    await expect(page.getByRole("button", { name: "Save all" })).toBeDisabled();
    await expect(page.getByRole("button", { name: /Save complete rows/ })).toBeEnabled();

    await page.getByRole("button", { name: /Save complete rows/ }).click();
    await expect(toast(page, /Candidate saved|Saved 1 candidate/)).toBeVisible({
      timeout: 30_000,
    });
    // The incomplete CV is still in the draft; its row is kept with what was typed.
    await expect(page.getByLabel(/^Email/)).toHaveValue(`multi.two.${stamp}@example.com`, {
      timeout: 15_000,
    });

    await page.getByLabel(/^Phone/).fill(`+91 90000 8${String(stamp).slice(-4)}`);
    await expect(saveButton(page)).toBeEnabled();
    await saveButton(page).click();
    await expect(toast(page, /Candidate saved/)).toBeVisible({ timeout: 30_000 });
  });
});
