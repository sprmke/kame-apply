<script setup lang="ts">
/** One sentence that states the result of the current values. */
defineProps<{ text: string; tone?: "neutral" | "accent" }>();
</script>

<template>
  <p
    class="flex items-start gap-2 rounded-lg px-3 py-2 text-sm leading-6"
    :class="tone === 'accent' ? 'bg-brand-50 text-brand-800' : 'bg-paper-2 text-ink-600'"
  >
    <span aria-hidden="true" class="mt-0.5 shrink-0 text-xs">●</span>
    <span>{{ text }}</span>
  </p>
</template>
