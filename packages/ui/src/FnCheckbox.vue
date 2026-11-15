<script setup lang="ts">
import { CheckboxIndicator, CheckboxRoot } from "reka-ui";

const model = defineModel<boolean>({ default: false });
withDefaults(
  defineProps<{ label: string; id?: string; hideLabel?: boolean; disabled?: boolean }>(),
  { hideLabel: false, disabled: false },
);
</script>

<template>
  <label class="flex min-h-11 cursor-pointer items-center gap-3 text-sm font-medium text-ink-900">
    <CheckboxRoot
      :id="id"
      v-model="model"
      :disabled="disabled"
      class="grid size-5 shrink-0 place-items-center rounded-md border border-edge bg-paper-1 data-[state=checked]:border-brand-600 data-[state=checked]:bg-brand-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 disabled:opacity-50"
    >
      <CheckboxIndicator class="text-xs leading-none text-on-brand">✓</CheckboxIndicator>
    </CheckboxRoot>
    <span :class="hideLabel ? 'sr-only' : ''">{{ label }}</span>
  </label>
</template>
