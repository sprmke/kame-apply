#!/usr/bin/env node
// Verifies WCAG contrast for the Signal token pairs in packages/ui/src/tokens.css.
// Themes are read from the CSS itself, so editing a token can never silently break contrast.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const css = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../../packages/ui/src/tokens.css"),
  "utf8",
);

const decls = (block) =>
  Object.fromEntries(
    [...block.matchAll(/--([\w-]+):\s*oklch\(([^)]+)\)\s*;/g)].map(([, k, v]) => {
      const [L, C, H] = v.split("/")[0].trim().split(/\s+/).map(Number);
      return [k, { L, C, H }];
    }),
  );

// Pull the declaration body of the first rule whose header contains `needle` (after `from`).
function body(needle, from = 0) {
  const i = css.indexOf(needle, from);
  if (i < 0) throw new Error(`token block not found: ${needle}`);
  let depth = 0;
  const start = css.indexOf("{", i);
  for (let j = start; j < css.length; j++) {
    if (css[j] === "{") depth++;
    if (css[j] === "}" && --depth === 0) return css.slice(start + 1, j);
  }
  throw new Error("unbalanced braces");
}

const light = decls(body("\n:root {", css.indexOf("@theme")));
const darkRule = decls(body(':root[data-theme="dark"]'));
const dark = { ...light, ...darkRule };
const hcLight = {
  ...light,
  ...decls(body(':root:not([data-theme="dark"]) {', css.indexOf("prefers-contrast: more)"))),
};
const hcDark = {
  ...dark,
  ...decls(
    body(':root:not([data-theme="light"]) {', css.indexOf("prefers-color-scheme: dark) and")),
  ),
};

function oklchToLinear({ L, C, H }) {
  const h = (H * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);
  const l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s_ = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const clamp = (x) => Math.min(1, Math.max(0, x));
  return [
    clamp(4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_),
    clamp(-1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_),
    clamp(-0.0041960863 * l_ - 0.7034186147 * m_ + 1.707614701 * s_),
  ];
}
const luminance = (c) => {
  const [r, g, b] = oklchToLinear(c);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const ratio = (a, b) => {
  const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
};

// [foreground, background, minimum ratio, why]
const pairs = [
  ...["paper-0", "paper-1", "paper-2"].flatMap((bg) => [
    ["ink-900", bg, 7, "body text"],
    ["ink-600", bg, 4.5, "secondary text"],
    ["pencil", bg, 4.5, "AI draft text"],
  ]),
  ["ink-400", "paper-0", 3, "placeholders (never essential info)"],
  ["brand-700", "paper-0", 4.5, "accent text and links"],
  ["brand-700", "paper-1", 4.5, "accent text on panels"],
  ["on-brand", "brand-500", 4.5, "text on brand fills"],
  ["edge", "paper-0", 3, "control borders"],
  ["edge", "paper-1", 3, "control borders on panels"],
  ...["fern-600", "saffron-600", "oxblood-600"].flatMap((c) => [
    [c, "paper-0", 3, "status glyphs and rules"],
    [c, "paper-1", 3, "status glyphs on panels"],
  ]),
  ...Array.from({ length: 8 }, (_, i) => [`track-${i + 1}`, "paper-0", 3, "Track identity"]),
];

let failures = 0;
for (const [name, theme] of [
  ["light", light],
  ["dark", dark],
  ["high-contrast light", hcLight],
  ["high-contrast dark", hcDark],
]) {
  for (const [fg, bg, min, why] of pairs) {
    if (!theme[fg] || !theme[bg]) throw new Error(`missing token ${fg} or ${bg} in ${name}`);
    const r = ratio(theme[fg], theme[bg]);
    if (r < min) {
      failures++;
      console.error(`FAIL [${name}] ${fg} on ${bg}: ${r.toFixed(2)} < ${min} (${why})`);
    }
  }
}
if (failures) {
  console.error(`\n${failures} contrast failure(s)`);
  process.exit(1);
}
console.log(`OK, token contrast: ${pairs.length} pairs x 4 themes`);
