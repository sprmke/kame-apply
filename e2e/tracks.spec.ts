import { expect, test } from "@playwright/test";
import { open, signUp } from "./helpers";

test.describe("Phase 4 tracks", () => {
  test("create a search from a description", async ({ page }) => {
    await signUp(page);
    await open(page, "/tracks");
    await expect(page.getByRole("heading", { name: "Searches" })).toBeVisible();
    await page.getByRole("button", { name: "New search" }).click();
    await page.getByLabel("What role are you looking for?").fill("AI engineer, remote, Python");
    await page.getByRole("button", { name: "Create search" }).click();
    await expect(page).toHaveURL(/\/tracks\/[0-9a-f-]+/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("duplicate and archive from the list", async ({ page }) => {
    await signUp(page);
    await open(page, "/tracks");
    await page.getByRole("button", { name: "New search" }).click();
    await page.getByLabel("What role are you looking for?").fill("ICU nurse night shifts UAE visa");
    await page.getByRole("button", { name: "Create search" }).click();
    await expect(page).toHaveURL(/\/tracks\/[0-9a-f-]+/);

    await open(page, "/tracks");
    const original = page.getByRole("link", { name: "ICU nurse night shifts UAE visa" });
    await expect(original).toBeVisible();
    await page.getByRole("button", { name: "Duplicate" }).first().click();
    await expect(
      page.getByRole("heading", { level: 1, name: "ICU nurse night shifts UAE visa copy" }),
    ).toBeVisible();
    await open(page, "/tracks");
    await expect(page.getByText("ICU nurse night shifts UAE visa copy")).toBeVisible();
    await page.getByRole("button", { name: "Archive" }).last().click();
    await expect(page.getByText("ICU nurse night shifts UAE visa copy")).toHaveCount(0);
  });

  test("Today next step reaches a search", async ({ page }) => {
    await signUp(page);
    await open(page, "/");
    await expect(page.getByText("Next step")).toBeVisible();
    const skip = page.getByRole("link", { name: "Skip to content" });
    await expect(skip).toBeAttached();
    await page.goto("/tracks");
    await expect(page.getByRole("heading", { name: "Searches" })).toBeVisible();
  });
});
