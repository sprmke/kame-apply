<script setup lang="ts">
defineProps<{ title: string; lede?: string }>();
</script>

<template>
  <header class="mb-8 flex flex-wrap items-end justify-between gap-4">
    <div class="flex min-w-0 flex-col gap-2">
      <h1 class="text-3xl font-bold tracking-[-0.03em] text-ink-900 md:text-4xl">
        {{ title }}
      </h1>
      <p v-if="lede" class="max-w-2xl text-md text-ink-600">{{ lede }}</p>
    </div>
    <div v-if="$slots.actions" class="flex flex-wrap gap-2"><slot name="actions" /></div>
  </header>
</template>
