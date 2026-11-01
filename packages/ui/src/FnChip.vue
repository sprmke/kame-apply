<script setup lang="ts">
import { tv, type VariantProps } from "tailwind-variants";

const chip = tv({
  base: "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-medium",
  variants: {
    tone: {
      neutral: "border-rule bg-paper-1 text-ink-900",
      accent: "border-persimmon-700 bg-paper-1 text-persimmon-700",
      pencil: "border-dashed border-pencil bg-paper-0 text-pencil",
    },
  },
  defaultVariants: { tone: "neutral" },
});

defineProps<{
  tone?: VariantProps<typeof chip>["tone"];
  removable?: boolean;
  removeLabel?: string; // pass a translated name whenever removable
}>();
const emit = defineEmits<{ remove: [] }>();
</script>

<template>
  <span :class="chip({ tone })">
    <slot />
    <button
      v-if="removable"
      type="button"
      class="-my-3 -mr-3 grid size-11 place-items-center rounded-sm text-ink-600 hover:bg-paper-2 focus-visible:outline-2 focus-visible:outline-persimmon-700"
      :aria-label="removeLabel"
      @click="emit('remove')"
    >
      <span aria-hidden="true">×</span>
    </button>
  </span>
</template>
