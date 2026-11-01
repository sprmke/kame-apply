<script setup lang="ts">
const props = defineProps<{ spentMicros: number; budgetCents: number }>();
const { t } = useI18n();
const fmt = useFormat();
const pct = computed(() =>
  props.budgetCents <= 0
    ? 100
    : Math.min(100, (props.spentMicros / (props.budgetCents * 10_000)) * 100),
);
const state = computed(() => (pct.value >= 100 ? "full" : pct.value >= 80 ? "near" : "ok"));
</script>

<template>
  <div class="flex flex-col gap-2">
    <p class="font-serif text-xl">
      {{ t("usage.of", { spent: fmt.usd(spentMicros), budget: fmt.usdCents(budgetCents) }) }}
    </p>
    <div
      class="h-2 overflow-hidden rounded-full border border-edge bg-paper-2"
      role="meter"
      :aria-valuenow="Math.round(pct)"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="t('usage.meter')"
    >
      <div
        class="h-full rounded-full"
        :class="state === 'ok' ? 'bg-ink-600' : 'bg-oxblood-600'"
        :style="{ width: `${pct}%` }"
      />
    </div>
    <p v-if="state !== 'ok'" class="flex gap-2 text-sm">
      <span class="text-oxblood-600" aria-hidden="true">{{ state === "full" ? "✕" : "!" }}</span
      >{{ state === "full" ? t("usage.full") : t("usage.near") }}
    </p>
  </div>
</template>
