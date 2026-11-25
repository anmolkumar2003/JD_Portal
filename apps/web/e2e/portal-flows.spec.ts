import fs from "node:fs";
import path from "node:path";

import { expect, test, type Locator, type Page } from "@playwright/test";

import { loginAsRecruiter, open } from "./helpers/auth";

/**
 * Portal flows covered end to end (requirement ids in docs/requirements.md):
 * manual add + salary, CV drag-and-drop (single / triple with duplicate / wrong type / >5 MB),
 * parsed-data correction with re-score, notes with @mention, tags + shortlist, email send,
 * bulk actions, kanban drag, Ctrl/Cmd+K palette, CSV download, document rename/delete and
 * interview ratings. Runs against the seeded demo stack (`make test-e2e`).
 *
 * Responsive screenshots are NOT part of this suite (see `make test-e2e-screenshots`).
 */

const FIXTURES = path.resolve(__dirname, "fixtures");
const CV_BACKEND = path.join(FIXTURES, "cv01_backend.pdf");
const CV_FRONTEND = path.join(FIXTURES, "cv02_frontend.pdf");
const WRONG_TYPE = path.join(FIXTURES, "wrong-type.exe"); // starts with "MZ" (Windows executable)

const MAILPIT_URL = process.env.MAILPIT_URL ?? "http://mailpit:8025";
const MAX_CV_BYTES = 5 * 1024 * 1024;
const ANDROID_JOB = "Senior Android Developer";

const seededEmail = (n: number) => `demo${String(n).padStart(2, "0")}@candidates.demo`;

type DropFile = { name: string; type: string; base64?: string; size?: number };

function fixtureFile(file: string, name = path.basename(file), type = "application/pdf"): DropFile {
  return { name, type, base64: fs.readFileSync(file).toString("base64") };
}

/** Fires a real `drop` event with a DataTransfer on the multi-CV dropzone. */
async function dropFiles(page: Page, files: DropFile[]): Promise<void> {
  const zone = page
    .getByText("Drop CV files here")
    .locator("xpath=ancestor::div[contains(@class,'border-dashed')][1]");
  await expect(zone).toBeVisible();
  const dataTransfer = await page.evaluateHandle((items) => {
    const dt = new DataTransfer();
    for (const item of items) {
      const bytes = item.base64
        ? Uint8Array.from(atob(item.base64), (c) => c.charCodeAt(0))
        : new Uint8Array(item.size ?? 0).fill(0x30);
      dt.items.add(new File([bytes], item.name, { type: item.type }));
    }
    return dt;
  }, files);
  await zone.dispatchEvent("dragenter", { dataTransfer });
  await zone.dispatchEvent("dragover", { dataTransfer });
  await zone.dispatchEvent("drop", { dataTransfer });
}

const uploadItem = (page: Page, fileName: string): Locator =>
  page.getByRole("listitem").filter({ hasText: fileName });

async function openProfileOf(page: Page, email: string): Promise<void> {
  await open(page, `/candidates?q=${encodeURIComponent(email)}`);
  await expect(page.getByText(email)).toBeVisible({ timeout: 20_000 });
  await page.getByText(email).click();
  await page.getByRole("link", { name: /Full profile/ }).click();
  await page.waitForURL(/\/candidates\/[^/?]+\?application=/, { timeout: 20_000 });
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
}

async function gotoTab(page: Page, name: string | RegExp): Promise<void> {
  await page.getByRole("tab", { name }).click();
}

const toast = (page: Page, text: string | RegExp): Locator =>
  page.locator("[data-sonner-toast]").filter({ hasText: text }).first();

test.beforeEach(async ({ page }) => {
  // A dirty add-candidate form registers a beforeunload guard; accept it when navigating away.
  page.on("dialog", (dialog) => void dialog.accept().catch(() => undefined));
  await loginAsRecruiter(page);
});

// ---------------------------------------------------------------------------------------------
// Add candidate: manual entry
// ---------------------------------------------------------------------------------------------
test.describe("Add candidate (manual)", () => {
  test("every field including salary is saved and shown on the profile", async ({ page }) => {
    const stamp = Date.now();
    const email = `manual.${stamp}@example.com`;
    await open(page, "/candidates/new");

    await page.getByLabel("First name", { exact: true }).fill("Manual");
    await page.getByLabel("Last name", { exact: true }).fill(`Entry${stamp}`);
    await page.getByLabel("Email", { exact: true }).fill(email);
    await page.getByLabel("Phone", { exact: true }).fill("+91 90000 11122");
    await page.getByLabel("Location", { exact: true }).fill("Pune, India");
    await page.getByLabel("Company", { exact: true }).fill("Acme Tools");
    await page.getByLabel("Title", { exact: true }).fill("Staff Engineer");
    await page.getByLabel("Experience (years)", { exact: true }).fill("7.5");
    await page.getByLabel("Notice period (days)", { exact: true }).fill("45");
    await page.getByLabel("LinkedIn", { exact: true }).fill("https://linkedin.com/in/manual-entry");
    await page.getByLabel("Portfolio", { exact: true }).fill("https://example.com/portfolio");
    await page.getByLabel("Department", { exact: true }).selectOption({ index: 1 });
    await page.getByLabel("Job", { exact: true }).selectOption({ label: ANDROID_JOB });
    await page.getByLabel("Source", { exact: true }).selectOption({ label: "Referral" });
    await page.getByLabel("Tags", { exact: true }).fill("e2e-manual, senior");

    const current = page.getByRole("group", { name: "Current CTC" });
    await current.getByLabel("Amount").fill("1200000");
    await current.getByLabel("Currency").selectOption("INR");
    await current.getByLabel("Unit").selectOption("pa");

    const expected = page.getByRole("group", { name: "Expected CTC" });
    await expected.getByLabel("Amount").fill("1500000");
    await expected.getByLabel("Currency").selectOption("INR");
    await expected.getByLabel("Unit").selectOption("pa");
    await expected.getByLabel("Negotiable").check();

    const offered = page.getByRole("group", { name: "Offered CTC" });
    await offered.getByLabel("Amount").fill("5000");
    await offered.getByLabel("Currency").selectOption("USD");
    await offered.getByLabel("Unit").selectOption("pm");

    await page.getByRole("button", { name: "Save candidate" }).click();
    await expect(toast(page, /Candidate saved/)).toBeVisible({ timeout: 20_000 });
    await page.waitForURL(/\/candidates\/[^/?]+\?application=/, { timeout: 20_000 });

    await expect(page.getByRole("heading", { level: 1 })).toContainText(`Manual Entry${stamp}`);
    await expect(page.getByText(email)).toBeVisible();
    await expect(page.getByText("Acme Tools")).toBeVisible();
    await expect(page.getByText("Staff Engineer").first()).toBeVisible();
    await expect(page.getByText("Pune, India")).toBeVisible();
    await expect(page.getByText(/7\.5 years/)).toBeVisible();
    await expect(page.getByText("Referral", { exact: true })).toBeVisible();
    await expect(page.getByText(/Current: 1,200,000 INR\/yr/)).toBeVisible();
    await expect(page.getByText(/Expected: 1,500,000 INR\/yr \(negotiable\)/)).toBeVisible();
    await expect(page.getByText(/Offered: 5,000 USD\/mo/)).toBeVisible();
    await expect(page.getByText("e2e-manual", { exact: true })).toBeVisible();
    await expect(page.getByText("senior", { exact: true })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------------------------
// Add candidate: CV dropzone
// ---------------------------------------------------------------------------------------------
test.describe("CV dropzone", () => {
  test("three files with a duplicate are parsed into a review table and saved", async ({
    page,
  }) => {
    const stamp = Date.now();
    await open(page, "/candidates/new");
    await dropFiles(page, [
      fixtureFile(CV_BACKEND),
      fixtureFile(CV_FRONTEND),
      // Same bytes as the first file under another name: the same person uploaded twice.
      fixtureFile(CV_BACKEND, "cv01_backend_copy.pdf"),
    ]);

    await expect(page.getByText("Review uploads")).toBeVisible({ timeout: 15_000 });
    for (const name of ["cv01_backend.pdf", "cv02_frontend.pdf", "cv01_backend_copy.pdf"]) {
      await expect(uploadItem(page, name).first()).toBeVisible();
    }
    // Parsing fills the rows; wait for each to arrive.
    await expect(page.getByLabel("First name for cv01_backend.pdf")).toHaveValue("Priya", {
      timeout: 60_000,
    });
    await expect(page.getByLabel("First name for cv02_frontend.pdf")).toHaveValue("Rahul");
    await expect(page.getByLabel("First name for cv01_backend_copy.pdf")).toHaveValue("Priya");

    const rowOf = (file: string) => page.getByRole("row").filter({ hasText: file });
    const emailOf = (file: string) => rowOf(file).getByRole("textbox").nth(2);

    // The duplicate parses to the identical e-mail address, which is how the API de-duplicates.
    const first = await emailOf("cv01_backend.pdf").inputValue();
    expect(first).toBeTruthy();
    await expect(emailOf("cv01_backend_copy.pdf")).toHaveValue(first);

    // Use unique addresses so the run is repeatable; the duplicate keeps matching the original.
    const dupEmail = `dup.${stamp}@example.com`;
    await emailOf("cv01_backend.pdf").fill(dupEmail);
    await emailOf("cv01_backend_copy.pdf").fill(dupEmail);
    await emailOf("cv02_frontend.pdf").fill(`rahul.${stamp}@example.com`);

    // Phone and job are required on every row (B3).
    await page.getByLabel("Job for all rows").selectOption({ label: ANDROID_JOB });
    for (const [n, file] of [
      "cv01_backend.pdf",
      "cv02_frontend.pdf",
      "cv01_backend_copy.pdf",
    ].entries()) {
      await page.getByLabel(`Phone for ${file}`).fill(`+91 90000 3${n}${String(stamp).slice(-3)}`);
    }

    await page.getByRole("button", { name: "Save all" }).click();
    await expect(toast(page, /Saved 3 candidates/)).toBeVisible({ timeout: 45_000 });
  });

  test("wrong file type and oversized files are rejected before upload", async ({ page }) => {
    await open(page, "/candidates/new");

    await dropFiles(page, [fixtureFile(WRONG_TYPE, "malware.exe", "application/x-msdownload")]);
    const wrong = uploadItem(page, "malware.exe");
    await expect(wrong).toContainText("Upload a PDF or Word (.docx) file.");

    await dropFiles(page, [
      { name: "huge-cv.pdf", type: "application/pdf", size: MAX_CV_BYTES + 1024 },
    ]);
    const big = uploadItem(page, "huge-cv.pdf");
    await expect(big).toContainText("exceeds 5 MB");
    await expect(big).toContainText("The file must be 5 MB or smaller.");

    // Nothing valid was added, so the form was not switched to review mode or auto-filled.
    await expect(page.getByLabel("First name", { exact: true })).toHaveValue("");
  });

  test("executable bytes with a .pdf name are rejected by the server-side parse", async ({
    page,
  }) => {
    await open(page, "/candidates/new");
    await dropFiles(page, [fixtureFile(WRONG_TYPE, "resume-fake.pdf", "application/pdf")]);
    const item = uploadItem(page, "resume-fake.pdf");
    await expect(item).toBeVisible();
    // Client checks only the extension; the API checks the real type from the file contents.
    await expect(item).not.toContainText("Parsing", { timeout: 30_000 });
    await expect(item).not.toContainText("Parsed");
    await expect(page.getByLabel("First name", { exact: true })).toHaveValue("");
  });
});

// ---------------------------------------------------------------------------------------------
// One candidate created from a dropped CV, then corrected / documents edited
// ---------------------------------------------------------------------------------------------
test.describe("CV candidate lifecycle", () => {
  test.describe.configure({ mode: "serial" });
  let profileUrl = "";

  test("single dropped CV prefills the form and saves with a job and salary", async ({ page }) => {
    const stamp = Date.now();
    await open(page, "/candidates/new");
    await dropFiles(page, [fixtureFile(CV_BACKEND)]);
    await expect(uploadItem(page, "cv01_backend.pdf")).toContainText("Parsed", { timeout: 60_000 });

    await expect(page.getByLabel(/^First name/)).toHaveValue("Priya");
    await expect(page.getByLabel(/^Last name/)).toHaveValue("Sharma");
    await expect(page.getByText("from CV").first()).toBeVisible();

    await page.getByLabel(/^Email/).fill(`priya.${stamp}@example.com`);
    await page.getByLabel(/^Phone/).fill(`+91 90000 4${String(stamp).slice(-4)}`);
    await page.getByLabel("Job", { exact: true }).selectOption({ label: ANDROID_JOB });
    await page.getByRole("group", { name: "Expected CTC" }).getByLabel("Amount").fill("1800000");
    await page.getByRole("button", { name: "Save candidate" }).click();

    await expect(toast(page, /Candidate saved/)).toBeVisible({ timeout: 30_000 });
    await page.waitForURL(/\/candidates\/[^/?]+\?application=/, { timeout: 20_000 });
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Priya Sharma");
    profileUrl = page.url();
  });

  test("parsed data can be corrected and the advisory match score is recalculated", async ({
    page,
  }) => {
    test.skip(!profileUrl, "No CV candidate from the previous test");
    test.setTimeout(240_000);
    await open(page, profileUrl);

    // The worker parses the CV asynchronously; reload until the analysis is ready.
    const heading = page.getByText("Correct parsed data");
    await expect(async () => {
      await page.reload();
      await page.locator("html[data-hydrated]").waitFor({ state: "attached" });
      await gotoTab(page, "Match Analysis");
      await expect(heading).toBeVisible({ timeout: 5_000 });
    }).toPass({ timeout: 150_000, intervals: [3_000, 5_000, 8_000] });

    const scoreLabel = async () =>
      (await page
        .getByLabel(/Match score \d+/)
        .first()
        .getAttribute("aria-label")) ?? "";
    const before = await scoreLabel();
    expect(before).toMatch(/Match score \d+/);

    await page
      .getByLabel("Skills (comma-separated)")
      .fill("Kotlin, Android SDK, Jetpack Compose, Coroutines, Room");
    await page.getByLabel("Experience (years)").fill("9");

    const patched = page.waitForResponse(
      (r) => r.url().includes("/parsed-profiles/") && r.request().method() === "PATCH",
    );
    await page.getByRole("button", { name: /Save corrections & re-score/ }).click();
    expect((await patched).ok()).toBe(true);

    // The corrected skills are persisted and the score is recomputed from them (advisory only).
    await expect.poll(scoreLabel, { timeout: 60_000 }).not.toBe(before);
    await page.reload();
    await page.locator("html[data-hydrated]").waitFor({ state: "attached" });
    await gotoTab(page, "Match Analysis");
    await expect(page.getByLabel("Skills (comma-separated)")).toHaveValue(/Jetpack Compose/, {
      timeout: 30_000,
    });
  });

  test("document can be renamed and then deleted", async ({ page }) => {
    test.skip(!profileUrl, "No CV candidate from the previous test");
    await open(page, profileUrl);
    await gotoTab(page, "CV");

    const rename = page.getByRole("button", { name: "Rename" });
    await expect(rename).toBeVisible({ timeout: 20_000 });
    await rename.click();
    const dialog = page.getByRole("dialog", { name: "Rename document" });
    await dialog.getByLabel("File name").fill("priya-renamed.pdf");
    await dialog.getByRole("button", { name: "Save" }).click();
    await expect(toast(page, "Document renamed")).toBeVisible();
    await expect(page.getByText("priya-renamed.pdf")).toBeVisible();

    await page.getByRole("button", { name: "Delete", exact: true }).click();
    await page.getByRole("button", { name: "Delete document" }).click();
    await expect(toast(page, "Document deleted")).toBeVisible();
    await expect(page.getByText("No CV uploaded")).toBeVisible({ timeout: 15_000 });
  });
});

// ---------------------------------------------------------------------------------------------
// Candidate profile actions on seeded candidates
// ---------------------------------------------------------------------------------------------
test.describe("Candidate profile", () => {
  test("note with an @mention records the mentioned teammate", async ({ page }) => {
    await openProfileOf(page, seededEmail(2));
    await gotoTab(page, "Notes");

    const body = page.getByLabel("Note body");
    await body.fill("Strong systems answers, looping in @Ish");
    // The suggestion list appears while the text after "@" matches a teammate.
    await page.getByRole("button", { name: "@Isha Interviewer" }).click();
    await expect(body).toHaveValue(/@Isha Interviewer\s*$/);

    await body.press("End");
    await body.pressSequentially("for the next round");
    await page.getByRole("button", { name: "Save note" }).click();

    await expect(toast(page, "Note added")).toBeVisible();
    await expect(page.getByText("for the next round").first()).toBeVisible();
    await expect(page.getByText(/Mentioned:\s*Isha Interviewer/)).toBeVisible();
  });

  test("tags can be added and removed, and the candidate can be shortlisted", async ({ page }) => {
    await openProfileOf(page, seededEmail(3));
    const tag = `e2e-tag-${Date.now() % 100000}`;

    await page.getByLabel("New tag").fill(tag);
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await expect(page.getByText(tag, { exact: true })).toBeVisible();

    const star = page.getByRole("button", { name: /(Add to|Remove from) shortlist/ });
    const wasShortlisted = (await star.getAttribute("aria-label")) === "Remove from shortlist";
    await star.click();
    await expect(
      page.getByRole("button", {
        name: wasShortlisted ? "Add to shortlist" : "Remove from shortlist",
      }),
    ).toBeVisible();

    // Both changes persist across a reload.
    await page.reload();
    await page.locator("html[data-hydrated]").waitFor({ state: "attached" });
    await expect(page.getByText(tag, { exact: true })).toBeVisible();
    await expect(
      page.getByRole("button", {
        name: wasShortlisted ? "Add to shortlist" : "Remove from shortlist",
      }),
    ).toBeVisible();

    await page.getByRole("button", { name: `Remove tag ${tag}` }).click();
    await expect(page.getByText(tag, { exact: true })).toHaveCount(0);
  });

  test("email is composed and sent", async ({ page, request }) => {
    const email = seededEmail(4);
    const subject = `E2E hello ${Date.now()}`;
    await openProfileOf(page, email);

    await page.getByRole("button", { name: "Email", exact: true }).first().click();
    const dialog = page.getByRole("dialog", { name: "Email candidate" });
    await expect(dialog.getByLabel("To")).toHaveValue(email);
    await dialog.getByLabel("Subject").fill(subject);
    await dialog
      .getByLabel("Body")
      .fill("Hi {{candidate_name}}, thanks for applying to {{job_title}}.");
    await dialog.getByRole("button", { name: "Preview variables" }).click();
    await expect(dialog.getByLabel("Body")).not.toHaveValue(/\{\{/, { timeout: 15_000 });
    await dialog.getByRole("button", { name: "Send" }).click();
    await expect(toast(page, "Email queued")).toBeVisible({ timeout: 15_000 });
    await expect(dialog).toBeHidden();

    // The worker delivers through Mailpit (reachable only from inside the e2e network).
    const probe = await request.get(`${MAILPIT_URL}/api/v1/info`).catch(() => null);
    if (!probe?.ok()) {
      test.info().annotations.push({
        type: "mailpit",
        description: `Mailpit not reachable at ${MAILPIT_URL}; delivery not verified`,
      });
      return;
    }
    await expect
      .poll(
        async () => {
          const res = await request.get(
            `${MAILPIT_URL}/api/v1/search?query=${encodeURIComponent(`subject:"${subject}"`)}`,
          );
          const data = (await res.json()) as { messages_count?: number };
          return data.messages_count ?? 0;
        },
        { timeout: 45_000, intervals: [1_000, 2_000, 3_000] },
      )
      .toBeGreaterThan(0);
  });

  test("interview rating can be added, edited and deleted", async ({ page }) => {
    await openProfileOf(page, seededEmail(5));
    await gotoTab(page, "Interviews");

    await page.getByRole("button", { name: "Add rating" }).click();
    const dialog = page.getByRole("dialog", { name: "New interview rating" });
    await dialog.getByLabel("Round", { exact: true }).fill("Technical round 1");
    await dialog.getByLabel("Interviewer", { exact: true }).fill("Isha Interviewer");
    await dialog.getByLabel("Mode").selectOption("video");
    await dialog.getByLabel(/^Overall/).fill("4");
    await dialog.getByLabel("Recommendation").selectOption({ label: "Yes" });
    await dialog.getByLabel("Comments").fill("Clear communicator, solid fundamentals.");
    await dialog.getByLabel("Strengths").fill("Systems design");
    await dialog.getByLabel("Concerns").fill("Limited exposure to Kotlin");
    await dialog.getByPlaceholder("Skill name").fill("Kotlin");
    await dialog.getByRole("button", { name: "Add skill" }).click();
    await dialog.getByLabel("Rating for Kotlin").fill("3");
    await dialog.getByRole("button", { name: "Save" }).click();

    await expect(toast(page, "Rating saved")).toBeVisible();
    await expect(page.getByText("Technical round 1").first()).toBeVisible();
    await expect(page.getByText(/Overall:\s*4\s*\/ 5/)).toBeVisible();
    await expect(page.getByText("Kotlin: 3")).toBeVisible();

    // Edit: bump the overall rating.
    await page.getByRole("button", { name: "Edit", exact: true }).first().click();
    const edit = page.getByRole("dialog", { name: "Edit interview rating" });
    await edit.getByLabel(/^Overall/).fill("5");
    await edit.getByRole("button", { name: "Save" }).click();
    await expect(toast(page, "Rating updated")).toBeVisible();
    await expect(page.getByText(/Overall:\s*5\s*\/ 5/)).toBeVisible();

    // The profile header interview average reflects the rating.
    await expect(page.getByLabel("Advisory scores")).toContainText(/5(\.0)? \/ 5/);

    // Delete (confirm dialog).
    await page.getByRole("button", { name: "Delete rating" }).first().click();
    await page.getByRole("button", { name: "Delete", exact: true }).click();
    await expect(page.getByText("No interview ratings")).toBeVisible({ timeout: 15_000 });
  });
});

// ---------------------------------------------------------------------------------------------
// Lists, boards, palette, export
// ---------------------------------------------------------------------------------------------
test.describe("Bulk actions", () => {
  test("select rows, tag them, move them and reject with a reason", async ({ page }) => {
    await open(page, `/candidates?q=${encodeURIComponent("@candidates.demo")}`);
    const rows = page.getByRole("checkbox", { name: "Select row" });
    await expect(rows.first()).toBeVisible({ timeout: 20_000 });
    expect(await rows.count()).toBeGreaterThanOrEqual(3);

    const toolbar = page.getByRole("toolbar", { name: "Bulk actions" });
    await rows.nth(0).check();
    await rows.nth(1).check();
    await expect(toolbar).toContainText("2 selected");

    const tag = `e2e-bulk-${Date.now() % 100000}`;
    await toolbar.getByLabel("Tag to add").fill(tag);
    await toolbar.getByRole("button", { name: "Tag", exact: true }).click();
    await expect(toast(page, /Tagged 2 application/)).toBeVisible({ timeout: 15_000 });
    await expect(toolbar).toBeHidden(); // selection cleared after the action

    await rows.nth(2).check();
    await rows.nth(3).check();
    await toolbar.getByLabel("Move to stage").selectOption({ label: "Screening" });
    await toolbar.getByRole("button", { name: "Move", exact: true }).click();
    await expect(toast(page, /Moved 2 application/)).toBeVisible({ timeout: 15_000 });

    // Reject requires a reason.
    await rows.nth(4).check();
    await toolbar.getByRole("button", { name: "Reject" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Reason").fill("E2E bulk rejection — not a fit for this opening");
    await dialog.getByRole("button", { name: "Reject candidate" }).click();
    await expect(toast(page, /Rejected 1 application/)).toBeVisible({ timeout: 15_000 });
  });
});

test.describe("Kanban", () => {
  test("a card can be dragged to another stage and the move persists", async ({ page }) => {
    await open(page, "/jobs");
    await page.getByRole("link", { name: ANDROID_JOB }).first().click();
    await page.getByRole("tab", { name: /Pipeline/i }).click();

    const applied = page.getByRole("region", { name: /^Applied,/ });
    const screening = page.getByRole("region", { name: /^Screening,/ });
    const card = applied.getByRole("article").first();
    await expect(card).toBeVisible({ timeout: 20_000 });
    const name = (await card.locator("p.truncate.font-medium").first().textContent())?.trim() ?? "";
    expect(name).toBeTruthy();

    const handle = card.locator("p.truncate.font-medium").first();
    const from = await handle.boundingBox();
    const to = await screening.locator("header").boundingBox();
    expect(from && to).toBeTruthy();

    // dnd-kit's PointerSensor needs real pointer events and a few intermediate moves.
    await page.mouse.move(from!.x + 10, from!.y + 5);
    await page.mouse.down();
    await page.mouse.move(from!.x + 30, from!.y + 25, { steps: 5 });
    await page.mouse.move(to!.x + to!.width / 2, to!.y + to!.height + 40, { steps: 20 });
    await page.mouse.up();

    await expect(screening.getByText(name)).toBeVisible({ timeout: 15_000 });
    await expect(applied.getByText(name)).toHaveCount(0);

    await page.reload();
    await page.locator("html[data-hydrated]").waitFor({ state: "attached" });
    await page.getByRole("tab", { name: /Pipeline/i }).click();
    await expect(page.getByRole("region", { name: /^Screening,/ }).getByText(name)).toBeVisible({
      timeout: 20_000,
    });
  });
});

test.describe("Command palette", () => {
  test("Ctrl+K and Cmd+K toggle it; search and navigation work from the keyboard", async ({
    page,
  }) => {
    await open(page, "/dashboard");
    const palette = page.getByRole("dialog", { name: "Command palette" });
    const input = page.getByLabel("Command palette search");

    await page.keyboard.press("Control+k");
    await expect(palette).toBeVisible();
    await expect(input).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(palette).toBeHidden();

    await page.keyboard.press("Meta+k");
    await expect(palette).toBeVisible();
    await page.keyboard.press("Meta+k"); // toggles closed
    await expect(palette).toBeHidden();

    // Navigation command.
    await page.keyboard.press("Control+k");
    await input.fill("Jobs");
    await expect(page.getByRole("option", { name: /Jobs/ }).first()).toBeVisible();
    await page.keyboard.press("Enter");
    await page.waitForURL("**/jobs");

    // Candidate search hit opens the candidate.
    await page.keyboard.press("Control+k");
    await input.fill(seededEmail(1));
    const hit = page.getByRole("option").filter({ hasText: seededEmail(1) });
    await expect(hit.first()).toBeVisible({ timeout: 15_000 });
    await hit.first().click();
    await page.waitForURL(/\/candidates\/[^/]+/, { timeout: 20_000 });
  });
});

test.describe("CSV export", () => {
  test("dashboard analytics export downloads a CSV file", async ({ page }) => {
    await open(page, "/dashboard");
    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 30_000 }),
      page.getByRole("button", { name: "Export CSV" }).click(),
    ]);
    expect(download.suggestedFilename()).toBe("analytics.csv");
    const file = await download.path();
    expect(file).toBeTruthy();
    const text = fs.readFileSync(file, "utf8");
    expect(text.trim().length).toBeGreaterThan(0);
    expect(text.split(/\r?\n/)[0]).toContain(",");
  });
});
