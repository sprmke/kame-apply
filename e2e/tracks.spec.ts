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

  test("several locations widen the search", async ({ page }) => {
    await signUp(page);
    await open(page, "/tracks");
    await page.getByRole("button", { name: "New search" }).click();
    await page.getByLabel("What role are you looking for?").fill("Cook, chef, kitchen");
    await page.getByRole("button", { name: "Create search" }).click();
    await expect(page).toHaveURL(/\/tracks\/[0-9a-f-]+/);
    const id = new URL(page.url()).pathname.split("/")[2];
    await open(page, `/tracks/${id}/look-for`);

    await page.getByRole("textbox", { name: "Location" }).fill("Pampanga");
    await page.getByRole("button", { name: "Add location" }).click();
    await page.getByRole("textbox", { name: "Location" }).nth(1).fill("Manila");
    await page.getByRole("spinbutton", { name: "Radius km" }).nth(1).fill("50");

    const saved = page.waitForResponse(
      (response) => response.url().includes("/criteria") && response.request().method() === "PUT",
    );
    await page.getByRole("button", { name: "Save filters" }).click();
    await saved;

    await page.reload();
    await page.waitForSelector("html[data-hydrated]");
    await expect(page.getByRole("textbox", { name: "Location" })).toHaveCount(2);
    await expect(page.getByRole("textbox", { name: "Location" }).nth(0)).toHaveValue("Pampanga");
    await expect(page.getByRole("textbox", { name: "Location" }).nth(1)).toHaveValue("Manila");
    await expect(page.getByRole("spinbutton", { name: "Radius km" }).nth(1)).toHaveValue("50");
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
