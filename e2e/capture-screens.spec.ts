import { test } from "@playwright/test";
import { open, signUp } from "./helpers";

// Review screenshots. Run: CAPTURE=1 pnpm exec playwright test e2e/capture-screens.spec.ts
test.skip(!process.env.CAPTURE, "set CAPTURE=1 to regenerate review screenshots");

const PHASE =
  process.env.CAPTURE_PHASE === "12"
    ? "phase-12"
    : process.env.CAPTURE_PHASE === "11"
      ? "phase-11"
      : process.env.CAPTURE_PHASE === "10"
        ? "phase-10"
        : process.env.CAPTURE_PHASE === "09"
          ? "phase-09"
          : process.env.CAPTURE_PHASE === "08"
            ? "phase-08"
            : process.env.CAPTURE_PHASE === "07"
              ? "phase-07"
              : process.env.CAPTURE_PHASE === "06"
                ? "phase-06"
                : process.env.CAPTURE_PHASE === "05"
                  ? "phase-05"
                  : process.env.CAPTURE_PHASE === "04"
                    ? "phase-04"
                    : process.env.CAPTURE_PHASE === "03"
                      ? "phase-03"
                      : "phase-02";

const PHASE_02_ROUTES = [
  ["today", "/"],
  ["settings-members", "/settings/members"],
  ["settings-ai", "/settings/ai"],
  ["settings-profile", "/settings/profile"],
  ["jobs-placeholder", "/jobs"],
] as const;

const PHASE_03_ROUTES = [
  ["profile", "/profile"],
  ["profile-onboarding", "/profile/onboarding"],
  ["profile-answers", "/profile/answers"],
  ["profile-voice", "/profile/voice"],
  ["profile-documents", "/profile/documents"],
] as const;

test(`capture ${PHASE} all viewports`, async ({ page }) => {
  await signUp(page);

  let phaseShots: [string, string][] | null = null;
  if (PHASE === "phase-12") {
    await open(page, "/answers");
    await page
      .locator("#desk-paste")
      .fill(
        "1. What is your notice period? (max 200 characters)\n2. Do you need visa sponsorship?\n3. Please answer without using AI tools. Why this role?\n4. Tell us about a conflict at work.",
      );
    await page.getByRole("button", { name: "Draft" }).click();
    await page.waitForSelector("text=Write this yourself");
    phaseShots = [
      ["answer-desk", "/answers"],
      ["answer-desk-restricted", "/answers"],
      ["profile-answers", "/profile/answers"],
    ];
  } else if (PHASE === "phase-11") {
    await open(page, "/tracks");
    await page.getByRole("button", { name: "New Track" }).click();
    await page.getByLabel("Name").fill("AI Engineer");
    await page.getByLabel("Describe the role").fill("AI engineer remote, Python");
    await page.getByRole("button", { name: "Create" }).click();
    await page.waitForURL(/\/tracks\/[0-9a-f-]+/);
    await open(page, "/applications");
    await page.getByRole("button", { name: "Log application" }).click();
    await page.getByLabel("Company").fill("Acme");
    await page.getByLabel("Title").fill("Staff Engineer");
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await page.waitForURL(/\/applications\/[0-9a-f-]+/);
    const appId = page.url().split("/").pop();
    phaseShots = [
      ["today-home", "/"],
      ["applications-table", "/applications"],
      ["applications-board", "/applications?view=board"],
      ["application-detail", `/applications/${appId}`],
    ];
  } else if (PHASE === "phase-10") {
    await open(page, "/tracks");
    await page.getByRole("button", { name: "New Track" }).click();
    await page.getByLabel("Name").fill("AI Engineer");
    await page.getByLabel("Describe the role").fill("AI engineer remote, Python");
    await page.getByRole("button", { name: "Create" }).click();
    await page.waitForURL(/\/tracks\/[0-9a-f-]+/);
    const trackId = page.url().split("/").pop();
    phaseShots = [
      ["track-settings-schedule", `/tracks/${trackId}/settings`],
      ["track-runs", `/tracks/${trackId}/runs`],
      ["notifications", "/notifications"],
      ["settings-notifications", "/settings/notifications"],
    ];
  } else if (PHASE === "phase-09") {
    await open(page, "/tracks");
    await page.getByRole("button", { name: "New Track" }).click();
    await page.getByLabel("Name").fill("AI Engineer");
    await page.getByLabel("Describe the role").fill("AI engineer remote, Python");
    await page.getByRole("button", { name: "Create" }).click();
    await page.waitForURL(/\/tracks\/[0-9a-f-]+/);
    phaseShots = [
      ["jobs-tailor-action", "/jobs"],
      ["tailor-placeholder", "/tailor/00000000-0000-0000-0000-000000000001"],
      ["studio", "/studio"],
    ];
  } else if (PHASE === "phase-08") {
    await open(page, "/tracks");
    await page.getByRole("button", { name: "New Track" }).click();
    await page.getByLabel("Name").fill("AI Engineer");
    await page.getByLabel("Describe the role").fill("AI engineer remote, Python");
    await page.getByRole("button", { name: "Create" }).click();
    await page.waitForURL(/\/tracks\/[0-9a-f-]+/);
    const trackId = page.url().split("/").pop();
    phaseShots = [
      ["studio-empty", "/studio"],
      ["studio-track", `/studio?track=${trackId}`],
      ["studio-critique", `/studio?track=${trackId}`],
      ["studio-insights", `/studio?track=${trackId}`],
      ["track-settings-resume", `/tracks/${trackId}/settings`],
    ];
  } else if (PHASE === "phase-07") {
    phaseShots = [
      ["safety-flagged", "/safety"],
      ["safety-check", "/safety"],
      ["jobs-risk", "/jobs"],
    ];
  } else if (PHASE === "phase-04" || PHASE === "phase-05" || PHASE === "phase-06") {
    await open(page, "/tracks");
    await page.getByRole("button", { name: "New Track" }).click();
    await page.getByLabel("Name").fill("AI Engineer");
    await page.getByLabel("Describe the role").fill("AI engineer remote, Python");
    await page.getByRole("button", { name: "Create" }).click();
    await page.waitForURL(/\/tracks\/[0-9a-f-]+/);
    const trackUrl = page.url();
    phaseShots =
      PHASE === "phase-06"
        ? [
            ["jobs-board", "/jobs"],
            ["jobs-help", "/jobs"],
            ["track-matched", trackUrl],
            ["tracks-list", "/tracks"],
            ["jobs-empty-track", `/jobs?track=${trackUrl.split("/").pop()}`],
          ]
        : PHASE === "phase-05"
          ? [
              ["track-run", trackUrl],
              ["track-settings-sources", `${trackUrl.replace(/\/$/, "")}/settings`],
              ["settings-sources", "/settings/sources"],
              ["tracks-list", "/tracks"],
              ["track-criteria", trackUrl],
            ]
          : [
              ["tracks-list", "/tracks"],
              ["track-criteria", trackUrl],
              ["track-settings", `${trackUrl.replace(/\/$/, "")}/settings`],
              ["tracks-new", "/tracks"],
              ["track-more-filters", trackUrl],
            ];
  }

  for (const scheme of ["light", "dark"] as const) {
    for (const width of [375, 820, 1440] as const) {
      await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 900 });

      if (PHASE === "phase-02") {
        await open(page, "/login");
        await page.screenshot({
          path: `docs/design/screenshots/phase-02/login-${width}-${scheme}.png`,
        });
      }

      if (
        (PHASE === "phase-04" ||
          PHASE === "phase-05" ||
          PHASE === "phase-06" ||
          PHASE === "phase-07" ||
          PHASE === "phase-08" ||
          PHASE === "phase-09" ||
          PHASE === "phase-10" ||
          PHASE === "phase-11" ||
          PHASE === "phase-12") &&
        phaseShots
      ) {
        for (const [name, path] of phaseShots) {
          await open(page, path);
          if (name === "tracks-new") {
            await page.getByRole("button", { name: "New Track" }).click();
          }
          if (name === "track-more-filters") {
            await page.getByRole("button", { name: "More filters" }).click();
          }
          if (name === "jobs-help") {
            await page.getByRole("button", { name: "Shortcuts" }).click();
          }
          if (name === "safety-check") {
            await page.getByRole("button", { name: "Check this" }).click();
          }
          if (name === "studio-critique") {
            await page
              .getByRole("button", { name: "Critique" })
              .click()
              .catch(() => undefined);
          }
          if (name === "studio-insights") {
            await page
              .getByRole("button", { name: "Insights" })
              .click()
              .catch(() => undefined);
          }
          await page.evaluate(() => document.fonts.ready);
          await page.waitForTimeout(300);
          await page.screenshot({
            path: `docs/design/screenshots/${PHASE}/${name}-${width}-${scheme}.png`,
          });
        }
        continue;
      }

      const routes = PHASE === "phase-03" ? PHASE_03_ROUTES : PHASE_02_ROUTES;
      for (const [name, path] of routes) {
        await open(page, path);
        await page.evaluate(() => document.fonts.ready);
        await page.waitForTimeout(300);
        await page.screenshot({
          path: `docs/design/screenshots/${PHASE}/${name}-${width}-${scheme}.png`,
        });
      }
    }
  }
});
