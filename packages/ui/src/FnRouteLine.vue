<script setup lang="ts">
/** Progress as a path: completed waypoints in ink, the active one in brand, future dotted. */
const props = defineProps<{ steps: string[]; active: number; label: string }>();
const stateOf = (i: number) => (i < props.active ? "done" : i === props.active ? "active" : "todo");
</script>

<template>
  <ol class="flex items-center" :aria-label="label">
    <li
      v-for="(s, i) in steps"
      :key="s"
      class="flex min-w-0 flex-1 items-center last:flex-none"
      :aria-current="stateOf(i) === 'active' ? 'step' : undefined"
    >
      <span class="flex flex-col items-start gap-1">
        <span
          class="size-3 rounded-full border-2"
          :class="{
            'border-ink-900 bg-ink-900': stateOf(i) === 'done',
            'border-brand-500 bg-brand-500': stateOf(i) === 'active',
            'border-ink-400 bg-paper-0': stateOf(i) === 'todo',
          }"
        />
        <span
          class="text-xs"
          :class="stateOf(i) === 'todo' ? 'text-ink-600' : 'font-medium text-ink-900'"
        >
          {{ s }}
          <span class="sr-only">{{ stateOf(i) }}</span>
        </span>
      </span>
      <span
        v-if="i < steps.length - 1"
        class="mx-2 mb-5 h-0.5 min-w-4 flex-1 border-t-2"
        :class="i < active ? 'border-ink-900' : 'border-dotted border-ink-400'"
        aria-hidden="true"
      />
    </li>
  </ol>
</template>
