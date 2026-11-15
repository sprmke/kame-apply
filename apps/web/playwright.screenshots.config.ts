import { defineConfig, devices } from "@playwright/test";

// UX clarity baseline and preview captures. Run through `pnpm run capture:design-screenshots`
// from the repo root; that script sets CAPTURE_DESIGN_SCREENSHOTS and points at the local app.
// The dev stack must be up (`pnpm run dev` or `dev:docker` + `dev:api` + `dev:web`).
export default defineConfig({
  testDir: "../../e2e",
  testMatch: /ux-screens\.spec\.ts/,
  timeout: 180_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.DESIGN_SCREENSHOT_BASE_URL ?? "http://localhost:3100",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
