<script setup lang="ts">
import { Primitive, type PrimitiveProps } from "reka-ui";
import { tv, type VariantProps } from "tailwind-variants";

const button = tv({
  base:
    "inline-flex items-center justify-center gap-2 rounded-sm font-medium whitespace-nowrap " +
    "transition-colors duration-[var(--dur-steady)] ease-[var(--ease-steady)] " +
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-persimmon-700 " +
    "disabled:opacity-50 disabled:pointer-events-none aria-disabled:opacity-50 aria-disabled:pointer-events-none",
  variants: {
    tone: {
      primary: "bg-persimmon-500 text-on-brand hover:brightness-95",
      quiet: "border border-edge bg-paper-1 text-ink-900 hover:bg-paper-2",
      ghost: "text-ink-900 hover:bg-paper-2",
      danger: "border border-oxblood-600 bg-paper-1 text-oxblood-600 hover:bg-paper-2",
    },
    size: {
      md: "min-h-11 px-4 text-sm",
      sm: "min-h-11 px-3 text-xs md:min-h-8",
    },
  },
  defaultVariants: { tone: "quiet", size: "md" },
});

type Props = PrimitiveProps & {
  tone?: VariantProps<typeof button>["tone"];
  size?: VariantProps<typeof button>["size"];
  loading?: boolean;
  type?: "button" | "submit" | "reset";
};
const props = withDefaults(defineProps<Props>(), { as: "button", type: "button" });
</script>

<template>
  <Primitive
    :as="props.as"
    :as-child="props.asChild"
    :type="props.as === 'button' ? props.type : undefined"
    :aria-busy="props.loading || undefined"
    :disabled="props.as === 'button' && props.loading ? true : undefined"
    :class="button({ tone: props.tone, size: props.size })"
  >
    <span
      v-if="props.loading"
      class="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none"
      aria-hidden="true"
    />
    <slot />
  </Primitive>
</template>
