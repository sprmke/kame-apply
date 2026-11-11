<script setup lang="ts">
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from "reka-ui";

/** Inline evidence mark: dotted underline plus an index; opens the source fact or quote. */
defineProps<{ index: number; source: string; quote?: string; label?: string }>();
</script>

<template>
  <PopoverRoot>
    <PopoverTrigger
      class="cursor-help rounded-sm underline decoration-ink-600 decoration-dotted underline-offset-4 focus-visible:outline-2 focus-visible:outline-brand-700"
      :aria-label="label ?? `Evidence ${index}`"
    >
      <slot /><sup class="ml-0.5 font-mono text-[0.625rem] text-ink-600">{{ index }}</sup>
    </PopoverTrigger>
    <PopoverPortal>
      <PopoverContent
        :side-offset="6"
        class="z-50 max-w-xs rounded-md border border-rule bg-paper-1 p-3 text-sm shadow-float focus:outline-none"
      >
        <p v-if="quote" class="font-serif text-ink-900 italic">“{{ quote }}”</p>
        <p class="mt-1 text-xs text-ink-600">{{ source }}</p>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
