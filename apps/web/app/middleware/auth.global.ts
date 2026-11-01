import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

const PUBLIC = [
  "/login",
  "/register",
  "/verify-email",
  "/forgot-password",
  "/reset-password",
  "/auth/callback",
  "/_design",
];

export default defineNuxtRouteMiddleware(async (to) => {
  const auth = useAuthStore();
  await auth.bootstrap();
  const isPublic = PUBLIC.includes(to.path);

  if (!auth.isAuthed) {
    // /invite is reachable signed out so it can explain what to do, then return here.
    if (isPublic || to.path === "/invite") return;
    return navigateTo({ path: "/login", query: { next: to.fullPath } });
  }

  const workspace = useWorkspaceStore();
  if (!workspace.loaded) await workspace.load();
  if (["/login", "/register", "/forgot-password"].includes(to.path)) return navigateTo("/");
});
