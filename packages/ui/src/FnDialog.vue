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
  /** dialog: centered. sheet: bottom on phones, right edge from 768px. */
  variant?: "dialog" | "sheet";
  closeLabel?: string;
}>();

const cls = computed(() =>
  props.variant === "sheet"
    ? "fixed inset-x-0 bottom-0 max-h-[85dvh] rounded-t-md md:inset-y-0 md:right-0 md:left-auto md:max-h-none md:w-[420px] md:rounded-none md:rounded-l-md"
    : "fixed top-1/2 left-1/2 max-h-[85dvh] w-[calc(100vw-32px)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-md",
);
</script>

<template>
  <DialogRoot v-model:open="open">
    <slot name="trigger" />
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-40 bg-ink-900/40" />
      <DialogContent
        class="z-50 flex flex-col gap-4 overflow-y-auto border border-rule bg-paper-1 p-5 shadow-float focus:outline-none"
        :class="cls"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex flex-col gap-1">
            <DialogTitle class="font-serif text-lg font-semibold text-ink-900">{{
              title
            }}</DialogTitle>
            <DialogDescription v-if="description" class="text-sm text-ink-600">{{
              description
            }}</DialogDescription>
            <DialogDescription v-else class="sr-only">{{ title }}</DialogDescription>
          </div>
          <DialogClose
            class="-mt-1 -mr-2 grid size-11 shrink-0 place-items-center rounded-sm text-ink-600 hover:bg-paper-2 focus-visible:outline-2 focus-visible:outline-persimmon-700"
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
