<script setup lang="ts">
const model = defineModel<string | null | undefined>({ default: "" });
defineProps<{
  invalid?: boolean;
  id?: string;
  rows?: number;
  placeholder?: string;
  describedby?: string;
}>();
</script>

<template>
  <textarea
    :id="id"
    v-model="model"
    :rows="rows ?? 4"
    :placeholder="placeholder"
    :aria-invalid="invalid || undefined"
    :aria-describedby="describedby"
    class="w-full rounded-md border bg-paper-1 px-4 py-3 text-base text-ink-900 shadow-[var(--shadow-card)] transition-colors duration-[var(--dur-steady)] placeholder:text-ink-400 hover:border-edge focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
    :class="invalid ? 'border-oxblood-600' : 'border-rule'"
  />
</template>
