<script setup lang="ts" generic="T extends Record<string, unknown>">
export type Column = { key: string; label: string; align?: "left" | "right"; mono?: boolean };

defineProps<{
  columns: Column[];
  rows: T[];
  rowKey: keyof T & string;
  caption: string;
  density?: "comfortable" | "compact";
  empty?: string;
  flat?: boolean;
}>();
</script>

<template>
  <div
    class="overflow-x-auto"
    :class="flat ? '' : 'rounded-lg border border-rule bg-paper-1 shadow-[var(--shadow-card)]'"
  >
    <table class="w-full border-collapse text-left text-sm">
      <caption class="sr-only">
        {{
          caption
        }}
      </caption>
      <thead class="bg-paper-2 text-xs font-semibold tracking-wide text-ink-600 uppercase">
        <tr>
          <th
            v-for="c in columns"
            :key="c.key"
            scope="col"
            class="px-4 py-3 font-semibold"
            :class="c.align === 'right' ? 'text-right' : ''"
          >
            {{ c.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!rows.length">
          <td :colspan="columns.length" class="px-4 py-10 text-center text-ink-600">{{ empty }}</td>
        </tr>
        <tr
          v-for="r in rows"
          :key="String(r[rowKey])"
          class="border-t border-rule transition-colors hover:bg-paper-2/50"
        >
          <td
            v-for="c in columns"
            :key="c.key"
            class="px-4 align-middle"
            :class="[
              density === 'compact' ? 'h-10' : 'h-14',
              c.align === 'right' ? 'text-right tabular-nums' : '',
              c.mono ? 'font-mono text-xs' : '',
            ]"
          >
            <slot :name="`cell-${c.key}`" :row="r" :value="r[c.key]">{{ r[c.key] }}</slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
