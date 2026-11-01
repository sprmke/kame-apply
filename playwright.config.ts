import { defineConfig, devices } from "@playwright/test";

// Runs against the local stack. `pnpm run dev:docker` must be up (Postgres + Mailpit); the API and
// web servers are started here unless already running.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000, toHaveScreenshot: { maxDiffPixelRatio: 0.02 } },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:3100", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "cd apps/api && uv run uvicorn app.main:app --port 8100",
      url: "http://localhost:8100/healthz",
      reuseExistingServer: true,
      timeout: 60_000,
      env: { AUTH_RATE_LIMIT_ENABLED: "false" },
    },
    {
      command: "cd apps/web && NUXT_PUBLIC_ENABLE_DESIGN=true pnpm exec nuxt dev --port 3100",
      url: "http://localhost:3100/login",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
