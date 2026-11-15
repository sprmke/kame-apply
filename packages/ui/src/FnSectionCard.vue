<script setup lang="ts">
import { computed, useId } from "vue";

/** Standard settings or explanation block: title, one intro line, body, one summary line,
 *  and a single "More options" fold. Keeps every page's section rhythm identical. */
defineProps<{
  title: string;
  /** One short line under the title. About 12 words. Omit when the title is unmistakable. */
  intro?: string;
  /** One sentence, generated from current values, stating what will happen. */
  summary?: string;
  /** Label for the advanced fold. Set to false to hide the fold entirely. */
  moreLabel?: string | false;
  tone?: "plain" | "quiet";
}>();
const uid = useId();
const titleId = computed(() => `s-${uid}`);
</script>

<template>
  <section
    :aria-labelledby="titleId"
    class="flex flex-col gap-4 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)] sm:p-5 md:p-6"
    :class="tone === 'quiet' ? 'bg-paper-0 shadow-none' : ''"
  >
    <div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
      <div class="flex min-w-0 flex-col gap-1">
        <h2 :id="titleId" class="text-lg font-bold tracking-[-0.02em] text-ink-900">
          {{ title }}
        </h2>
        <p v-if="intro" class="max-w-2xl text-sm leading-6 text-ink-600">{{ intro }}</p>
      </div>
      <div v-if="$slots.actions" class="flex shrink-0 flex-wrap items-center gap-2">
        <slot name="actions" />
      </div>
    </div>

    <slot />

    <p v-if="summary" class="text-sm leading-6 text-ink-600">{{ summary }}</p>

    <details v-if="$slots.more && moreLabel !== false" class="group border-t border-rule pt-3">
      <summary
        class="flex min-h-11 cursor-pointer list-none items-center gap-2 text-sm font-semibold text-ink-600 hover:text-ink-900"
      >
        <span aria-hidden="true" class="text-base leading-none group-open:hidden">+</span>
        <span aria-hidden="true" class="hidden text-base leading-none group-open:inline">−</span>
        {{ moreLabel || "More options" }}
      </summary>
      <div class="flex flex-col gap-4 pt-3">
        <slot name="more" />
      </div>
    </details>
    <slot name="footer" />
  </section>
</template>
