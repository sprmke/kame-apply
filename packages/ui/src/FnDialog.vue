<script setup lang="ts">
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from "reka-ui";
import { computed } from "vue";

const open = defineModel<boolean>("open", { default: false });
const props = defineProps<{
  title: string;
  description?: string;
  variant?: "dialog" | "sheet";
  closeLabel?: string;
}>();

const cls = computed(() =>
  props.variant === "sheet"
    ? "fixed inset-x-0 bottom-0 max-h-[88dvh] rounded-t-2xl md:inset-y-0 md:right-0 md:left-auto md:max-h-none md:w-[440px] md:rounded-none md:rounded-l-2xl"
    : "fixed top-1/2 left-1/2 max-h-[88dvh] w-[calc(100vw-32px)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl",
);
</script>

<template>
  <DialogRoot v-model:open="open">
    <slot name="trigger" />
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-40 bg-ink-900/50" />
      <DialogContent
        class="z-50 flex flex-col gap-5 overflow-y-auto border border-rule bg-paper-1 p-6 shadow-[var(--shadow-float)] focus:outline-none"
        :class="cls"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex flex-col gap-1">
            <DialogTitle class="text-xl font-bold tracking-[-0.02em] text-ink-900">{{
              title
            }}</DialogTitle>
            <DialogDescription v-if="description" class="text-sm text-ink-600">{{
              description
            }}</DialogDescription>
            <DialogDescription v-else class="sr-only">{{ title }}</DialogDescription>
          </div>
          <DialogClose
            class="-mt-2 -mr-2 grid size-11 shrink-0 place-items-center rounded-full text-ink-600 hover:bg-paper-2 focus-visible:outline-2 focus-visible:outline-brand-500"
            :aria-label="closeLabel ?? 'Close'"
          >
            <span aria-hidden="true" class="text-xl leading-none">×</span>
          </DialogClose>
        </div>
        <slot />
        <div v-if="$slots.footer" class="flex flex-wrap justify-end gap-2">
          <slot name="footer" />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
