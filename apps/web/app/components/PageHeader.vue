<script setup lang="ts">
defineProps<{ title: string; lede?: string; eyebrow?: string }>();
</script>

<template>
  <header class="mb-6 flex flex-col gap-4 md:mb-8">
    <div class="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
      <div class="flex min-w-0 flex-col gap-1.5">
        <p v-if="eyebrow" class="text-xs font-semibold tracking-[0.12em] text-ink-400 uppercase">
          {{ eyebrow }}
        </p>
        <h1
          class="text-2xl leading-tight font-bold tracking-[-0.03em] text-ink-900 sm:text-3xl md:text-4xl"
        >
          {{ title }}
        </h1>
        <p v-if="lede" class="max-w-2xl text-base leading-6 text-ink-600">{{ lede }}</p>
      </div>
      <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2 sm:justify-end">
        <slot name="actions" />
      </div>
    </div>
    <slot />
  </header>
</template>
