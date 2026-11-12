<script setup lang="ts">
import FnTooltip from "./FnTooltip.vue";

/** A word with a dotted underline that shows its plain definition on hover or tap. */
defineProps<{ term: string; definition: string }>();
</script>

<template>
  <FnTooltip :text="definition" side="top">
    <button
      type="button"
      class="inline cursor-help border-b border-dotted border-edge text-inherit underline-offset-2 hover:border-ink-600"
      :aria-label="`${term}: ${definition}`"
    >
      {{ term }}
    </button>
  </FnTooltip>
</template>
