<script setup lang="ts">
defineProps<{ name: string; size?: number }>();
</script>

<template>
  <Icon :name="name" :size="size ?? 20" aria-hidden="true" />
</template>
