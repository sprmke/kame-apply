/** Marks the document once Vue has taken over, so e2e tests never act on a half-loaded page. */
export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.hook("app:mounted", () => {
    document.documentElement.dataset.hydrated = "true";
  });
});
