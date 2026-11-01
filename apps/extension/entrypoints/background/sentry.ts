/** Optional Sentry for the extension service worker. Set VITE_SENTRY_DSN at build time. */
export function initExtensionSentry(): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined;
  if (!dsn) return;
  // Lightweight breadcrumb log; full @sentry/browser is optional at build time.
  console.info("[sentry] DSN configured");
}
