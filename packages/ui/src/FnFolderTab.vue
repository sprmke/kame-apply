<script setup lang="ts">
/** Folder-tab shape for Tracks and dossiers. `hue` picks one of the eight Track colors. */
defineProps<{ hue: 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8; active?: boolean }>();
</script>

<template>
  <span
    class="inline-flex min-h-11 items-center gap-2 rounded-t-md border border-b-0 px-3 text-sm"
    :class="
      active ? 'border-rule bg-paper-1 font-medium text-ink-900' : 'border-transparent text-ink-600'
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
