<script setup lang="ts">
defineProps<{ title: string; lede?: string }>();
</script>

<template>
  <header class="mb-6 flex flex-wrap items-end justify-between gap-3">
    <div class="flex flex-col gap-1">
      <h1 class="font-serif text-2xl font-semibold text-ink-900 md:text-[length:var(--text-2xl)]">
        {{ title }}
      </h1>
      <p v-if="lede" class="max-w-prose text-ink-600">{{ lede }}</p>
    </div>
    <div v-if="$slots.actions" class="flex gap-2"><slot name="actions" /></div>
  </header>
</template>
