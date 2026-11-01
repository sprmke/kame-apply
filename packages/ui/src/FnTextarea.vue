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
    class="w-full rounded-sm border bg-paper-0 px-3 py-2 text-base text-ink-900 placeholder:text-ink-400 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-persimmon-700"
    :class="invalid ? 'border-oxblood-600' : 'border-edge'"
  />
</template>
