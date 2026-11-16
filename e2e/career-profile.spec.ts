import { expect, test } from "@playwright/test";
import { open, signUp } from "./helpers";

test.describe("Phase 3 career profile", () => {
  test("account menu opens the profile surfaces", async ({ page }) => {
    await signUp(page);
    await open(page, "/");

    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("menuitem", { name: "Profile", exact: true }).click();
    await expect(page).toHaveURL(/\/profile$/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("menuitem", { name: "Answers" }).click();
    await expect(page).toHaveURL(/\/profile\/answers/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("menuitem", { name: "Writing style" }).click();
    await expect(page).toHaveURL(/\/profile\/voice/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("menuitem", { name: "Files" }).click();
    await expect(page).toHaveURL(/\/profile\/documents/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("start reads a pasted resume and shows the review", async ({ page }) => {
    await signUp(page);
    await open(page, "/start");
    await page.getByLabel("Or paste your resume").fill(`ANA REYES
Registered Nurse
Manila, Philippines
ana@example.com

Summary
Registered nurse with 6 years in acute care and ward leadership.

Skills: patient care, triage, mentoring, EMR

Experience
2019 - Present Charge Nurse at St. Luke's Medical Center
Managed a 12-bed ward and mentored new grads.

Education
2013 - 2017 BS Nursing, University of Santo Tomas`);
    await page.getByRole("button", { name: "Read my resume" }).click();
    await expect(page.getByText("Keep what is right. Change anything below.")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByRole("textbox", { name: "Name" })).toHaveValue("ANA REYES");
  });

  test("Today shows one next step", async ({ page }) => {
    await signUp(page);
    await open(page, "/");
    await expect(page.getByText("Next step")).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Add your resume|Start a search|Review/ }).first(),
    ).toBeVisible();
  });
});
