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
    class="min-h-11 w-full rounded-sm border bg-paper-0 px-3 text-base text-ink-900 placeholder:text-ink-400 transition-colors duration-[var(--dur-steady)] focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-persimmon-700 disabled:opacity-50"
    :class="invalid ? 'border-oxblood-600' : 'border-edge'"
  />
</template>
