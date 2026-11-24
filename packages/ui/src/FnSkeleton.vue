<script setup lang="ts">
import { computed, useAttrs } from "vue";
import { tv } from "tailwind-variants";

/**
 * A placeholder bar. Size it with classes (`h-4`, `w-48`, `rounded-full`); the default is one
 * line of body text. Multiple lines render as a paragraph with a shorter last line.
 *
 * Decorative: screen readers get the label from `FnSkeletonGroup`, never from the bars.
 */
defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    /** Number of text lines. Use 1 and size with classes for anything that is not body text. */
    lines?: number;
    /** Width of the last line when `lines` is greater than 1. */
    lastWidth?: string;
  }>(),
  { lines: 1, lastWidth: "60%" },
);

const attrs = useAttrs();

const bar = tv({
  variants: {
    single: {
      true: "h-4 w-full animate-pulse rounded-md bg-paper-2 motion-reduce:animate-none",
      false: "flex flex-col gap-2",
    },
  },
  defaultVariants: { single: true },
});

const single = computed(() => (props.lines ?? 1) <= 1);
const classes = computed(() =>
  bar({ single: single.value, class: attrs.class as string | undefined }),
);
</script>

<template>
  <div v-if="single" :class="classes" aria-hidden="true" />
  <div v-else :class="classes" aria-hidden="true">
    <div
      v-for="n in lines"
      :key="n"
      class="h-4 w-full animate-pulse rounded-md bg-paper-2 motion-reduce:animate-none"
      :style="{ width: n === lines ? lastWidth : '100%' }"
    />
  </div>
</template>
