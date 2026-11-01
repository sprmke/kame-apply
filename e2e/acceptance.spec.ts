import { expect, test } from "@playwright/test";
import {
  devGeminiKey,
  latestMail,
  open,
  PASSWORD,
  signIn,
  signUp,
  uniqueEmail,
  verifyEmail,
} from "./helpers";

test.describe("Phase 2 acceptance", () => {
  test("1. sign up lands in a personal workspace with the onboarding checklist", async ({
    page,
  }) => {
    await signUp(page);
    await expect(page.getByRole("button", { name: "Switch workspace" })).toContainText("Personal");
    await expect(page.getByRole("heading", { name: "Get set up" })).toBeVisible();
    await expect(page.getByText("Add an AI key")).toBeVisible();
    // Reload keeps the session through the refresh cookie.
    await page.reload();
    await expect(page.getByRole("heading", { level: 1, name: /Welcome/ })).toBeVisible();
  });

  test("login, wrong password, and sign out", async ({ page }) => {
    const email = await signUp(page);
    await page.getByRole("button", { name: "Account menu" }).click();
    await page.getByRole("menuitem", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login/);
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("not the password");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toContainText("Email or password is incorrect");
    await signIn(page, email);
  });

  test("signed-out visitors are sent to login and back", async ({ page }) => {
    await open(page, "/settings/members");
    await expect(page).toHaveURL(/\/login\?next=(%2F|\/)settings(%2F|\/)members/);
    await page.getByRole("link", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/register\?next=/);
    await page.getByLabel("Email").fill(uniqueEmail());
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/settings\/members/);
  });

  test("form validation is translated and accessible", async ({ page }) => {
    await open(page, "/register");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByLabel("Email")).toHaveAttribute("aria-invalid", "true");
    await expect(page.getByText("Required").first()).toBeVisible();
    await page.getByLabel("Email").fill("not-an-email");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Enter a valid email")).toBeVisible();
    await page.getByLabel("Password").fill("short");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Use at least 10 characters")).toBeVisible();
  });

  test("email verification link works from the Mailpit message", async ({ page }) => {
    const email = await signUp(page);
    await expect(page.getByText(`Confirm ${email}`)).toBeVisible();
    const body = await latestMail("Verify your email", email);
    const link = body.match(/http:\/\/localhost:3100\/verify-email\?token=[\w-]+/)![0];
    await open(page, link);
    await expect(page.getByText("Email confirmed.")).toBeVisible();
    await page.getByRole("link", { name: "Continue" }).click();
    await expect(page.getByText(`Confirm ${email}`)).toHaveCount(0);
  });

  test("password reset ends the old session", async ({ page, browser }) => {
    const email = await signUp(page);
    const other = await (await browser.newContext()).newPage();
    await open(other, "/forgot-password");
    await other.getByLabel("Email").fill(email);
    await other.getByRole("button", { name: "Send link" }).click();
    await expect(other.getByText("a reset link is on its way")).toBeVisible();
    const body = await latestMail("Reset your password", email);
    await open(other, body.match(/http:\/\/localhost:3100\/reset-password\?token=[\w-]+/)![0]);
    await other.getByLabel("New password").fill("a brand new passphrase");
    await other.getByRole("button", { name: "Set password" }).click();
    await expect(other).toHaveURL(/\/login/);
    await other.getByLabel("Email").fill(email);
    await other.getByLabel("Password").fill("a brand new passphrase");
    await other.getByRole("button", { name: "Sign in" }).click();
    await expect(other.getByRole("heading", { level: 1, name: /Welcome/ })).toBeVisible();
    // The first browser's session was revoked by the reset.
    await open(page, "/settings/sessions");
    await expect(page).toHaveURL(/\/login/);
  });

  test("3. owner adds a Gemini key, sets a $5 budget, usage shows $0.00", async ({ page }) => {
    await signUp(page);
    await page.getByRole("link", { name: "Add an AI key" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "AI providers" })).toBeVisible();
    await expect(page.getByText("$0.00 of $5.00 this month")).toBeVisible();

    await page.getByRole("button", { name: "Add key" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("API key").fill(devGeminiKey() ?? "not-a-real-key-123");
    await dialog.getByRole("button", { name: "Save and test" }).click();
    if (devGeminiKey()) {
      await expect(page.getByText("Key works").first()).toBeVisible({ timeout: 30_000 });
      await expect(page.getByRole("row", { name: /Google Gemini/ })).toContainText("Valid");
    } else {
      await expect(page.getByText("The provider rejected this key")).toBeVisible({
        timeout: 30_000,
      });
    }
    // The key is masked everywhere.
    await expect(page.getByRole("row", { name: /Google Gemini/ })).toContainText("••••");

    await page.getByLabel("Budget (USD)").fill("7.50");
    await page.getByRole("button", { name: "Save" }).first().click();
    await expect(page.getByText("Saved").first()).toBeVisible();
    await expect(page.getByText(/of \$7\.50 this month/)).toBeVisible();
    await page.getByRole("button", { name: "Show table" }).click();
  });

  test("invite a member who joins and appears with the right role", async ({ page, browser }) => {
    await verifyEmail(page, await signUp(page));
    await page.getByRole("button", { name: "Switch workspace" }).click();
    await page.getByRole("menuitem", { name: "New workspace" }).click();
    await page.getByRole("dialog").getByLabel("Name").fill("Crew");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.getByRole("button", { name: "Switch workspace" })).toContainText("Crew");

    await open(page, "/settings/members");
    const guestEmail = uniqueEmail("guest");
    await page.getByRole("button", { name: "Invite member" }).click();
    await page.getByRole("dialog").getByLabel("Email").fill(guestEmail);
    await page.getByRole("button", { name: "Send invite" }).click();
    await expect(page.getByText("Invite sent").first()).toBeVisible();
    await expect(page.getByText("Pending invites")).toBeVisible();

    const guest = await (await browser.newContext()).newPage();
    await signUp(guest, guestEmail, "Gus Guest");
    await verifyEmail(guest, guestEmail);
    const mail = await latestMail("You are invited", guestEmail);
    await open(guest, mail.match(/http:\/\/localhost:3100\/invite\?token=[\w-]+/)![0]);
    await guest.getByRole("button", { name: "Join workspace" }).click();
    await expect(guest.getByRole("button", { name: "Switch workspace" })).toContainText("Crew");

    await page.reload();
    await expect(page.getByRole("row", { name: /Gus Guest/ })).toContainText("Member");
    await expect(page.getByText("2 of 10 seats used")).toBeVisible();
  });

  test("members cannot see manager-only controls", async ({ page, browser }) => {
    await verifyEmail(page, await signUp(page));
    await page.getByRole("button", { name: "Switch workspace" }).click();
    await page.getByRole("menuitem", { name: "New workspace" }).click();
    await page.getByRole("dialog").getByLabel("Name").fill("Locked");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.getByRole("button", { name: "Switch workspace" })).toContainText("Locked");
    await open(page, "/settings/members");
    const email = uniqueEmail("viewer");
    await page.getByRole("button", { name: "Invite member" }).click();
    await page.getByRole("dialog").getByLabel("Email").fill(email);
    await page.getByRole("dialog").getByLabel("Role").click();
    await page.getByRole("option", { name: "Viewer" }).click();
    await page.getByRole("button", { name: "Send invite" }).click();
    const v = await (await browser.newContext()).newPage();
    await signUp(v, email);
    await verifyEmail(v, email);
    await open(
      v,
      (await latestMail("You are invited", email)).match(
        /http:\/\/localhost:3100\/invite\?token=[\w-]+/,
      )![0],
    );
    await v.getByRole("button", { name: "Join workspace" }).click();
    await expect(v.getByRole("button", { name: "Switch workspace" })).toContainText("Locked");
    await open(v, "/settings/members");
    await expect(v.getByRole("button", { name: "Invite member" })).toHaveCount(0);
    await open(v, "/settings/ai");
    await expect(v.getByText("Owners and admins manage keys and budget.")).toBeVisible();
    await expect(v.getByRole("button", { name: "Add key" })).toHaveCount(0);
  });

  test("sessions page lists this device and revokes others", async ({ page, browser }) => {
    const email = await signUp(page);
    const second = await (await browser.newContext()).newPage();
    await signIn(second, email);
    await open(page, "/settings/sessions");
    await expect(page.getByText("This device")).toHaveCount(1);
    await page.getByRole("button", { name: "Sign out" }).first().click();
    await expect(page.getByText("Device signed out")).toBeVisible();
    await open(second, "/settings/profile");
    await expect(second).toHaveURL(/\/login/);
  });

  test("workspace switching never shows another workspace's data", async ({ page }) => {
    await signUp(page);
    await page.getByRole("button", { name: "Switch workspace" }).click();
    await page.getByRole("menuitem", { name: "New workspace" }).click();
    await page.getByRole("dialog").getByLabel("Name").fill("Second");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.getByRole("button", { name: "Switch workspace" })).toContainText("Second");
    await open(page, "/settings/members");
    await expect(page.getByText("1 of 10 seats used")).toBeVisible();
    await page.getByRole("button", { name: "Switch workspace" }).click();
    await page.getByRole("menuitem", { name: /Personal/ }).click();
    await open(page, "/settings/general");
    await expect(page.getByLabel("Name")).toHaveValue("Personal");
  });
});
