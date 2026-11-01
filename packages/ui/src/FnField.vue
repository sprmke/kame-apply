<script setup lang="ts">
import { computed, useId } from "vue";

const props = defineProps<{ label: string; hint?: string; error?: string | null; for?: string }>();
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
  <div class="flex flex-col gap-1.5">
    <label :for="inputId" class="text-sm font-medium text-ink-900">{{ label }}</label>
    <slot :id="inputId" :describedby="describedby" :invalid="!!error" />
    <p v-if="hint" :id="hintId" class="text-xs text-ink-600">{{ hint }}</p>
    <p
      v-if="error"
      :id="errorId"
      role="alert"
      class="flex items-start gap-1.5 text-xs text-oxblood-600"
    >
      <span aria-hidden="true">✕</span><span class="text-ink-900">{{ error }}</span>
    </p>
  </div>
</template>
