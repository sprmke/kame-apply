<script setup lang="ts">
defineProps<{ name: string; phase: number }>();
const { t } = useI18n();
</script>

<template>
  <section class="mx-auto flex max-w-[880px] flex-col gap-3">
    <PageHeader :title="name" />
    <div class="relative overflow-hidden rounded-md border border-dashed border-edge p-8">
      <ContourBackdrop />
      <p class="relative font-serif text-lg text-ink-900">{{ t("placeholder.title") }}</p>
      <p class="relative mt-1 text-ink-600">{{ t("placeholder.phase", { n: phase }) }}</p>
    </div>
  </section>
</template>
