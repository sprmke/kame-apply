/**
 * Register the service worker and expose a helper for push permission.
 * Ask for permission only after a Needs-you item appears (caller decides timing).
 */
export default defineNuxtPlugin(() => {
  if (!("serviceWorker" in navigator)) return;

  navigator.serviceWorker.register("/sw.js").catch(() => {
    /* ignore offline / file:// */
  });

  if (import.meta.client) {
    const link = document.createElement("link");
    link.rel = "manifest";
    link.href = "/manifest.webmanifest";
    document.head.appendChild(link);
  }
});
