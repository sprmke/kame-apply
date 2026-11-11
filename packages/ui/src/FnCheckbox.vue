<script setup lang="ts">
import { CheckboxIndicator, CheckboxRoot } from "reka-ui";

const model = defineModel<boolean>({ default: false });
defineProps<{ label: string; id?: string }>();
</script>

<template>
  <label class="flex min-h-11 cursor-pointer items-center gap-3 text-sm font-medium text-ink-900">
    <CheckboxRoot
      :id="id"
      v-model="model"
      class="grid size-5 shrink-0 place-items-center rounded-md border border-edge bg-paper-1 data-[state=checked]:border-brand-600 data-[state=checked]:bg-brand-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
    >
      <CheckboxIndicator class="text-xs leading-none text-on-brand">✓</CheckboxIndicator>
    </CheckboxRoot>
    {{ label }}
  </label>
</template>
