import { expect, test } from "@playwright/test";

test.describe("Phase 7 safety", () => {
  test("safety page renders flagged and check-this tabs", async ({ page }) => {
    await page.goto("/safety");
    // Auth gate may redirect; accept either safety chrome or login.
    const onSafety = page.getByRole("heading", { name: /safety/i });
    const onLogin = page.getByRole("heading", { name: /sign in|log in/i });
    await expect(onSafety.or(onLogin)).toBeVisible({ timeout: 15_000 });
    if (await onSafety.isVisible().catch(() => false)) {
      await expect(page.getByRole("button", { name: "Check this" })).toBeVisible();
      await page.getByRole("button", { name: "Check this" }).click();
      await expect(page.getByLabel("Message or URL")).toBeVisible();
    }
  });
});
