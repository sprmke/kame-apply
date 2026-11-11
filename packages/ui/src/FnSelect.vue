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
  ariaLabel?: string;
}>();
</script>

<template>
  <SelectRoot v-model="model" :disabled="disabled">
    <SelectTrigger
      :id="id"
      :aria-label="ariaLabel"
      :aria-invalid="invalid || undefined"
      class="group relative flex min-h-12 w-full items-center rounded-md border bg-paper-1 pr-11 pl-4 text-left text-base text-ink-900 shadow-[var(--shadow-card)] transition-colors hover:border-edge focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none disabled:opacity-50 data-[placeholder]:text-ink-400"
      :class="invalid ? 'border-oxblood-600' : 'border-rule'"
    >
      <SelectValue :placeholder="placeholder" class="min-w-0 flex-1 truncate" />
      <span
        aria-hidden="true"
        class="pointer-events-none absolute top-1/2 right-4 -translate-y-1/2 text-ink-400 transition-transform duration-150 group-data-[state=open]:rotate-180"
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path
            d="m4 6 4 4 4-4"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </span>
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
            <SelectItemIndicator aria-hidden="true" class="text-brand-700">✓</SelectItemIndicator>
          </SelectItem>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>
