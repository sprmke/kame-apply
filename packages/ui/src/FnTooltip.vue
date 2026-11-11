<script setup lang="ts">
import {
  TooltipContent,
  TooltipPortal,
  TooltipProvider,
  TooltipRoot,
  TooltipTrigger,
} from "reka-ui";

defineProps<{ text: string; side?: "top" | "right" | "bottom" | "left" }>();
</script>

<template>
  <TooltipProvider :delay-duration="300">
    <TooltipRoot>
      <TooltipTrigger as-child><slot /></TooltipTrigger>
      <TooltipPortal>
        <TooltipContent
          :side="side ?? 'right'"
          :side-offset="8"
          class="z-50 rounded-md bg-ink-900 px-3 py-1.5 text-sm text-paper-0 shadow-[var(--shadow-float)]"
        >
          {{ text }}
        </TooltipContent>
      </TooltipPortal>
    </TooltipRoot>
  </TooltipProvider>
</template>
