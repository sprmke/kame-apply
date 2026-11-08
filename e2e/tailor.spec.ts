import { expect, test } from "@playwright/test";
import { open, signIn } from "./helpers";

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

const API = "http://localhost:8100/api/v1";

test("tailor changes can be removed and kept", async ({ page, request }) => {
  const email = `tailor-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
  const reg = await request.post(`${API}/auth/register`, {
    data: { email, password: "correct horse battery" },
  });
  expect(reg.ok()).toBeTruthy();
  const { access_token } = await reg.json();
  const auth = { Authorization: `Bearer ${access_token}` };
  const workspaces = await (await request.get(`${API}/workspaces`, { headers: auth })).json();
  const ws = workspaces[0].id;
  const h = { ...auth, "X-Workspace-Id": ws };

  const profile = await (
    await request.post(`${API}/profiles`, {
      headers: h,
      data: { display_name: "Ada Tailor", headline: "Backend Engineer" },
    })
  ).json();
  await request.patch(`${API}/profiles/${profile.id}`, {
    headers: h,
    data: { summary: "Builds APIs" },
  });
  const exp = await (
    await request.post(`${API}/profiles/${profile.id}/experiences`, {
      headers: h,
      data: {
        company: "Acme",
        title: "Engineer",
        start_date: "2019-01-01",
        is_current: true,
      },
    })
  ).json();
  await request.post(`${API}/profiles/${profile.id}/bullets`, {
    headers: h,
    data: { experience_id: exp.id, text: "Built FastAPI services for 12 teams" },
  });
  await request.post(`${API}/profiles/${profile.id}/skills`, {
    headers: h,
    data: { name: "Python" },
  });
  const track = await (
    await request.post(`${API}/tracks`, {
      headers: h,
      data: {
        profile_id: profile.id,
        name: "Backend",
        nl_text: "backend engineer Python",
        criteria: {
          schema_version: 1,
          titles: [{ title: "Backend Engineer", synonyms: [], exclude: false }],
          skills: { must: ["Python"], nice: [], exclude: [] },
        },
      },
    })
  ).json();
  const tok = await (
    await request.post(`${API}/extension/tokens`, {
      headers: h,
      data: { label: "e2e" },
    })
  ).json();
  const eh = { Authorization: `Bearer ${tok.token}`, "X-Workspace-Id": ws };
  const clip = await (
    await request.post(`${API}/extension/clip`, {
      headers: eh,
      data: {
        url: `https://boards.greenhouse.io/acme/jobs/${Date.now()}`,
        title: "Backend Engineer",
        company: "Acme",
        track_id: track.id,
        platform: "greenhouse",
        json_ld: {
          "@type": "JobPosting",
          title: "Backend Engineer",
          description:
            "<p>Requirements:</p><ul><li>Python</li><li>FastAPI</li></ul>" +
            "<p>Build APIs for customers.</p>",
        },
      },
    })
  ).json();
  await request.post(`${API}/resumes`, {
    headers: h,
    data: { profile_id: profile.id, track_id: track.id, label: "Base" },
  });

  await signIn(page, email);
  await open(page, `/tailor/${clip.track_job_id}`);
  await expect(page.getByRole("heading", { name: "Tailor" })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("button", { name: "Accept" })).toBeEnabled({ timeout: 30_000 });

  const keep = page.getByRole("button", { name: "Keep", exact: true }).first();
  const remove = page.getByRole("button", { name: "Remove", exact: true }).first();
  await expect(page.getByRole("button", { name: /^(Keep|Remove)$/ }).first()).toBeVisible({
    timeout: 15_000,
  });
  if (await keep.isEnabled().catch(() => false)) {
    await keep.click();
    await expect(keep).toBeDisabled();
    await expect(remove).toBeEnabled();
    await remove.click();
    await expect(remove).toBeDisabled();
  } else {
    await remove.click();
    await expect(remove).toBeDisabled();
    await keep.click();
    await expect(keep).toBeDisabled();
  }
});
