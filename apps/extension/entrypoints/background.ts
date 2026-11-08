import { apiFetch, isAllowedApiBase, looksLikeExtensionToken } from "../utils/api";
import { clearSession, getSession, setSession, type ExtSession } from "../utils/storage";
import { detectPlatform } from "../utils/platforms";
import { initExtensionSentry } from "./background/sentry";

initExtensionSentry();

type ConnectMsg = {
  type: "kame.connect";
  token: string;
  workspaceId: string;
  apiBase: string;
  trackId?: string;
  profileId?: string;
};

async function ensureContent(tabId: number, url?: string) {
  if (!url || url.startsWith("chrome://") || url.startsWith("about:")) {
    throw new Error("Open a job page first");
  }
  try {
    const origin = new URL(url).origin + "/*";
    const have = await browser.permissions.contains({ origins: [origin] });
    if (!have) {
      const granted = await browser.permissions.request({ origins: [origin] });
      if (!granted) throw new Error("Site permission denied");
    }
  } catch {
    // optional_host_permissions may cover it; fall through to scripting
  }
  // Unlisted script (page-bridge.ts): not declared as content_scripts, so no required host_permissions.
  await browser.scripting.executeScript({
    target: { tabId, allFrames: true },
    files: ["/page-bridge.js"],
  });
}

async function activeTab() {
  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  const tab = tabs[0];
  if (!tab?.id) throw new Error("No active tab");
  return tab;
}

export default defineBackground(() => {
  browser.sidePanel?.setPanelBehavior?.({ openPanelOnActionClick: true }).catch(() => {});

  browser.runtime.onMessage.addListener((msg) => {
    if (!msg || typeof msg !== "object") return;
    const type = (msg as { type?: string }).type;

    if (type === "kame.getSession") {
      return getSession();
    }
    if (type === "kame.clearSession") {
      return clearSession().then(() => ({ ok: true }));
    }
    if (type === "kame.setPrefs") {
      return getSession().then(async (s) => {
        if (!s) return null;
        const next = {
          ...s,
          trackId: (msg as { trackId?: string }).trackId ?? s.trackId,
          profileId: (msg as { profileId?: string }).profileId ?? s.profileId,
        };
        await setSession(next);
        return next;
      });
    }

    if (type === "kame.clip") {
      return (async () => {
        const session = await getSession();
        if (!session) throw new Error("Reconnect");
        const tab = await activeTab();
        await ensureContent(tab.id!, tab.url);
        const page = await browser.tabs.sendMessage(tab.id!, { type: "kame.extract" });
        return apiFetch("/api/v1/extension/clip", {
          method: "POST",
          body: JSON.stringify({
            url: page.url,
            title: page.hints?.title || tab.title || "",
            company: page.hints?.company || "",
            json_ld: page.hints?.json_ld || null,
            track_id: session.trackId || null,
            platform: page.platform || detectPlatform(page.url),
          }),
        });
      })();
    }

    if (type === "kame.autofill") {
      return (async () => {
        const session = await getSession();
        if (!session?.profileId) throw new Error("Pick a profile");
        const tab = await activeTab();
        await ensureContent(tab.id!, tab.url);
        const page = await browser.tabs.sendMessage(tab.id!, { type: "kame.extract" });
        const plan = await apiFetch<{
          instructions: unknown[];
          autofill_allowed: boolean;
          notes: string[];
          page_ai_restricted: boolean;
          run_id: string;
        }>("/api/v1/extension/runs/plan-page", {
          method: "POST",
          body: JSON.stringify({
            fields: page.fields || [],
            page_url: page.url,
            page_text: page.pageText || "",
            platform: page.platform,
            profile_id: session.profileId,
            track_id: session.trackId || null,
            job_id: (msg as { jobId?: string }).jobId || null,
          }),
        });
        let result = { filled: 0, checkpoints: 0, skipped: 0 };
        if (plan.autofill_allowed) {
          result = await browser.tabs.sendMessage(tab.id!, {
            type: "kame.fill",
            instructions: plan.instructions,
          });
        }
        return { ...plan, result };
      })();
    }

    if (type === "kame.logApplied") {
      return (async () => {
        const session = await getSession();
        if (!session) throw new Error("Reconnect");
        const tab = await activeTab();
        return apiFetch("/api/v1/extension/log-applied", {
          method: "POST",
          body: JSON.stringify({
            track_job_id: (msg as { trackJobId?: string }).trackJobId || null,
            job_id: (msg as { jobId?: string }).jobId || null,
            track_id: session.trackId || null,
            run_id: (msg as { runId?: string }).runId || null,
            confirmation_url: tab.url || "",
            notes: (msg as { notes?: string }).notes || "",
          }),
        });
      })();
    }

    if (type === "kame.answerInsert") {
      return (async () => {
        const session = await getSession();
        if (!session?.profileId) throw new Error("Pick a profile");
        const tab = await activeTab();
        await ensureContent(tab.id!, tab.url);
        const focused = await browser.tabs.sendMessage(tab.id!, { type: "kame.focused" });
        const draft = await apiFetch<{
          draft: string;
          ai_restricted: boolean;
          source: string;
          note?: string;
        }>("/api/v1/extension/answer-insert", {
          method: "POST",
          body: JSON.stringify({
            profile_id: session.profileId,
            question: focused?.question || (msg as { question?: string }).question || "",
            page_context: tab.url || "",
          }),
        });
        if (draft.draft && !draft.ai_restricted) {
          await browser.tabs.sendMessage(tab.id!, {
            type: "kame.fill",
            instructions: [
              {
                field_id: focused?.field_id || "focused",
                action: "fill",
                value: draft.draft,
                badge: "Draft",
              },
            ],
          });
        }
        return draft;
      })();
    }

    if (type === "kame.sessionSummary") {
      return apiFetch("/api/v1/extension/session");
    }

    return undefined;
  });

  // Web app handshake: Settings → Connect extension
  browser.runtime.onMessageExternal.addListener((msg, _sender, sendResponse) => {
    const m = msg as ConnectMsg;
    if (
      m?.type === "kame.connect" &&
      looksLikeExtensionToken(m.token || "") &&
      m.workspaceId &&
      isAllowedApiBase(m.apiBase || "")
    ) {
      const session: ExtSession = {
        token: m.token,
        workspaceId: m.workspaceId,
        apiBase: m.apiBase,
        trackId: m.trackId,
        profileId: m.profileId,
      };
      setSession(session).then(() => sendResponse({ ok: true }));
      return true;
    }
    if (m?.type === "kame.connect") {
      sendResponse({ ok: false, error: "Untrusted connect request" });
      return true;
    }
    if ((msg as { type?: string })?.type === "kame.ping") {
      sendResponse({ ok: true, version: browser.runtime.getManifest().version });
      return true;
    }
    return false;
  });
});
