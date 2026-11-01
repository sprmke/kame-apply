import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "wxt";

const webOrigins = [
  "http://localhost:3100/*",
  "https://*.kame.apply/*",
  "https://app.kame.apply/*",
];

export default defineConfig({
  modules: ["@wxt-dev/module-vue"],
  vite: () => ({ plugins: [tailwindcss()] }),
  manifest: {
    name: "Kame Apply",
    description: "Clip jobs and fill applications in your own browser session.",
    permissions: ["sidePanel", "storage", "activeTab", "scripting"],
    optional_host_permissions: [
      "https://*.linkedin.com/*",
      "https://*.indeed.com/*",
      "https://*.jobstreet.com/*",
      "https://*.seek.com.au/*",
      "https://*.seek.co.nz/*",
      "https://boards.greenhouse.io/*",
      "https://*.greenhouse.io/*",
      "https://jobs.lever.co/*",
      "https://*.ashbyhq.com/*",
      "https://*.myworkdayjobs.com/*",
      "https://*.workable.com/*",
      "https://*.smartrecruiters.com/*",
      "http://localhost/*",
      "https://*/*",
    ],
    externally_connectable: {
      matches: webOrigins,
    },
    action: { default_title: "Kame Apply" },
  },
});
