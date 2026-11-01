<script setup lang="ts">
import { FnToaster } from "@kame/ui";

const { t } = useI18n();
useTheme();
</script>

<template>
  <div
    class="relative flex min-h-dvh flex-col items-center overflow-hidden bg-paper-0 px-4 py-10 text-ink-900"
  >
    <ContourBackdrop />
    <div class="relative z-10 flex w-full max-w-sm flex-1 flex-col justify-center gap-8">
      <NuxtLink to="/" class="self-start" :aria-label="t('app.name')"
        ><BrandMark wordmark
      /></NuxtLink>
      <main id="main" tabindex="-1" class="focus:outline-none"><slot /></main>
    </div>
    <FnToaster :dismiss-label="t('common.dismiss')" />
  </div>
</template>
