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
      class="flex items-start gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-float)]"
      @update:open="(o: boolean) => !o && dismiss(t.id)"
    >
      <span aria-hidden="true" :class="tint[t.tone]" class="mt-0.5 w-4 text-center font-bold">{{
        glyph[t.tone]
      }}</span>
      <div class="flex-1">
        <ToastTitle class="text-sm font-semibold text-ink-900">{{ t.title }}</ToastTitle>
        <ToastDescription v-if="t.description" class="mt-1 text-sm text-ink-600">{{
          t.description
        }}</ToastDescription>
      </div>
      <button
        type="button"
        class="-m-2 grid size-11 place-items-center rounded-full text-ink-600 hover:bg-paper-2 focus-visible:outline-2 focus-visible:outline-brand-500"
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
