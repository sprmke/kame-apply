import withNuxt from "./.nuxt/eslint.config.mjs";

export default withNuxt(
  {
    rules: {
      "vue/multi-word-component-names": ["error", { ignores: ["index", "default", "error"] }],
    },
  },
  // Nuxt derives routes and layouts from file names, so single-word names are the convention there.
  {
    files: ["app/pages/**/*.vue", "app/layouts/**/*.vue"],
    rules: { "vue/multi-word-component-names": "off" },
  },
);
