import { expect, test } from "@playwright/test";
import { open, signUp } from "./helpers";

const RESUME = `CARA LIM
Customer Support Lead
Manila, Philippines
cara@example.com
https://linkedin.com/in/cara-lim

Summary
Customer support lead with 6 years in SaaS onboarding, QA, and team leadership.

Notice period: 30 days

Skills: onboarding, Zendesk, team leadership, QA, SQL

Experience
2020 - 2025 Support Lead at Acme
Cut response times by 40 percent and led a team of 8.

Education
2013 - 2017 BS Psychology, University of the Philippines`;

const RESUME_NO_COUNTRY = `CARA LIM
Customer Support Lead
cara@example.com

Summary
Customer support lead with 6 years in SaaS onboarding, QA, and team leadership.

Notice period: 30 days

Skills: onboarding, Zendesk, team leadership, QA, SQL

Experience
2020 - 2025 Support Lead at Acme
Cut response times by 40 percent and led a team of 8.`;

/** A one-page PDF with Helvetica text, so the upload path is exercised with a real file. */
function makePdf(lines: string[]): Buffer {
  const escape = (line: string) =>
    line.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
  const content = [
    "BT",
    "/F1 11 Tf",
    "14 TL",
    "72 760 Td",
    ...lines.filter(Boolean).map((line) => `(${escape(line)}) Tj T*`),
    "ET",
  ].join("\n");
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] " +
      "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
    `<< /Length ${Buffer.byteLength(content, "latin1")} >>\nstream\n${content}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let pdf = "%PDF-1.4\n";
  const offsets: number[] = [];
  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(pdf, "latin1"));
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = Buffer.byteLength(pdf, "latin1");
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets) pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(pdf, "latin1");
}

async function startSetup(page: Parameters<typeof open>[0]) {
  await open(page, "/start");
  await page.getByLabel("Or paste your resume").fill(RESUME);
  await page.getByLabel("What do you want next?").fill("Support lead, remote from the Philippines");
  await page.getByRole("button", { name: "Read my resume" }).click();
  await expect(page.getByText("Keep what is right. Change anything below.")).toBeVisible({
    timeout: 30_000,
  });
}

test.describe("Setup from a resume", () => {
  test("paste, review, apply, and land on the new search", async ({ page }) => {
    await signUp(page, undefined, "Cara Lim");
    await startSetup(page);

    await page.getByRole("textbox", { name: "Notice period" }).fill("30 days");
    await page.getByRole("textbox", { name: "Sponsorship" }).fill("No");
    await page.getByRole("button", { name: "Use these and start searching" }).click();

    await expect(page).toHaveURL(/\/tracks\/[0-9a-f-]+/, { timeout: 30_000 });
    await expect(page.getByText("We filled your pages")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Support Lead");

    await open(page, "/profile");
    await expect(page.getByText("CARA LIM")).toBeVisible();
    await expect(page.getByText("Customer Support Lead")).toBeVisible();

    await open(page, "/profile/answers");
    const noticeRow = page.locator("article", {
      has: page.getByRole("heading", { name: "Notice period" }),
    });
    await expect(noticeRow.getByRole("textbox")).toHaveValue("30 days");
    const sponsorshipRow = page.locator("article", {
      has: page.getByRole("heading", { name: /Sponsorship/ }),
    });
    await expect(sponsorshipRow.getByRole("textbox")).toHaveValue("No");
  });

  test("undo setup keeps the pages but removes what setup added", async ({ page }) => {
    await signUp(page, undefined, "Cara Lim");
    await startSetup(page);
    await page.getByRole("button", { name: "Use these and start searching" }).click();
    await expect(page).toHaveURL(/\/tracks\/[0-9a-f-]+/, { timeout: 30_000 });

    page.on("dialog", (dialog) => dialog.accept());
    await open(page, "/");
    await expect(page.getByText("Setup done")).toBeVisible();
    await page.getByRole("button", { name: "Undo setup" }).click();
    await expect(page.getByText("Setup undone. Your edits are kept.").last()).toBeVisible();
    await expect(page.getByText("Setup done")).toHaveCount(0);
  });

  test("work authorization asks for a country and saves", async ({ page }) => {
    await signUp(page, undefined, "Cara Lim");
    await open(page, "/start");
    await page.getByLabel("Or paste your resume").fill(RESUME_NO_COUNTRY);
    await page.getByRole("button", { name: "Read my resume" }).click();
    await expect(page.getByText("Keep what is right. Change anything below.")).toBeVisible({
      timeout: 30_000,
    });

    const saved = page.waitForResponse(
      (response) =>
        response.url().includes("/decisions") &&
        response.request().method() === "PATCH" &&
        response.status() === 200,
    );
    await page.getByRole("textbox", { name: "Work authorization" }).fill("Filipino citizen");
    await page.getByRole("textbox", { name: "Country" }).fill("PH");
    await page.getByRole("textbox", { name: "Country" }).blur();
    await saved;

    // The answer and the country survive a reload, so the draft really stored them.
    await page.reload();
    await page.waitForSelector("html[data-hydrated]");
    await expect(page.getByRole("textbox", { name: "Work authorization" })).toHaveValue(
      "Filipino citizen",
    );
    await expect(page.getByRole("textbox", { name: "Country" })).toHaveValue("PH");

    await page.getByRole("button", { name: "Use these and start searching" }).click();
    await expect(page).toHaveURL(/\/tracks\/[0-9a-f-]+/, { timeout: 30_000 });

    await open(page, "/profile/answers");
    const authRow = page.locator("article", {
      has: page.getByRole("heading", { name: /Work authorization/ }),
    });
    await expect(authRow.getByRole("textbox")).toHaveValue("Filipino citizen");

    // The same common answers are offered on the answer bank.
    await authRow.getByRole("button", { name: "Yes, I am authorized", exact: true }).click();
    await expect(authRow.getByRole("textbox")).toHaveValue("Yes, I am authorized");
  });

  test("uploads the resume to the profile the setup is created for", async ({ page }) => {
    await signUp(page, undefined, "Cara Lim");
    await open(page, "/start");

    const upload = page.waitForRequest(
      (request) => request.url().includes("/documents") && request.method() === "POST",
    );
    await page.locator('input[type="file"]').setInputFiles({
      name: "cara-lim.pdf",
      mimeType: "application/pdf",
      buffer: makePdf(RESUME_NO_COUNTRY.split("\n")),
    });

    const created = page.waitForRequest(
      (request) =>
        request.url().endsWith("/api/v1/onboarding/setups") && request.method() === "POST",
    );
    await page.getByRole("button", { name: "Read my resume" }).click();

    // The setup must name the profile that received the upload. Without it the API resolves
    // the default profile and answers 404 document_not_found.
    const uploadedTo = new URL((await upload).url()).pathname.split("/")[4];
    const body = (await created).postDataJSON() as {
      document_id?: string;
      profile_id?: string;
    };
    expect(body.document_id).toBeTruthy();
    expect(body.profile_id).toBe(uploadedTo);

    await expect(page.getByText("Keep what is right. Change anything below.")).toBeVisible({
      timeout: 30_000,
    });
  });

  test("common answers fill a question in one tap", async ({ page }) => {
    await signUp(page, undefined, "Cara Lim");
    await startSetup(page);

    await expect(page.getByRole("button", { name: "30 days", exact: true })).toBeVisible();
    const saved = page.waitForResponse(
      (response) =>
        response.url().includes("/decisions") &&
        response.request().method() === "PATCH" &&
        response.status() === 200,
    );
    await page.getByRole("button", { name: "30 days", exact: true }).click();
    await expect(page.getByRole("textbox", { name: "Notice period" })).toHaveValue("30 days");
    await saved;

    await page.getByRole("button", { name: "Not sure yet", exact: true }).click();
    await expect(page.getByRole("textbox", { name: "Sponsorship" })).toHaveValue("Not sure yet");
  });

  test("editing a search opens the sheet", async ({ page }) => {
    await signUp(page, undefined, "Cara Lim");
    await startSetup(page);
    await page.getByRole("button", { name: "Edit" }).first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
    // The sheet clones the proposal; cloning a reactive proxy throws DataCloneError.
    await expect(page.getByText("DataCloneError")).toHaveCount(0);
  });

  test("settings opens setup from a resume", async ({ page }) => {
    await signUp(page);
    await open(page, "/settings/general");
    await page.getByRole("link", { name: "Upload resume" }).click();
    await expect(page).toHaveURL(/\/start/);
    await expect(page.getByRole("heading", { name: "Set up from your resume" })).toBeVisible();
  });
});
