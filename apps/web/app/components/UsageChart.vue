<script setup lang="ts">
import type { UsageDay } from "@kame/api-client";

const props = defineProps<{ days: UsageDay[]; caption: string }>();
const { t } = useI18n();
const fmt = useFormat();
const showTable = ref(false);
const max = computed(() => Math.max(1, ...props.days.map((d) => d.cost_micros)));
</script>

<template>
  <figure class="flex flex-col gap-2">
    <figcaption class="flex items-center justify-between gap-3 text-sm text-ink-600">
      <span>{{ caption }}</span>
      <button
        type="button"
        class="min-h-11 text-brand-700 underline underline-offset-2"
        :aria-pressed="showTable"
        @click="showTable = !showTable"
      >
        {{ showTable ? t("usage.showChart") : t("usage.showTable") }}
      </button>
    </figcaption>
    <p
      v-if="!days.length"
      class="rounded-md border border-dashed border-edge p-6 text-center text-sm text-ink-600"
    >
      {{ t("usage.none") }}
    </p>
    <table v-else-if="showTable" class="w-full text-left text-sm">
      <thead class="text-xs text-ink-600">
        <tr>
          <th scope="col" class="py-1">{{ t("usage.day") }}</th>
          <th scope="col" class="py-1 text-right">{{ t("usage.calls") }}</th>
          <th scope="col" class="py-1 text-right">{{ t("usage.cost") }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in days" :key="d.day" class="border-t border-rule">
          <td class="py-1.5">{{ fmt.date(d.day) }}</td>
          <td class="py-1.5 text-right tabular-nums">{{ d.calls }}</td>
          <td class="py-1.5 text-right tabular-nums">{{ fmt.usd(d.cost_micros) }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="flex h-32 items-end gap-1" role="img" :aria-label="caption">
      <div
        v-for="d in days"
        :key="d.day"
        class="flex-1 rounded-t-sm bg-brand-500"
        :style="{ height: `${Math.max(4, (d.cost_micros / max) * 100)}%` }"
        :title="`${fmt.date(d.day)}: ${fmt.usd(d.cost_micros)}`"
      />
    </div>
  </figure>
</template>
