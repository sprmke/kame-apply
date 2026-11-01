import {
  loginApiV1AuthLoginPost,
  logoutApiV1AuthLogoutPost,
  refreshApiV1AuthRefreshPost,
  registerApiV1AuthRegisterPost,
  type AuthRead,
  type UserRead,
} from "@kame/api-client";
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { isFresh } from "~/lib/jwt";

type Status = "unknown" | "authed" | "anon";

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref<string | null>(null);
  const user = ref<UserRead | null>(null);
  const status = ref<Status>("unknown");
  let inflight: Promise<boolean> | null = null;

  const isAuthed = computed(() => status.value === "authed");

  function apply(r: AuthRead) {
    accessToken.value = r.access_token;
    user.value = r.user;
    status.value = "authed";
  }

  function clear() {
    accessToken.value = null;
    user.value = null;
    status.value = "anon";
  }

  /** Single flight: concurrent callers (many requests, many tabs of work) share one refresh. */
  function refresh(): Promise<boolean> {
    inflight ??= (async () => {
      try {
        const { data } = await refreshApiV1AuthRefreshPost({ throwOnError: true });
        apply(data);
        return true;
      } catch {
        clear();
        return false;
      } finally {
        inflight = null;
      }
    })();
    return inflight;
  }

  async function ensureFresh(): Promise<string | null> {
    if (isFresh(accessToken.value)) return accessToken.value;
    if (status.value === "anon") return null;
    return (await refresh()) ? accessToken.value : null;
  }

  async function bootstrap(): Promise<void> {
    if (status.value === "unknown") await refresh();
  }

  async function login(email: string, password: string) {
    const { data } = await loginApiV1AuthLoginPost({
      body: { email, password },
      throwOnError: true,
    });
    apply(data);
  }

  async function register(email: string, password: string, name?: string) {
    const { data } = await registerApiV1AuthRegisterPost({
      body: { email, password, name: name || null },
      throwOnError: true,
    });
    apply(data);
  }

  async function logout() {
    try {
      await logoutApiV1AuthLogoutPost({ throwOnError: true });
    } catch {
      // The session may already be gone; local sign-out must still succeed.
    }
    clear();
  }

  return {
    accessToken,
    user,
    status,
    isAuthed,
    refresh,
    ensureFresh,
    bootstrap,
    login,
    register,
    logout,
    clear,
  };
});
