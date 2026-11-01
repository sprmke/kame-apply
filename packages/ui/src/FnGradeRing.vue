<script setup lang="ts">
/** A simulated grade, shown as a letter in a thin ring. `from` renders a transition. */
defineProps<{ grade: string; from?: string; simulationLabel: string }>();
</script>

<template>
  <span class="inline-flex items-center gap-2">
    <span v-if="from" class="font-serif text-ink-600 line-through decoration-1">{{ from }}</span>
    <span v-if="from" aria-hidden="true" class="text-ink-600">→</span>
    <span
      class="grid size-11 place-items-center rounded-full border border-ink-900 font-serif text-lg font-semibold text-ink-900"
    >
      {{ grade }}
    </span>
    <span class="text-xs text-ink-600">{{ simulationLabel }}</span>
  </span>
</template>
