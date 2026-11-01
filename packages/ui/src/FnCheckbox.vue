<script setup lang="ts">
import { CheckboxIndicator, CheckboxRoot } from "reka-ui";

const model = defineModel<boolean>({ default: false });
defineProps<{ label: string; id?: string }>();
</script>

<template>
  <label class="flex min-h-11 cursor-pointer items-center gap-3 text-sm text-ink-900">
    <CheckboxRoot
      :id="id"
      v-model="model"
      class="grid size-5 shrink-0 place-items-center rounded-sm border border-edge bg-paper-0 data-[state=checked]:border-persimmon-700 data-[state=checked]:bg-persimmon-500"
    >
      <CheckboxIndicator class="text-xs leading-none text-on-brand">✓</CheckboxIndicator>
    </CheckboxRoot>
    {{ label }}
  </label>
</template>
