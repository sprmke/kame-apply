<script setup lang="ts">
/** Hexagonal shell plate whose inner line is a forward route arrow. */
withDefaults(defineProps<{ size?: number; wordmark?: boolean }>(), { size: 32, wordmark: false });
</script>

<template>
  <span class="inline-flex items-center gap-2.5">
    <svg :width="size" :height="size" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path d="M16 2.5 28 9.25v13.5L16 29.5 4 22.75V9.25L16 2.5Z" class="fill-brand-500" />
      <path
        d="M9 18.5h10m0 0-3.2-3.2M19 18.5l-3.2 3.2"
        class="stroke-on-brand"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <path
        d="M9 12.5h6"
        class="stroke-on-brand"
        stroke-width="2"
        stroke-linecap="round"
        opacity=".55"
      />
    </svg>
    <span v-if="wordmark" class="font-serif text-lg font-semibold text-ink-900">{{
      $t("app.name")
    }}</span>
  </span>
</template>
