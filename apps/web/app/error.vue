<script setup lang="ts">
import { FnButton } from "@kame/ui";
import type { NuxtError } from "#app";

const props = defineProps<{ error: NuxtError }>();
const { t } = useI18n();
const notFound = computed(() => props.error.statusCode === 404);
useTheme();
</script>

<template>
  <div class="grid min-h-dvh place-items-center bg-paper-0 px-4 text-ink-900">
    <div class="flex max-w-md flex-col items-start gap-4">
      <BrandMark />
      <h1 class="font-serif text-2xl font-semibold">
        {{ notFound ? t("error.notFoundTitle") : t("error.title") }}
      </h1>
      <p class="text-ink-600">{{ notFound ? t("error.notFoundBody") : t("error.body") }}</p>
      <FnButton tone="primary" @click="clearError({ redirect: '/' })">{{
        t("error.home")
      }}</FnButton>
    </div>
  </div>
</template>
