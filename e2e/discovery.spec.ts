import { expect, test } from "@playwright/test";
import { open, signUp } from "./helpers";

test.describe("Phase 5 discovery", () => {
  test("run now appears on a track and sources settings loads for owner", async ({ page }) => {
    await signUp(page);
    await open(page, "/tracks");
    await page.getByRole("button", { name: "New search" }).click();
    await page.getByLabel("Name (optional)").fill("Software Engineer");
    await page.getByLabel("What role are you looking for?").fill("software engineer remote Python");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page).toHaveURL(/\/tracks\/[0-9a-f-]+/);
    await expect(page.getByRole("button", { name: "Run search" })).toBeVisible();
    await page
      .getByRole("navigation", { name: "Track sections" })
      .getByRole("link", { name: "Settings" })
      .click();
    await expect(page.getByText("Sources", { exact: true }).first()).toBeVisible();
    await open(page, "/settings/sources");
    await expect(page.getByRole("heading", { name: "Source health" })).toBeVisible();
  });
});
