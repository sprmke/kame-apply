<script setup lang="ts">
import { useId } from "vue";

export type ChoiceCard = {
  value: string;
  title: string;
  /** One line stating what this choice does. */
  effect?: string;
  /** Short badge such as Recommended or Advanced. */
  badge?: string;
  disabled?: boolean;
};

const props = defineProps<{
  modelValue: string;
  options: ChoiceCard[];
  /** Accessible name for the group. */
  label: string;
  name?: string;
  columns?: 1 | 2;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
const uid = useId();
const groupName = props.name ?? `choice-${uid}`;
</script>

<template>
  <fieldset class="flex flex-col gap-2">
    <legend class="sr-only">{{ label }}</legend>
    <div class="grid gap-2" :class="columns === 2 ? 'sm:grid-cols-2' : ''">
      <label
        v-for="opt in options"
        :key="opt.value"
        class="flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors sm:p-4"
        :class="[
          modelValue === opt.value
            ? 'border-brand-500 bg-brand-50'
            : 'border-rule bg-paper-1 hover:border-edge',
          opt.disabled ? 'pointer-events-none opacity-50' : '',
        ]"
      >
        <input
          :id="`${groupName}-${opt.value}`"
          type="radio"
          class="mt-1 size-4 shrink-0 accent-brand-600"
          :name="groupName"
          :value="opt.value"
          :checked="modelValue === opt.value"
          :disabled="opt.disabled"
          @change="emit('update:modelValue', opt.value)"
        />
        <span class="flex min-w-0 flex-col gap-1">
          <span class="flex flex-wrap items-center gap-2">
            <span class="text-sm font-semibold text-ink-900">{{ opt.title }}</span>
            <span
              v-if="opt.badge"
              class="rounded-full bg-brand-100 px-2 py-0.5 text-[0.6875rem] font-semibold text-brand-700"
            >{{ opt.badge }}</span>
          </span>
          <span v-if="opt.effect" class="text-sm leading-5 text-ink-600">{{ opt.effect }}</span>
        </span>
      </label>
    </div>
  </fieldset>
</template>
