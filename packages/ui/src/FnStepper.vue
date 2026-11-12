<script setup lang="ts">
export type Step = { key: string; label: string };

/** Linear multi-step shell. Emits the step key; the page decides whether it may jump. */
withDefaults(
  defineProps<{
    steps: Step[];
    modelValue: string;
    label: string;
    clickable?: boolean;
    /** Completed steps before the current one. Defaults to the current index. */
    doneBefore?: number;
  }>(),
  { clickable: false, doneBefore: undefined },
);
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
</script>

<template>
  <nav :aria-label="label">
    <ol class="flex gap-1 overflow-x-auto rounded-lg bg-paper-2 p-1">
      <li v-for="(step, i) in steps" :key="step.key" class="shrink-0">
        <button
          type="button"
          class="flex min-h-11 items-center gap-1.5 rounded-md px-2 text-xs font-semibold whitespace-nowrap transition-colors sm:gap-2 sm:px-3 sm:text-sm"
          :class="
            step.key === modelValue
              ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
              : 'text-ink-600 hover:text-ink-900'
          "
          :aria-current="step.key === modelValue ? 'step' : undefined"
          :aria-label="step.label"
          :disabled="!clickable && step.key !== modelValue"
          @click="emit('update:modelValue', step.key)"
        >
          <span
            class="grid size-5 shrink-0 place-items-center rounded-full text-[0.6875rem] tabular-nums"
            :class="
              step.key === modelValue
                ? 'bg-brand-700 text-on-brand'
                : i < (doneBefore ?? steps.findIndex((s) => s.key === modelValue))
                  ? 'bg-fern-600 text-paper-1'
                  : 'bg-paper-1 text-ink-600'
            "
            >{{ i + 1 }}</span
          >
          <span :class="step.key === modelValue ? '' : 'hidden lg:inline'">{{ step.label }}</span>
        </button>
      </li>
    </ol>
  </nav>
</template>
