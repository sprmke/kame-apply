import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "./openapi.json",
  output: { path: "./src/generated", postProcess: [] },
  plugins: [
    "@hey-api/typescript",
    "@hey-api/sdk",
    "@tanstack/vue-query",
    { name: "zod", compatibilityVersion: 3 },
  ],
});
