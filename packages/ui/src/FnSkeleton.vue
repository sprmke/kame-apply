<script setup lang="ts">
defineProps<{ lines?: number }>();
</script>

<template>
  <div class="flex flex-col gap-2" aria-hidden="true">
    <div
      v-for="n in lines ?? 1"
      :key="n"
      class="h-4 animate-pulse rounded-sm bg-paper-2 motion-reduce:animate-none"
      :style="{ width: n === (lines ?? 1) && (lines ?? 1) > 1 ? '60%' : '100%' }"
    />
  </div>
</template>
