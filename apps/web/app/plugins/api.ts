import { client } from "@kame/api-client";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

/** Points the generated client at the API and adds auth + workspace headers. */
export default defineNuxtPlugin(() => {
  const { public: cfg } = useRuntimeConfig();
  const auth = useAuthStore();
  const workspace = useWorkspaceStore();

  client.setConfig({ baseUrl: cfg.apiBase, credentials: "include", throwOnError: true });

  client.interceptors.request.use(async (request) => {
    const path = new URL(request.url).pathname;
    // Auth endpoints carry the refresh cookie, not a bearer token (and must not recurse).
    const isAuthRoute =
      path.startsWith("/api/v1/auth/") &&
      !path.endsWith("/logout") &&
      !path.endsWith("/google/link") &&
      !path.endsWith("/verify-email/resend");
    if (!isAuthRoute) {
      const token = await auth.ensureFresh();
      if (token) request.headers.set("Authorization", `Bearer ${token}`);
      if (workspace.currentId) request.headers.set("X-Workspace-Id", workspace.currentId);
    }
    return request;
  });

  client.interceptors.response.use(async (response, request) => {
    const path = new URL(request.url).pathname;
    if (response.status === 401 && !path.startsWith("/api/v1/auth/")) {
      // The server rejected a token we believed fresh (revoked session). Go sign in again.
      auth.clear();
      workspace.reset();
      await navigateTo({ path: "/login", query: { next: useRoute().fullPath } });
    }
    return response;
  });
});
