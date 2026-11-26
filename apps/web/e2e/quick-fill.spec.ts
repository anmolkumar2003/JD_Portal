import { expect, test, type Locator, type Page, type Request } from "@playwright/test";

import { loginAsHrAdmin, open } from "./helpers/auth";

/**
 * Quick fill on Add candidate and on the profile edit dialog: paste text, Extract, edit a value,
 * Apply, Undo, then save under the normal required-field rules. Nothing is saved by Quick fill
 * itself, and HR-typed values are only replaced when "Replace" is ticked.
 */

const ANDROID_JOB = "Senior Android Developer";
const seededEmail = (n: number) => `demo${String(n).padStart(2, "0")}@candidates.demo`;

const toast = (page: Page, text: string | RegExp): Locator =>
  page.locator("[data-sonner-toast]").filter({ hasText: text }).first();

const tid = (page: Page, id: string): Locator => page.getByTestId(id);
const saveButton = (page: Page): Locator => page.getByTestId("save-candidate");

/** Records POSTs that would create a candidate, so a test can prove nothing was saved. */
function watchCreates(page: Page): Request[] {
  const created: Request[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && /\/api\/v1\/candidates(\?|$)/.test(r.url())) created.push(r);
  });
  return created;
}

async function openCard(page: Page): Promise<void> {
  const card = tid(page, "quick-fill-card");
  await expect(card).toBeVisible();
  const textbox = card.getByRole("textbox");
  if (!(await textbox.isVisible())) await card.getByRole("button", { name: /Quick fill/ }).click();
  await expect(textbox).toBeVisible();
}

async function extract(page: Page, text: string): Promise<void> {
  await openCard(page);
  await tid(page, "quick-fill-card").getByRole("textbox").fill(text);
  const parsed = page.waitForResponse(
    (r) => r.url().includes("/candidates/quick-parse") && r.request().method() === "POST",
  );
  await tid(page, "quick-fill-extract").click();
  expect((await parsed).ok()).toBe(true);
}

test.beforeEach(async ({ page }) => {
  // A dirty add-candidate form registers a beforeunload guard; accept it when navigating away.
  page.on("dialog", (dialog) => void dialog.accept().catch(() => undefined));
  await loginAsHrAdmin(page);
});

test.describe("Quick fill on Add candidate", () => {
  test("type, Extract, edit a value, Apply, Undo, then save under the required-field rules", async ({
    page,
  }) => {
    const stamp = Date.now();
    const email = `qf.${stamp}@example.com`;
    const phone = `+91 90000 5${String(stamp).slice(-4)}`;
    const created = watchCreates(page);
    await open(page, "/candidates/new");

    // The example sentence from the placeholder, with a unique email (no phone: required later).
    await extract(
      page,
      `Rahul Sharma, Pune, 5 years, current 8 LPA, expected 12 LPA, 30 days notice, ${email}`,
    );
    const preview = tid(page, "quick-fill-preview");
    await expect(preview).toBeVisible();

    // Found values, confidence badges and "Not found" rows are shown; high rows start ticked.
    await expect(tid(page, "quick-fill-value-first_name")).toHaveValue("Rahul");
    await expect(tid(page, "quick-fill-value-email")).toHaveValue(email);
    await expect(tid(page, "quick-fill-confidence-first_name")).toContainText(/high/i);
    await expect(tid(page, "quick-fill-check-first_name")).toBeChecked();
    await expect(tid(page, "quick-fill-row-phone")).toContainText("Not found");
    await expect(tid(page, "quick-fill-check-phone")).toBeDisabled();

    // Nothing is in the form yet.
    await expect(page.locator("#first_name")).toHaveValue("");

    // The HR user edits a found value before applying.
    await tid(page, "quick-fill-value-expected_ctc").fill("1300000");
    await tid(page, "quick-fill-apply-selected").click();

    await expect(page.locator("#first_name")).toHaveValue("Rahul");
    await expect(page.locator("#last_name")).toHaveValue("Sharma");
    await expect(page.locator("#email")).toHaveValue(email);
    await expect(page.locator("[id='expected_ctc.amount']")).toHaveValue("1300000");
    await expect(page.locator("[id='current_ctc.amount']")).toHaveValue("800000");
    await expect(tid(page, "quick-fill-badge-first_name")).toContainText("from quick fill");

    // Applying only fills the form: nothing is saved, and the required rules still block Save.
    expect(created).toHaveLength(0);
    await expect(saveButton(page)).toBeDisabled();

    // Undo puts the form back and removes the badges.
    await tid(page, "quick-fill-undo").click();
    await expect(page.locator("#first_name")).toHaveValue("");
    await expect(page.locator("#email")).toHaveValue("");
    await expect(page.locator("[id='expected_ctc.amount']")).toHaveValue("");
    await expect(tid(page, "quick-fill-badge-first_name")).toHaveCount(0);
    await expect(tid(page, "quick-fill-undo")).toHaveCount(0);

    // Apply again, then finish the required fields by hand and save.
    await extract(
      page,
      `Rahul Sharma, Pune, 5 years, current 8 LPA, expected 12 LPA, 30 days notice, ${email}`,
    );
    await tid(page, "quick-fill-apply-high").click();
    await expect(page.locator("#first_name")).toHaveValue("Rahul");
    await expect(saveButton(page)).toBeDisabled(); // phone and job still missing
    await page.locator("#phone").fill(phone);
    await expect(saveButton(page)).toBeDisabled(); // job still missing
    await page.getByLabel("Job", { exact: true }).selectOption({ label: ANDROID_JOB });
    await expect(saveButton(page)).toBeEnabled();
    await saveButton(page).click();

    await expect(toast(page, /Candidate saved/)).toBeVisible({ timeout: 30_000 });
    await page.waitForURL(/\/candidates\/[^/?]+\?application=/, { timeout: 20_000 });
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Rahul Sharma");
    expect(created).toHaveLength(1);
  });

  test("typed values are kept unless the row is ticked and marked Replace", async ({ page }) => {
    await open(page, "/candidates/new");
    await page.locator("#first_name").fill("Manual");

    await extract(page, "Rahul Sharma, Pune");
    const row = tid(page, "quick-fill-row-first_name");
    await expect(row).toContainText("Manual"); // the current form value is shown next to the found one
    await expect(tid(page, "quick-fill-replace-first_name")).not.toBeChecked();

    // Applying with Replace unticked leaves the typed value alone but fills the empty fields.
    await tid(page, "quick-fill-apply-selected").click();
    await expect(page.locator("#first_name")).toHaveValue("Manual");
    await expect(page.locator("#last_name")).toHaveValue("Sharma");
    await expect(tid(page, "quick-fill-badge-first_name")).toHaveCount(0);

    // Ticking Replace overwrites it, and Undo brings the typed value back.
    await extract(page, "Rahul Sharma, Pune");
    await tid(page, "quick-fill-replace-first_name").check();
    await tid(page, "quick-fill-apply-selected").click();
    await expect(page.locator("#first_name")).toHaveValue("Rahul");
    await expect(tid(page, "quick-fill-badge-first_name")).toContainText("from quick fill");
    await tid(page, "quick-fill-undo").click();
    await expect(page.locator("#first_name")).toHaveValue("Manual");
  });

  test("an ambiguous salary is never guessed: it asks which one", async ({ page }) => {
    await open(page, "/candidates/new");
    await extract(page, "Rahul, Pune, 8 LPA, 12 LPA");

    await expect(tid(page, "quick-fill-choice-current_ctc")).toBeVisible();
    await expect(tid(page, "quick-fill-check-current_ctc")).not.toBeChecked();
    await expect(tid(page, "quick-fill-warnings")).toContainText(/label|which/i);

    await tid(page, "quick-fill-apply-high").click();
    await expect(page.locator("[id='current_ctc.amount']")).toHaveValue("");
    await expect(page.locator("[id='expected_ctc.amount']")).toHaveValue("");
  });

  test("text about several candidates is not mixed: pick one", async ({ page }) => {
    await open(page, "/candidates/new");
    await extract(page, "Rahul Sharma, Pune, 5 years\nPriya Nair, Mumbai, 3 years");

    await expect(tid(page, "quick-fill-multiple")).toBeVisible();
    await expect(tid(page, "quick-fill-preview")).toHaveCount(0);
    await expect(page.locator("#first_name")).toHaveValue("");

    await tid(page, "quick-fill-segment-1").click();
    await expect(tid(page, "quick-fill-value-first_name")).toHaveValue("Priya");
    await expect(tid(page, "quick-fill-value-last_name")).toHaveValue("Nair");
    await expect(tid(page, "quick-fill-multiple")).toHaveCount(0);
  });

  test("empty and unreadable text does not break the form", async ({ page }) => {
    await open(page, "/candidates/new");
    await openCard(page);
    await expect(tid(page, "quick-fill-extract")).toBeDisabled(); // empty box

    await extract(page, "\u{1F600}\u{1F600} \u0930\u092E\u0947\u0936 ???");
    await expect(page.locator("#first_name")).toHaveValue("");
    await expect(tid(page, "quick-fill-card")).toBeVisible();
  });

  test("recent entries are kept on the page only", async ({ page }) => {
    await open(page, "/candidates/new");
    await extract(page, "Rahul Sharma, Pune");
    await expect(tid(page, "quick-fill-history")).toContainText("Rahul Sharma");

    await open(page, "/candidates/new");
    await openCard(page);
    await expect(tid(page, "quick-fill-history")).toHaveCount(0);
  });
});

test.describe("Quick fill on the candidate profile", () => {
  test("fills the edit form, marks the fields and saves only on Save changes", async ({ page }) => {
    await open(page, "/candidates");
    // Look the seeded candidate up through the API so the test does not depend on the drawer.
    const target = await page.evaluate(async (email) => {
      const refresh = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        credentials: "include",
      });
      const { access_token: token } = (await refresh.json()) as { access_token: string };
      const response = await fetch(`/api/v1/applications?q=${encodeURIComponent(email)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const body = (await response.json()) as { items: { id: string; candidate_id: string }[] };
      return body.items[0] ?? null;
    }, seededEmail(3));
    expect(target).not.toBeNull();
    await open(page, `/candidates/${target?.candidate_id}?application=${target?.id}`);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    await page.getByRole("button", { name: "Edit", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Edit candidate" });
    await expect(dialog).toBeVisible();

    const patches: Request[] = [];
    page.on("request", (r) => {
      if (r.method() === "PATCH" && /\/api\/v1\/candidates\//.test(r.url())) patches.push(r);
    });

    const originalLocation = await dialog.locator("#edit-location").inputValue();
    const text = "Location: Chennai; Company: Zoho; Notice: 45 days";

    // A field that already holds a value is kept unless its Replace box is ticked.
    await extract(page, text);
    await tid(page, "quick-fill-apply-selected").click();
    await expect(dialog.locator("#edit-location")).toHaveValue(originalLocation);
    expect(patches).toHaveLength(0);

    await extract(page, text);
    const replaceBoxes = page.locator('[data-testid^="quick-fill-replace-"]');
    for (let i = 0; i < (await replaceBoxes.count()); i += 1) await replaceBoxes.nth(i).check();
    await tid(page, "quick-fill-apply-selected").click();

    await expect(dialog.locator("#edit-location")).toHaveValue("Chennai");
    await expect(dialog.locator("#edit-company")).toHaveValue("Zoho");
    await expect(dialog.locator("#edit-notice")).toHaveValue("45");
    await expect(tid(page, "quick-fill-badge-current_location")).toContainText("from quick fill");
    expect(patches).toHaveLength(0); // filling the form saves nothing

    // Undo restores what was there before.
    await tid(page, "quick-fill-undo").click();
    await expect(dialog.locator("#edit-location")).toHaveValue(originalLocation);

    // Apply again and save.
    await extract(page, text);
    for (let i = 0; i < (await replaceBoxes.count()); i += 1) await replaceBoxes.nth(i).check();
    await tid(page, "quick-fill-apply-selected").click();
    await dialog.getByRole("button", { name: "Save changes" }).click();

    await expect(toast(page, "Profile updated")).toBeVisible({ timeout: 20_000 });
    expect(patches).toHaveLength(1);
    await expect(page.getByText("Chennai").first()).toBeVisible();
  });
});
