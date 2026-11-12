<script setup lang="ts">
import { useId } from "vue";

/** One consistent disclosure for advanced controls. Basic first, advanced folded. */
withDefaults(defineProps<{ label?: string; open?: boolean }>(), { label: "More options" });
const uid = useId();
</script>

<template>
  <details :open="open" class="group border-t border-rule pt-3">
    <summary
      class="flex min-h-11 cursor-pointer list-none items-center gap-2 text-sm font-semibold text-ink-600 hover:text-ink-900"
      :aria-controls="`more-${uid}`"
    >
      <span aria-hidden="true" class="text-base leading-none group-open:hidden">+</span>
      <span aria-hidden="true" class="hidden text-base leading-none group-open:inline">−</span>
      {{ label }}
    </summary>
    <div :id="`more-${uid}`" class="flex flex-col gap-4 pt-3">
      <slot />
    </div>
  </details>
</template>
