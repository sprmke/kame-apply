import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, type Page } from "@playwright/test";

export const PASSWORD = "correct horse battery";
export const uniqueEmail = (tag = "e2e") =>
  `${tag}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;

/** Navigate and wait until Vue has hydrated (forms would otherwise submit natively). */
export async function open(page: Page, path: string) {
  await page.goto(path);
  await page.waitForSelector("html[data-hydrated]");
}

export async function signUp(page: Page, email = uniqueEmail(), name = "Mika Tester") {
  await open(page, "/register");
  await page.getByLabel("Name").fill(name);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { level: 1, name: /Welcome/ })).toBeVisible();
  return email;
}

/** Opens the emailed confirmation link in a throwaway tab of the same context. */
export async function verifyEmail(page: Page, email: string) {
  const body = await latestMail("Verify your email", email);
  const link = body.match(/http:\/\/localhost:3100\/verify-email\?token=[\w-]+/)![0];
  const tab = await page.context().newPage();
  await open(tab, link);
  await expect(tab.getByText("Email confirmed.")).toBeVisible();
  await tab.close();
  await page.reload();
  await page.waitForSelector("html[data-hydrated]");
}

export async function signIn(page: Page, email: string) {
  await open(page, "/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { level: 1, name: /Welcome/ })).toBeVisible();
}

/** Local dev Gemini key from apps/api/.env (gitignored); undefined in CI. */
export function devGeminiKey(): string | undefined {
  try {
    const env = readFileSync(join(__dirname, "../apps/api/.env"), "utf8");
    return (
      env
        .match(/^GEMINI_API_KEYS=(.+)$/m)?.[1]
        ?.split(",")[0]
        ?.trim() || undefined
    );
  } catch {
    return undefined;
  }
}

export async function latestMail(subject: string, to: string): Promise<string> {
  for (let i = 0; i < 20; i++) {
    const list = (await (await fetch("http://localhost:8125/api/v1/messages")).json()) as {
      messages: { ID: string; Subject: string; To: { Address: string }[] }[];
    };
    const hit = list.messages.find(
      (m) => m.Subject.startsWith(subject) && m.To.some((t) => t.Address === to.toLowerCase()),
    );
    if (hit)
      return (
        (await (await fetch(`http://localhost:8125/api/v1/message/${hit.ID}`)).json()) as {
          Text: string;
        }
      ).Text;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`no mail "${subject}" for ${to}`);
}
