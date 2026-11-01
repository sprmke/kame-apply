import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "./spec.json",
  output: { path: "./generated", postProcess: [] },
  plugins: ["@hey-api/typescript", "@hey-api/sdk", "@tanstack/vue-query"],
});
