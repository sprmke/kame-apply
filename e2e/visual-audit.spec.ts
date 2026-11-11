import { expect, test } from "@playwright/test";
import { open, signUp } from "./helpers";

/**
 * Visual audit harness. Not a pixel snapshot test: it captures the real app at three widths and
 * fails only on horizontal overflow. Open the screenshots under test-results/visual-audit-* when
 * changing layout, spacing, type, or component styling.
 */
const WIDTHS = [375, 820, 1440] as const;

async function capture(
  page: import("@playwright/test").Page,
  testInfo: import("@playwright/test").TestInfo,
  routes: Array<[string, string]>,
) {
  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: 900 });
    for (const [name, path] of routes) {
      await open(page, path);
      await page.waitForTimeout(350);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, `${path} overflows at ${width}px`).toBeLessThanOrEqual(0);
      await page.screenshot({
        path: testInfo.outputPath(`${width}-${name}.png`),
        fullPage: true,
      });
    }
  }
}

test.describe("visual audit", () => {
  test("core job-search routes at 375, 820, and 1440", async ({ page }, testInfo) => {
    test.setTimeout(120_000);
    await signUp(page);
    await capture(page, testInfo, [
      ["today", "/"],
      ["searches", "/tracks"],
      ["jobs", "/jobs"],
      ["applications", "/applications"],
      ["profile", "/profile"],
    ]);
  });

  test("settings and supporting routes at 375, 820, and 1440", async ({ page }, testInfo) => {
    test.setTimeout(120_000);
    await signUp(page);
    await capture(page, testInfo, [
      ["settings", "/settings"],
      ["ai", "/settings/ai"],
      ["integrations", "/settings/integrations"],
      ["answers", "/answers"],
      ["safety", "/safety"],
    ]);
  });
});
