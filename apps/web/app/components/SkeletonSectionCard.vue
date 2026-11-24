<script setup lang="ts">
import { FnSkeleton } from "@kame/ui";

/** Shell of `FnSectionCard` while its data loads: same border, padding, title, and intro space. */
withDefaults(
  defineProps<{
    /** Reserve room for a title and an intro line. */
    headed?: boolean;
    /** Reserve room for the intro line under the title. */
    intro?: boolean;
    /** Reserve room for one action control at the top right. */
    action?: boolean;
    tone?: "plain" | "quiet";
  }>(),
  { headed: true, intro: true, action: false, tone: "plain" },
);
</script>

<template>
  <section
    class="flex flex-col gap-4 rounded-xl border border-rule p-4 sm:p-5 md:p-6"
    :class="tone === 'quiet' ? 'bg-paper-0 shadow-none' : 'bg-paper-1 shadow-[var(--shadow-card)]'"
  >
    <div v-if="headed" class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
      <div class="flex min-w-0 flex-1 flex-col gap-2">
        <FnSkeleton class="h-6 w-40" />
        <FnSkeleton v-if="intro" class="h-3.5 w-full max-w-md" />
      </div>
      <FnSkeleton v-if="action" class="h-11 w-24 shrink-0 rounded-md" />
    </div>
    <slot />
  </section>
</template>
