<script setup lang="ts">
import { FnSkeleton } from "@kame/ui";

/**
 * Mirrors `FnTable`: a recessed header and fixed-height rows on desktop; with `stack`, labelled
 * cards on phones. Column widths are even, which is close enough for a table that loads in place.
 */
withDefaults(
  defineProps<{
    columns: number;
    rows?: number;
    /** Collapses to cards under 640px, like the real table. */
    stack?: boolean;
    compact?: boolean;
    /** Border and white surface around the table. */
    framed?: boolean;
    /** Minimum table width, for tables that scroll sideways on phones. */
    minWidth?: string;
  }>(),
  { rows: 5, stack: false, compact: false, framed: true, minWidth: "" },
);
</script>

<template>
  <div
    :class="
      framed
        ? 'overflow-hidden rounded-lg border border-rule bg-paper-1 shadow-[var(--shadow-card)]'
        : ''
    "
  >
    <!-- Phone cards, only when the real table stacks. -->
    <ul v-if="stack" class="flex flex-col divide-y divide-rule sm:hidden">
      <li v-for="r in rows" :key="`m-${r}`" class="flex flex-col gap-2 px-4 py-3">
        <div class="flex items-center justify-between gap-3">
          <FnSkeleton class="h-4 w-2/5" />
          <FnSkeleton class="h-7 w-20 rounded-full" />
        </div>
        <FnSkeleton class="h-3.5 w-3/5" />
      </li>
    </ul>

    <div :class="stack ? 'hidden sm:block' : 'overflow-x-auto'">
      <table
        class="w-full border-collapse text-left text-sm"
        :style="minWidth ? { minWidth } : undefined"
      >
        <thead class="bg-paper-2">
          <tr>
            <th v-for="c in columns" :key="c" class="px-4 py-3" scope="col">
              <FnSkeleton class="h-3 w-16 bg-paper-1" />
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r" class="border-t border-rule">
            <td
              v-for="c in columns"
              :key="c"
              class="px-4 align-middle"
              :class="compact ? 'h-10' : 'h-14'"
            >
              <FnSkeleton class="h-4" :class="c === 1 ? 'w-3/4' : 'w-1/2'" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
