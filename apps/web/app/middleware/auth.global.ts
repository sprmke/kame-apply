import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";
import { isPublicPath } from "~/lib/public-routes";

export default defineNuxtRouteMiddleware(async (to) => {
  const auth = useAuthStore();
  await auth.bootstrap();
  const isPublic = isPublicPath(to.path);

  if (!auth.isAuthed) {
    // /invite is reachable signed out so it can explain what to do, then return here.
    if (isPublic) return;
    return navigateTo({ path: "/login", query: { next: to.fullPath } });
  }

  const workspace = useWorkspaceStore();
  if (!workspace.loaded) await workspace.load();
  if (["/login", "/register", "/forgot-password"].includes(to.path)) return navigateTo("/");
});
