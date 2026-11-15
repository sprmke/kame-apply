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

  test("settings opens setup from a resume", async ({ page }) => {
    await signUp(page);
    await open(page, "/settings/general");
    await page.getByRole("link", { name: "Upload resume" }).click();
    await expect(page).toHaveURL(/\/start/);
    await expect(page.getByRole("heading", { name: "Set up from your resume" })).toBeVisible();
  });
});
