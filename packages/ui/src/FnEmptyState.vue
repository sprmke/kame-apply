<script setup lang="ts">
/** Empty, error, and no-results states: one line, one action, nothing else. */
withDefaults(defineProps<{ title: string; body?: string; tone?: "neutral" | "danger" }>(), {
  tone: "neutral",
});
</script>

<template>
  <div
    class="flex flex-col items-start gap-3 rounded-xl border border-dashed border-rule px-5 py-8"
  >
    <div v-if="$slots.icon" aria-hidden="true" class="text-ink-400">
      <slot name="icon" />
    </div>
    <div class="flex flex-col gap-1">
      <p class="font-semibold text-ink-900" :class="tone === 'danger' ? 'text-oxblood-600' : ''">
        {{ title }}
      </p>
      <p v-if="body" class="max-w-prose text-sm leading-6 text-ink-600">{{ body }}</p>
    </div>
    <div v-if="$slots.default" class="flex flex-wrap items-center gap-2">
      <slot />
    </div>
  </div>
</template>
