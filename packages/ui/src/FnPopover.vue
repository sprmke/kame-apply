<script setup lang="ts">
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from "reka-ui";

defineProps<{ side?: "top" | "right" | "bottom" | "left" }>();
</script>

<template>
  <PopoverRoot>
    <PopoverTrigger as-child><slot name="trigger" /></PopoverTrigger>
    <PopoverPortal>
      <PopoverContent
        :side="side ?? 'bottom'"
        :side-offset="6"
        class="z-50 max-w-xs rounded-xl border border-rule bg-paper-1 p-4 text-sm text-ink-900 shadow-[var(--shadow-float)] focus:outline-none"
      >
        <slot />
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
