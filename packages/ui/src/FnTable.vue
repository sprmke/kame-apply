<script setup lang="ts" generic="T extends Record<string, unknown>">
export type Column = { key: string; label: string; align?: "left" | "right"; mono?: boolean };

defineProps<{
  columns: Column[];
  rows: T[];
  rowKey: keyof T & string;
  caption: string;
  density?: "comfortable" | "compact";
  empty?: string;
}>();
</script>

<template>
  <div class="overflow-x-auto rounded-md border border-rule">
    <table class="w-full border-collapse text-left text-sm">
      <caption class="sr-only">
        {{
          caption
        }}
      </caption>
      <thead class="bg-paper-2 text-xs text-ink-600">
        <tr>
          <th
            v-for="c in columns"
            :key="c.key"
            scope="col"
            class="px-3 py-2 font-medium"
            :class="c.align === 'right' ? 'text-right' : ''"
          >
            {{ c.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!rows.length">
          <td :colspan="columns.length" class="px-3 py-8 text-center text-ink-600">{{ empty }}</td>
        </tr>
        <tr v-for="r in rows" :key="String(r[rowKey])" class="border-t border-rule">
          <td
            v-for="c in columns"
            :key="c.key"
            class="px-3 align-middle"
            :class="[
              density === 'compact' ? 'h-8' : 'h-12',
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
