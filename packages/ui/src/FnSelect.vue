<script setup lang="ts">
import {
  SelectContent,
  SelectItem,
  SelectItemIndicator,
  SelectItemText,
  SelectPortal,
  SelectRoot,
  SelectTrigger,
  SelectValue,
  SelectViewport,
} from "reka-ui";

export type SelectOption = { value: string; label: string; disabled?: boolean };

const model = defineModel<string>();
defineProps<{
  options: SelectOption[];
  placeholder?: string;
  id?: string;
  invalid?: boolean;
  disabled?: boolean;
}>();
</script>

<template>
  <SelectRoot v-model="model" :disabled="disabled">
    <SelectTrigger
      :id="id"
      :aria-invalid="invalid || undefined"
      class="flex min-h-12 w-full items-center justify-between gap-2 rounded-md border bg-paper-1 px-4 text-left text-base text-ink-900 shadow-[var(--shadow-card)] transition-colors hover:border-edge focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none disabled:opacity-50 data-[placeholder]:text-ink-400"
      :class="invalid ? 'border-oxblood-600' : 'border-rule'"
    >
      <SelectValue :placeholder="placeholder" />
      <span aria-hidden="true" class="text-ink-400">▾</span>
    </SelectTrigger>
    <SelectPortal>
      <SelectContent
        position="popper"
        :side-offset="6"
        class="z-50 min-w-[var(--reka-select-trigger-width)] rounded-lg border border-rule bg-paper-1 p-1.5 shadow-[var(--shadow-float)]"
      >
        <SelectViewport>
          <SelectItem
            v-for="o in options"
            :key="o.value"
            :value="o.value"
            :disabled="o.disabled"
            class="flex min-h-11 cursor-pointer items-center justify-between gap-2 rounded-md px-3 text-sm text-ink-900 outline-none data-[disabled]:opacity-50 data-[highlighted]:bg-brand-50 data-[highlighted]:text-brand-700"
          >
            <SelectItemText>{{ o.label }}</SelectItemText>
            <SelectItemIndicator aria-hidden="true">✓</SelectItemIndicator>
          </SelectItem>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>
