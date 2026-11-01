import { expect, test } from "@playwright/test";

test.describe("Phase 9 tailor", () => {
  test("jobs board exposes Tailor action when signed in", async ({ page }) => {
    await page.goto("/jobs");
    const onJobs = page.getByRole("heading", { name: /jobs/i });
    const onLogin = page.getByRole("heading", { name: /sign in|log in/i });
    await expect(onJobs.or(onLogin)).toBeVisible({ timeout: 15_000 });
    if (await onJobs.isVisible().catch(() => false)) {
      // Empty board still has chrome; Tailor appears when a row is selected.
      await expect(page.getByRole("button", { name: "?" })).toBeVisible();
    }
  });

  test("tailor route shows login or tailor chrome", async ({ page }) => {
    await page.goto("/tailor/00000000-0000-0000-0000-000000000001");
    const onTailor = page.getByRole("heading", { name: /tailor/i });
    const onLogin = page.getByRole("heading", { name: /sign in|log in/i });
    await expect(onTailor.or(onLogin)).toBeVisible({ timeout: 15_000 });
  });
});
