<script setup lang="ts">
import { FnToaster } from "@kame/ui";

const { t } = useI18n();
useTheme();
</script>

<template>
  <div class="flex min-h-dvh items-center justify-center bg-paper-0 px-4 py-10 text-ink-900">
    <div
      class="w-full max-w-md rounded-2xl border border-rule bg-paper-1 p-7 shadow-[var(--shadow-float)] md:p-9"
    >
      <NuxtLink to="/" class="inline-flex" :aria-label="t('app.name')"
        ><BrandMark wordmark
      /></NuxtLink>
      <main id="main" tabindex="-1" class="mt-8 focus:outline-none"><slot /></main>
    </div>
    <FnToaster :dismiss-label="t('common.dismiss')" />
  </div>
</template>
