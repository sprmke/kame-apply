<script setup lang="ts">
import { tv, type VariantProps } from "tailwind-variants";

const chip = tv({
  base: "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold",
  variants: {
    tone: {
      neutral: "border-rule bg-paper-2 text-ink-600",
      accent: "border-brand-200 bg-brand-50 text-brand-700",
      pencil: "border-dashed border-pencil bg-paper-0 text-pencil",
    },
  },
  defaultVariants: { tone: "neutral" },
});

defineProps<{
  tone?: VariantProps<typeof chip>["tone"];
  removable?: boolean;
  removeLabel?: string;
}>();
const emit = defineEmits<{ remove: [] }>();
</script>

<template>
  <span :class="chip({ tone })">
    <slot />
    <button
      v-if="removable"
      type="button"
      class="-my-2 -mr-2 grid size-11 place-items-center rounded-full text-ink-600 hover:bg-paper-2 focus-visible:outline-2 focus-visible:outline-brand-500"
      :aria-label="removeLabel"
      @click="emit('remove')"
    >
      <span aria-hidden="true">×</span>
    </button>
  </span>
</template>
