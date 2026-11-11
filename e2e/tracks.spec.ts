import { expect, test } from "@playwright/test";
import { open, signUp } from "./helpers";

test.describe("Phase 4 tracks", () => {
  test("create a track from name and open criteria", async ({ page }) => {
    await signUp(page);
    await open(page, "/tracks");
    await expect(page.getByRole("heading", { name: "Searches" })).toBeVisible();
    await page.getByRole("button", { name: "New search" }).click();
    await page.getByLabel("Name (optional)").fill("AI Engineer");
    await page.getByLabel("What role are you looking for?").fill("AI engineer, remote, Python");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page).toHaveURL(/\/tracks\/[0-9a-f-]+/);
    await expect(page.getByLabel("What role are you looking for?")).toBeVisible();
    await expect(page.getByText("Update this to refine your matches.")).toBeVisible();
    await page.getByRole("button", { name: "More filters" }).click();
    await expect(page.getByText("Work mode")).toBeVisible();
    await page
      .getByRole("navigation", { name: "Track sections" })
      .getByRole("link", { name: "Settings" })
      .click();
    await expect(page).toHaveURL(/\/tracks\/.+\/settings/);
    await expect(page.getByText("Autonomy")).toBeVisible();
  });

  test("duplicate and archive from the list", async ({ page }) => {
    await signUp(page);
    await open(page, "/tracks");
    await page.getByRole("button", { name: "New search" }).click();
    await page.getByLabel("Name (optional)").fill("ICU Nurse");
    await page.getByLabel("What role are you looking for?").fill("ICU nurse night shifts UAE visa");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page).toHaveURL(/\/tracks\/[0-9a-f-]+/);
    await open(page, "/tracks");
    const rows = page.locator("main ul > li");
    await expect(rows).toHaveCount(1);
    await page.getByRole("button", { name: "Duplicate" }).first().click();
    await expect(rows).toHaveCount(2);
    await expect(page.getByText("ICU Nurse copy")).toBeVisible();
    await page.getByRole("button", { name: "Archive" }).first().click();
    await expect(rows).toHaveCount(1);
  });

  test("Today checklist links to tracks", async ({ page }) => {
    await signUp(page);
    await expect(page.getByRole("link", { name: "Start a search" })).toBeVisible();
    await page.getByRole("link", { name: "Start a search" }).click();
    await expect(page).toHaveURL(/\/tracks/);
  });
});
