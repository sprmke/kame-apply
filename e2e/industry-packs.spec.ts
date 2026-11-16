import { expect, test } from "@playwright/test";
import { open, signUp } from "./helpers";

test.describe("Industry packs", () => {
  test("creating a workspace asks for the name, the field, then an optional resume", async ({
    page,
  }) => {
    await signUp(page);
    await open(page, "/");
    await page.getByRole("button", { name: "Switch workspace" }).click();
    await page.getByRole("menuitem", { name: /New workspace|Create/ }).click();

    await expect(page.getByText("Step 1 of 3")).toBeVisible();
    await page.getByLabel("Name").fill("Kitchen team");
    await page.getByRole("button", { name: "Next" }).click();

    await expect(page.getByText("Step 2 of 3")).toBeVisible();
    await expect(page.getByText("What kind of work?")).toBeVisible();
    await page.getByRole("button", { name: /Hospitality and food/ }).click();
    await page.getByRole("button", { name: "Next" }).click();

    await expect(page.getByText("Step 3 of 3")).toBeVisible();
    await expect(page.getByText("Start from a resume")).toBeVisible();
    await page.getByRole("button", { name: "Create workspace" }).click();

    await expect(page.getByRole("button", { name: "Switch workspace" })).toContainText(
      "Kitchen team",
    );
  });

  test("settings shows the workspace fields of work", async ({ page }) => {
    await signUp(page);
    await open(page, "/settings/general");
    await expect(page.getByText("Fields of work")).toBeVisible();
    await expect(page.getByText("Technology and software")).toBeVisible();
    await expect(page.getByText("Hospitality and food")).toBeVisible();
  });

  test("making hospitality primary says what changes in searches", async ({ page }) => {
    await signUp(page);
    await open(page, "/settings/general");
    await page.getByRole("button", { name: "Hospitality and food" }).click();
    await page.getByRole("button", { name: "Make primary" }).click();
    await expect(page.getByText(/Shift filters appear in searches/)).toBeVisible();
    await page.getByRole("button", { name: "Confirm" }).click();
    await expect(page.getByText("Primary", { exact: true }).first()).toBeVisible({
      timeout: 20_000,
    });
  });
});
