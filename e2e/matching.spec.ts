import { expect, test } from "@playwright/test";
import { open, signUp } from "./helpers";

test.describe("Phase 6 matching board", () => {
  test("jobs page loads and shows shortcuts help", async ({ page }) => {
    await signUp(page);
    await open(page, "/jobs");
    await expect(page.getByRole("heading", { name: "Jobs" })).toBeVisible();
    await page.getByRole("button", { name: "Shortcuts" }).click();
    await expect(page.getByText("j/k move")).toBeVisible();
    await expect(page.getByRole("button", { name: "CSV" })).toBeVisible();
  });
});
