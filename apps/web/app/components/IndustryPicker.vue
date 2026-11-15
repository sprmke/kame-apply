<script setup lang="ts">
import type { IndustrySummary } from "@kame/api-client";

const props = withDefaults(
  defineProps<{
    industries: (IndustrySummary & { draft?: boolean })[];
    selected: string[];
    primary: string | null;
    max?: number;
    disabled?: boolean;
  }>(),
  { max: 2, disabled: false },
);
const emit = defineEmits<{
  "update:selected": [value: string[]];
  "update:primary": [value: string | null];
}>();

const { t, te } = useI18n();

function label(industry: IndustrySummary): string {
  if (industry.label) return industry.label;
  return te(industry.label_key) ? t(industry.label_key) : industry.key;
}

function shortLabel(industry: IndustrySummary & { draft?: boolean }): string {
  const full = label(industry);
  if (!industry.draft) return full;
  const words = full.split(/\s+/).filter(Boolean);
  return words.length > 5 ? `${words.slice(0, 5).join(" ")}…` : full;
}

function families(industry: IndustrySummary): string {
  return (industry.role_families ?? [])
    .slice(0, 3)
    .map((family) => (te(family.label_key) ? t(family.label_key) : family.key))
    .join(" · ");
}

function isSelected(key: string): boolean {
  return props.selected.includes(key);
}

function atLimit(key: string): boolean {
  return !isSelected(key) && props.selected.length >= props.max;
}

function toggle(key: string) {
  if (props.disabled) return;
  let next: string[];
  if (isSelected(key)) {
    next = props.selected.filter((item) => item !== key);
  } else {
    if (atLimit(key)) return;
    next = [...props.selected, key];
  }
  emit("update:selected", next);
  if (!props.primary || !next.includes(props.primary)) {
    emit("update:primary", next[0] ?? null);
  }
}
</script>

<template>
  <div
    class="grid min-w-0 gap-2 sm:grid-cols-2"
    role="group"
    :aria-label="t('workspace.pickField')"
  >
    <button
      v-for="industry in industries"
      :key="industry.key"
      type="button"
      class="group flex min-h-16 min-w-0 items-center gap-3 rounded-xl border bg-paper-0 px-3 py-2.5 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-50"
      :class="
        isSelected(industry.key)
          ? 'border-brand-500 bg-brand-50'
          : 'border-edge hover:border-brand-200 hover:bg-brand-50/60'
      "
      :aria-label="industry.draft ? `${label(industry)}, draft` : label(industry)"
      :aria-pressed="isSelected(industry.key)"
      :disabled="disabled || atLimit(industry.key)"
      @click="toggle(industry.key)"
    >
      <span
        class="grid size-10 shrink-0 place-items-center rounded-lg"
        :class="
          isSelected(industry.key) ? 'bg-brand-100 text-brand-700' : 'bg-paper-2 text-ink-600'
        "
      >
        <Icon :name="industry.icon" :size="20" aria-hidden="true" />
      </span>
      <span class="min-w-0 flex-1">
        <span class="flex min-w-0 flex-wrap items-center gap-1.5">
          <span
            class="text-sm font-semibold text-ink-900"
            :class="industry.draft ? 'w-full text-pencil' : 'min-w-0 truncate'"
            :title="label(industry)"
            >{{ shortLabel(industry) }}</span
          >
          <span
            v-if="industry.draft"
            class="rounded-full bg-paper-2 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-ink-600 uppercase"
            >{{ t("workspace.draftBadge") }}</span
          >
          <span
            v-if="industry.key === primary && isSelected(industry.key)"
            class="rounded-full bg-brand-100 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-brand-700 uppercase"
            >{{ t("workspace.primaryField") }}</span
          >
        </span>
        <span
          v-if="families(industry)"
          class="mt-0.5 block truncate text-xs text-ink-600"
          :title="families(industry)"
          >{{ families(industry) }}</span
        >
      </span>
      <Icon
        v-if="isSelected(industry.key)"
        name="ph:check-circle-fill"
        :size="18"
        class="shrink-0 text-brand-600"
        aria-hidden="true"
      />
    </button>
  </div>
</template>
