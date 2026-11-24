<script setup lang="ts">
/**
 * Wraps a skeleton composition so assistive tech announces the wait once, and the whole region is
 * marked busy while the real content loads. Keep the wrapper's layout classes identical to the
 * content it replaces so nothing moves when the data lands.
 */
withDefaults(defineProps<{ label?: string }>(), { label: "Loading" });
</script>

<template>
  <div role="status" aria-live="polite" aria-busy="true">
    <slot />
    <span class="sr-only">{{ label }}</span>
  </div>
</template>
