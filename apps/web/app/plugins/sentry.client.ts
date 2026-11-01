/**
 * Optional Sentry. Loads only when NUXT_PUBLIC_SENTRY_DSN is set.
 * Uses dynamic import so the dependency stays optional in local/dev.
 */
export default defineNuxtPlugin(async (nuxtApp) => {
  const dsn = String(useRuntimeConfig().public.sentryDsn || "");
  if (!dsn) return;
  try {
    const Sentry = await import("@sentry/vue");
    Sentry.init({
      app: nuxtApp.vueApp,
      dsn,
      sendDefaultPii: false,
      tracesSampleRate: 0.05,
    });
  } catch {
    // @sentry/vue not installed; ignore.
  }
});
