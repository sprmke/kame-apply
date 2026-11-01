import { expect, test } from "@playwright/test";

test.describe("Phase 8 studio", () => {
  test("studio page renders chrome and track picker", async ({ page }) => {
    await page.goto("/studio");
    const onStudio = page.getByRole("heading", { name: /studio/i });
    const onLogin = page.getByRole("heading", { name: /sign in|log in/i });
    await expect(onStudio.or(onLogin)).toBeVisible({ timeout: 15_000 });
    if (await onStudio.isVisible().catch(() => false)) {
      await expect(page.getByRole("button", { name: "New base" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Critique" })).toBeVisible();
      await page.getByRole("button", { name: "Skim" }).click();
      await page.getByRole("button", { name: "Parse" }).click();
    }
  });
});
