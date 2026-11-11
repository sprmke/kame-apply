<script setup lang="ts">
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "reka-ui";

export type MenuItem =
  | { type: "separator" }
  | { type?: "item"; label: string; tone?: "danger"; disabled?: boolean; onSelect: () => void };

defineProps<{
  items: MenuItem[];
  align?: "start" | "center" | "end";
  side?: "top" | "right" | "bottom" | "left";
}>();
</script>

<template>
  <DropdownMenuRoot>
    <DropdownMenuTrigger as-child><slot /></DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent
        :align="align ?? 'end'"
        :side="side ?? 'bottom'"
        :side-offset="6"
        class="z-50 min-w-48 rounded-lg border border-rule bg-paper-1 p-1.5 shadow-[var(--shadow-float)]"
      >
        <template v-for="(it, i) in items" :key="i">
          <DropdownMenuSeparator v-if="it.type === 'separator'" class="my-1 h-px bg-rule" />
          <DropdownMenuItem
            v-else
            :disabled="it.disabled"
            class="flex min-h-11 cursor-pointer items-center rounded-md px-3 text-sm font-medium outline-none data-[disabled]:opacity-50 data-[highlighted]:bg-paper-2"
            :class="it.tone === 'danger' ? 'text-oxblood-600' : 'text-ink-900'"
            @select="it.onSelect()"
          >
            {{ it.label }}
          </DropdownMenuItem>
        </template>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>
