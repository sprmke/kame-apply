<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ components?: Record<string, unknown> | null }>();

const { t } = useI18n();

const LABELS: Record<string, string> = {
  title: t("jobs.signal_title"),
  skills: t("jobs.signal_skills"),
  seniority: t("jobs.signal_seniority"),
  salary: t("jobs.signal_salary"),
  freshness: t("jobs.signal_freshness"),
  location: t("jobs.signal_location"),
  semantic: t("jobs.signal_description"),
  llm: t("jobs.signal_ai"),
};

const rows = computed(() =>
  Object.entries(props.components ?? {})
    .filter(([key, value]) => key in LABELS && typeof value === "number" && Number.isFinite(value))
    .map(([key, value]) => ({
      key,
      label: LABELS[key]!,
      value: Math.max(0, Math.min(100, Math.round(value as number))),
    }))
    .sort((a, b) => b.value - a.value),
);
</script>

<template>
  <details v-if="rows.length" class="group">
    <summary
      class="flex min-h-11 cursor-pointer list-none items-center justify-between gap-2 text-sm font-semibold text-ink-900 [&::-webkit-details-marker]:hidden"
    >
      {{ t("jobs.whyScore") }}
      <NavIcon
        name="ph:caret-down"
        :size="14"
        class="text-ink-400 transition-transform group-open:rotate-180"
      />
    </summary>
    <ul class="mt-2 flex flex-col gap-2.5">
      <li v-for="row in rows" :key="row.key">
        <div class="flex items-baseline justify-between gap-2 text-xs">
          <span class="text-ink-600">{{ row.label }}</span>
          <span class="font-semibold tabular-nums text-ink-900">{{ row.value }}</span>
        </div>
        <div class="mt-1 h-1.5 overflow-hidden rounded-full bg-paper-2" aria-hidden="true">
          <div class="h-full rounded-full bg-ink-600" :style="{ width: `${row.value}%` }" />
        </div>
      </li>
    </ul>
    <p class="mt-3 text-xs text-ink-400">{{ t("jobs.scoreNote") }}</p>
  </details>
</template>
