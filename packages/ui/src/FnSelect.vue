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
      class="flex min-h-11 w-full items-center justify-between gap-2 rounded-sm border bg-paper-0 px-3 text-left text-base text-ink-900 data-[placeholder]:text-ink-400 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-persimmon-700 disabled:opacity-50"
      :class="invalid ? 'border-oxblood-600' : 'border-edge'"
    >
      <SelectValue :placeholder="placeholder" />
      <span aria-hidden="true" class="text-ink-600">▾</span>
    </SelectTrigger>
    <SelectPortal>
      <SelectContent
        position="popper"
        :side-offset="4"
        class="z-50 min-w-[var(--reka-select-trigger-width)] rounded-md border border-rule bg-paper-1 p-1 shadow-float"
      >
        <SelectViewport>
          <SelectItem
            v-for="o in options"
            :key="o.value"
            :value="o.value"
            :disabled="o.disabled"
            class="flex min-h-11 cursor-pointer items-center justify-between gap-2 rounded-sm px-3 text-sm text-ink-900 outline-none data-[disabled]:opacity-50 data-[highlighted]:bg-paper-2"
          >
            <SelectItemText>{{ o.label }}</SelectItemText>
            <SelectItemIndicator aria-hidden="true">✓</SelectItemIndicator>
          </SelectItem>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>
