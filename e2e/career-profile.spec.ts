import { expect, test } from "@playwright/test";
import { open, signUp } from "./helpers";

test.describe("Phase 3 career profile", () => {
  test("profile menu opens career surfaces and onboarding upload", async ({ page }) => {
    await signUp(page);
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("menuitem", { name: "Career Profile" }).click();
    await expect(page).toHaveURL(/\/profile/);
    await expect(page.getByRole("heading", { name: "Career Profile" })).toBeVisible();

    await page.getByRole("link", { name: "Answer bank" }).click();
    await expect(page).toHaveURL(/\/profile\/answers/);
    await expect(page.getByRole("button", { name: "Quick setup" })).toBeVisible();

    await page.getByRole("link", { name: "Voice" }).click();
    await expect(page).toHaveURL(/\/profile\/voice/);
    await expect(page.getByRole("button", { name: "Analyze" })).toBeVisible();

    await page.getByRole("link", { name: "Documents" }).click();
    await expect(page).toHaveURL(/\/profile\/documents/);

    await open(page, "/profile/onboarding");
    await expect(page.getByRole("heading", { name: "Your profile" })).toBeVisible();
    await page
      .getByLabel("Or paste resume text")
      .fill(
        "Ana Reyes\nRegistered Nurse\nSt. Luke's Medical Center\n2019-03 – Present\nManaged a 12-bed ward and mentored new grads.",
      );
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page).toHaveURL(/\/profile\/review\//);
    await expect(page.getByRole("heading", { name: "Parse review" })).toBeVisible();
  });

  test("Today checklist links to profile onboarding", async ({ page }) => {
    await signUp(page);
    await expect(page.getByRole("link", { name: "Add your resume" })).toBeVisible();
    await page.getByRole("link", { name: "Add your resume" }).click();
    await expect(page).toHaveURL(/\/profile\/onboarding/);
  });
});
