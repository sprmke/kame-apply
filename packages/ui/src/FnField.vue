<script setup lang="ts">
import { computed, useId } from "vue";
import FnTooltip from "./FnTooltip.vue";

const props = defineProps<{
  label: string;
  hint?: string;
  /** One-sentence explanation behind a ? next to the label. Use when the label alone is ambiguous. */
  help?: string;
  error?: string | null;
  for?: string;
}>();
const uid = useId();
const inputId = computed(() => props.for ?? `f-${uid}`);
const hintId = computed(() => `${inputId.value}-hint`);
const errorId = computed(() => `${inputId.value}-error`);
const describedby = computed(
  () =>
    [props.hint ? hintId.value : null, props.error ? errorId.value : null]
      .filter(Boolean)
      .join(" ") || undefined,
);
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center gap-1.5">
      <label :for="inputId" class="text-sm font-semibold text-ink-900">{{ label }}</label>
      <FnTooltip v-if="help" :text="help" side="top">
        <button
          type="button"
          class="grid size-5 shrink-0 place-items-center rounded-full border border-rule text-[0.6875rem] font-semibold text-ink-600 hover:border-edge hover:bg-paper-2 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-500"
          :aria-label="help"
        >
          ?
        </button>
      </FnTooltip>
    </div>
    <slot :id="inputId" :describedby="describedby" :invalid="!!error" />
    <p v-if="hint" :id="hintId" class="text-sm text-ink-600">{{ hint }}</p>
    <p
      v-if="error"
      :id="errorId"
      role="alert"
      class="flex items-start gap-2 text-sm text-oxblood-600"
    >
      <span aria-hidden="true">✕</span><span>{{ error }}</span>
    </p>
  </div>
</template>
