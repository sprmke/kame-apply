<script setup lang="ts">
/** Risk is a level with a glyph and a word, never color alone. */
const props = defineProps<{ level: "clear" | "caution" | "danger"; label: string }>();
const glyph = { clear: "✓", caution: "!", danger: "✕" } as const;
const tone = {
  clear: "border-fern-600 text-fern-600",
  caution: "border-saffron-600 text-saffron-600",
  danger: "border-oxblood-600 text-oxblood-600",
} as const;
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-sm border-2 px-2 py-0.5 text-xs font-semibold tracking-wide uppercase"
    :class="tone[props.level]"
    :data-level="props.level"
  >
    <span aria-hidden="true">{{ glyph[props.level] }}</span>
    <span class="text-ink-900">{{ label }}</span>
  </span>
</template>
