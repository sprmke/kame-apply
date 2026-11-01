import { expect, test } from "@playwright/test";
import { open, signUp } from "./helpers";

const WIDTHS = [375, 820, 1440] as const;

test.describe("4. shell at 375 / 820 / 1440", () => {
  for (const width of WIDTHS) {
    test(`no horizontal scroll and primary navigation at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await signUp(page);
      for (const path of [
        "/",
        "/settings/general",
        "/settings/members",
        "/settings/ai",
        "/settings/profile",
        "/settings/sessions",
        "/jobs",
      ]) {
        await open(page, path);
        await expect(page.locator("main")).toBeVisible();
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow, `${path} overflows at ${width}px`).toBeLessThanOrEqual(0);
      }
      const nav = page.getByRole("navigation", { name: "Main" });
      await expect(nav.first()).toBeVisible();
      if (width < 768) {
        await expect(nav.getByRole("link", { name: "Today" })).toBeVisible();
        await nav.getByRole("button", { name: "More" }).click();
        await expect(
          page.getByRole("dialog").getByRole("link", { name: "Settings" }),
        ).toBeVisible();
      } else {
        await expect(nav.getByRole("link", { name: "Jobs" })).toBeVisible();
      }
    });
  }

  test("⌘K opens the command bar and navigates by keyboard", async ({ page }) => {
    await signUp(page);
    await page.keyboard.press("Control+k");
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.type("members");
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/settings\/members/);
    await page.keyboard.press("Escape");
  });

  test("keyboard reaches the skip link, rail, and profile menu", async ({ page }) => {
    await signUp(page);
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("main")).toBeFocused();
    await page.getByRole("button", { name: "Account menu" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("menuitem", { name: "Sign out" })).toBeVisible();
    await page.keyboard.press("Escape");
  });

  test("theme can be switched and persists", async ({ page }) => {
    await signUp(page);
    await open(page, "/settings/profile");
    await page.getByLabel("Theme").click();
    await page.getByRole("option", { name: "Dark" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("unknown routes show the 404 page", async ({ page }) => {
    await signUp(page);
    await open(page, "/nope/nothing");
    await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
    await page.getByRole("button", { name: "Back to Today" }).click();
    await expect(page.getByRole("heading", { level: 1, name: /Welcome/ })).toBeVisible();
  });
});
