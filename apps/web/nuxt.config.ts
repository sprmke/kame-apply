import tailwindcss from "@tailwindcss/vite";

export default defineNuxtConfig({
  compatibilityDate: "2026-10-01",
  devtools: { enabled: false },
  // App routes are a SPA; public/marketing/legal pages opt back into prerendering below.
  ssr: false,
  modules: ["@nuxt/eslint", "@nuxt/icon", "@nuxt/fonts", "@nuxtjs/i18n", "@pinia/nuxt"],
  css: ["~/assets/css/main.css"],
  // Reset, verify and invite links carry tokens in the query string; never send them as a Referer.
  app: {
    head: {
      meta: [{ name: "referrer", content: "no-referrer" }],
      // CSP for the SPA shell. API calls go to apiBase; fonts from Google Fonts provider.
      htmlAttrs: { lang: "en" },
    },
  },
  vite: { plugins: [tailwindcss()] },
  routeRules: {
    "/": { prerender: true },
    "/legal/**": { prerender: true },
    "/**": {
      headers: {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy":
          "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; object-src 'none'; img-src 'self' data: blob: https:; font-src 'self' https://fonts.gstatic.com data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; script-src 'self' 'unsafe-inline'; connect-src 'self' https: http://127.0.0.1:* http://localhost:*; worker-src 'self' blob:",
      },
    },
  },
  typescript: { strict: true, typeCheck: false },
  icon: { serverBundle: "local", clientBundle: { scan: true } },
  fonts: {
    families: [
      { name: "Instrument Sans", provider: "google", weights: ["400 700"] },
      {
        name: "Newsreader",
        provider: "google",
        weights: ["400 700"],
        styles: ["normal", "italic"],
      },
      { name: "Martian Mono", provider: "google", weights: ["400 600"] },
    ],
  },
  i18n: {
    defaultLocale: "en",
    strategy: "no_prefix",
    locales: [{ code: "en", language: "en-US", file: "en.json" }],
  },
  runtimeConfig: {
    // enableDesign exposes the /_design style guide outside dev (e2e builds set NUXT_PUBLIC_ENABLE_DESIGN=true).
    public: {
      apiBase: "http://localhost:8100",
      enableDesign: false,
      // Chrome extension id for Settings → Connect (NUXT_PUBLIC_EXTENSION_ID).
      extensionId: "",
      // Optional Sentry browser DSN (NUXT_PUBLIC_SENTRY_DSN).
      sentryDsn: "",
    },
  },
  devServer: { port: 3100 },
});
