<script setup lang="ts">
/** Search identity chip. `hue` picks one of the eight track colors. */
defineProps<{ hue: 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8; active?: boolean }>();
</script>

<template>
  <span
    class="inline-flex min-h-11 items-center gap-2 rounded-full border px-4 text-sm font-semibold"
    :class="
      active ? 'border-brand-200 bg-brand-50 text-brand-700' : 'border-rule bg-paper-1 text-ink-600'
    "
  >
    <span
      class="size-2.5 rounded-full"
      :style="{ background: `var(--track-${hue})` }"
      aria-hidden="true"
    />
    <slot />
  </span>
</template>
