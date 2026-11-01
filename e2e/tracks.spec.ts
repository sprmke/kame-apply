import { expect, test } from "@playwright/test";
import { open, signUp } from "./helpers";

test.describe("Phase 4 tracks", () => {
  test("create a track from name and open criteria", async ({ page }) => {
    await signUp(page);
    await open(page, "/tracks");
    await expect(page.getByRole("heading", { name: "Tracks" })).toBeVisible();
    await page.getByRole("button", { name: "New Track" }).click();
    await page.getByLabel("Name").fill("AI Engineer");
    await page.getByLabel("Describe the role").fill("AI engineer, remote, Python");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page).toHaveURL(/\/tracks\/[0-9a-f-]+/);
    await expect(page.getByLabel("Describe the role")).toBeVisible();
    await expect(page.getByText("Preview available after first discovery")).toBeVisible();
    await page.getByRole("button", { name: "More filters" }).click();
    await expect(page.getByText("Work mode")).toBeVisible();
    await page.locator("main").getByRole("link", { name: "Settings" }).first().click();
    await expect(page).toHaveURL(/\/tracks\/.+\/settings/);
    await expect(page.getByText("Autonomy")).toBeVisible();
  });

  test("duplicate and archive from the list", async ({ page }) => {
    await signUp(page);
    await open(page, "/tracks");
    await page.getByRole("button", { name: "New Track" }).click();
    await page.getByLabel("Name").fill("ICU Nurse");
    await page.getByLabel("Describe the role").fill("ICU nurse night shifts UAE visa");
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
    await expect(page.getByRole("link", { name: "Create a Track" })).toBeVisible();
    await page.getByRole("link", { name: "Create a Track" }).click();
    await expect(page).toHaveURL(/\/tracks/);
  });
});
