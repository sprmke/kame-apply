<script setup lang="ts">
import { ToastDescription, ToastProvider, ToastRoot, ToastTitle, ToastViewport } from "reka-ui";
import { useToast } from "./toast";

defineProps<{ dismissLabel?: string }>();
const { toasts, dismiss } = useToast();
const glyph = { neutral: "•", success: "✓", danger: "✕" } as const;
const tint = {
  neutral: "text-ink-600",
  success: "text-fern-600",
  danger: "text-oxblood-600",
} as const;
</script>

<template>
  <ToastProvider :duration="5000">
    <ToastRoot
      v-for="t in toasts"
      :key="t.id"
      class="flex items-start gap-3 rounded-md border border-rule bg-paper-1 p-3 shadow-float"
      @update:open="(o: boolean) => !o && dismiss(t.id)"
    >
      <span aria-hidden="true" :class="tint[t.tone]" class="mt-px w-4 text-center">{{
        glyph[t.tone]
      }}</span>
      <div class="flex-1">
        <ToastTitle class="text-sm font-medium text-ink-900">{{ t.title }}</ToastTitle>
        <ToastDescription v-if="t.description" class="mt-0.5 text-xs text-ink-600">{{
          t.description
        }}</ToastDescription>
      </div>
      <button
        type="button"
        class="-m-2 grid size-11 place-items-center rounded-sm text-ink-600 hover:bg-paper-2 focus-visible:outline-2 focus-visible:outline-persimmon-700"
        :aria-label="dismissLabel ?? 'Dismiss'"
        @click="dismiss(t.id)"
      >
        <span aria-hidden="true">×</span>
      </button>
    </ToastRoot>
    <ToastViewport
      class="fixed right-4 bottom-4 z-[60] m-0 flex w-[calc(100vw-32px)] max-w-sm list-none flex-col gap-2 p-0 max-md:bottom-20"
    />
  </ToastProvider>
</template>
