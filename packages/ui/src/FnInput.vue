<script setup lang="ts">
const model = defineModel<string | null | undefined>({ default: "" });
defineProps<{
  type?: string;
  invalid?: boolean;
  id?: string;
  placeholder?: string;
  autocomplete?: string;
  disabled?: boolean;
  required?: boolean;
  describedby?: string;
  name?: string;
  inputmode?: "text" | "email" | "numeric" | "decimal" | "search" | "url";
}>();
</script>

<template>
  <input
    :id="id"
    v-model="model"
    :name="name"
    :type="type ?? 'text'"
    :placeholder="placeholder"
    :autocomplete="autocomplete"
    :disabled="disabled"
    :required="required"
    :inputmode="inputmode"
    :aria-invalid="invalid || undefined"
    :aria-describedby="describedby"
    class="min-h-12 w-full rounded-md border bg-paper-1 px-4 text-base text-ink-900 shadow-[var(--shadow-card)] transition-colors duration-[var(--dur-steady)] placeholder:text-ink-400 hover:border-edge focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none disabled:opacity-50"
    :class="invalid ? 'border-oxblood-600' : 'border-rule'"
  />
</template>
