<script setup lang="ts">
/** Risk is a level with a glyph and a word, never color alone. */
const props = defineProps<{ level: "clear" | "caution" | "danger"; label: string }>();
const glyph = { clear: "✓", caution: "!", danger: "✕" } as const;
const tone = {
  clear: "border-fern-600/40 bg-fern-600/10 text-fern-600",
  caution: "border-saffron-600/40 bg-saffron-600/10 text-saffron-600",
  danger: "border-oxblood-600/40 bg-oxblood-600/10 text-oxblood-600",
} as const;
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold tracking-wide uppercase"
    :class="tone[props.level]"
    :data-level="props.level"
  >
    <span aria-hidden="true">{{ glyph[props.level] }}</span>
    <span class="text-ink-900">{{ label }}</span>
  </span>
</template>
