import { test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { open, signUp, uniqueEmail } from "./helpers";

// Baseline "before/after" capture for the UX clarity program.
// Run: pnpm run capture:design-screenshots
// Output: .audit-screenshots/harness/<route>-<width>-<theme>.png (gitignored)
test.skip(!process.env.CAPTURE_DESIGN_SCREENSHOTS, "set CAPTURE_DESIGN_SCREENSHOTS=1");

const OUT = join(__dirname, "../../.audit-screenshots/harness");

const PUBLIC = [
  ["login", "/login"],
  ["register", "/register"],
] as const;

const APP = [
  ["today", "/"],
  ["tracks", "/tracks"],
  ["jobs", "/jobs"],
  ["applications", "/applications"],
  ["profile", "/profile"],
  ["answers", "/answers"],
  ["studio", "/studio"],
  ["responses", "/responses"],
  ["contacts", "/contacts"],
  ["safety", "/safety"],
  ["notifications", "/notifications"],
  ["settings", "/settings"],
  ["settings-ai", "/settings/ai"],
  ["settings-integrations", "/settings/integrations"],
  ["settings-notifications", "/settings/notifications"],
  ["settings-general", "/settings/general"],
  ["design", "/_design"],
  ["start", "/start"],
] as const;

test("baseline captures at 375, 820, 1440 in both themes", async ({ page }) => {
  mkdirSync(OUT, { recursive: true });
  const email = await signUp(page, uniqueEmail("ux-baseline"));

  // One search so list and detail pages have real content.
  await open(page, "/tracks");
  await page.getByRole("button", { name: "New search" }).click();
  await page.getByLabel("What role are you looking for?").fill("Customer support lead, remote");
  await page.getByRole("button", { name: "Create search", exact: true }).click();
  await page.waitForURL(/\/tracks\/[0-9a-f-]+/);
  const trackId = page.url().split("/").pop()!;

  const appRoutes = [
    ...APP,
    ["track", `/tracks/${trackId}`],
    ["track-automation", `/tracks/${trackId}/settings`],
    ["track-history", `/tracks/${trackId}/runs`],
  ] as const;

  for (const scheme of ["light", "dark"] as const) {
    for (const width of [375, 820, 1440] as const) {
      await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 900 });

      if (width === 375) {
        for (const [name, path] of PUBLIC) {
          await open(page, path);
          await page.evaluate(() => document.fonts.ready);
          await page.screenshot({ path: join(OUT, `${name}-${width}-${scheme}.png`) });
        }
      }

      for (const [name, path] of appRoutes) {
        await open(page, path);
        await page.evaluate(() => document.fonts.ready);
        await page.waitForTimeout(250);
        await page.screenshot({ path: join(OUT, `${name}-${width}-${scheme}.png`) });
      }
    }
  }

  // eslint-disable-next-line no-console
  console.log(`captures written for ${email} (search ${trackId})`);
});
