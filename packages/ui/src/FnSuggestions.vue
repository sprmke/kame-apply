<script setup lang="ts">
import FnButton from "./FnButton.vue";

defineProps<{
  /** Common answers for one question. The field stays free text. */
  options: string[];
  /** Accessible name for the group. */
  label: string;
}>();

const emit = defineEmits<{ select: [value: string] }>();
</script>

<template>
  <div
    v-if="options.length"
    class="flex flex-wrap items-center gap-2"
    role="group"
    :aria-label="label"
  >
    <FnButton
      v-for="option in options"
      :key="option"
      size="sm"
      tone="quiet"
      class="min-h-11 rounded-full px-3 text-sm font-medium"
      @click="emit('select', option)"
    >
      {{ option }}
    </FnButton>
  </div>
</template>
