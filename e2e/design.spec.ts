import { expect, test } from "@playwright/test";
import { open } from "./helpers";

// Visual regression for the living style guide. Update with: pnpm exec playwright test e2e/design.spec.ts --update-snapshots
for (const scheme of ["light", "dark"] as const) {
  for (const width of [375, 820, 1440] as const) {
    test(`/_design ${scheme} ${width}px`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 900 });
      await open(page, "/_design");
      await page.evaluate(() => document.fonts.ready);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);
      await expect(page).toHaveScreenshot(`design-${scheme}-${width}.png`, {
        fullPage: true,
        animations: "disabled",
      });
    });
  }
}

test("overlays open, trap focus, and close on Escape", async ({ page }) => {
  await open(page, "/_design");
  await page.getByRole("button", { name: "Dialog", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Close" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Dialog", exact: true })).toBeFocused();

  await page.getByRole("button", { name: "Toast" }).click();
  await expect(page.getByText("Your change is live", { exact: true })).toBeVisible();
});

test("pencil text turns to ink when accepted", async ({ page }) => {
  await open(page, "/_design");
  await expect(page.getByText("cut deploy time by half")).toHaveClass(/text-pencil/);
  await page.getByRole("button", { name: "Accept" }).click();
  await expect(page.getByText("cut deploy time by half")).toHaveClass(/text-ink-900/);
});

// WCAG 2.5.8 / design-system §12: touch targets are at least 44px on phones. Inline links inside
// running text are exempt, as is the visually hidden skip link.
test("interactive controls are at least 44px tall at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await open(page, "/_design");
  const small = await page.evaluate(() => {
    const sel =
      'button, a[href], [role="tab"], [role="combobox"], input:not([type="hidden"]), textarea';
    return [...document.querySelectorAll<HTMLElement>(sel)]
      .filter((el) => el.offsetParent !== null && !el.closest("p") && !el.closest("label"))
      .map((el) => ({
        name: (el.getAttribute("aria-label") || el.textContent || el.tagName).trim().slice(0, 30),
        h: Math.round(el.getBoundingClientRect().height),
      }))
      .filter((x) => x.h < 44);
  });
  expect(small).toEqual([]);
});
