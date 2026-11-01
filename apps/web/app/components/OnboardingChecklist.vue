<script setup lang="ts">
import { listCredentialsApiV1AiCredentialsGet } from "@kame/api-client";
import { FnChip } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const ws = useWorkspaceStore();
const canSeeKeys = computed(() => ws.canManage);
const { data: creds } = useQuery({
  queryKey: computed(() => ["onboarding-credentials", ws.currentId]),
  queryFn: async () => (await listCredentialsApiV1AiCredentialsGet()).data,
  enabled: canSeeKeys,
});
const hasKey = computed(() => (creds.value?.length ?? 0) > 0);

// Profile, Track and Extension light up as their phases ship.
const steps = computed(() =>
  [
    { key: "ai", done: hasKey.value, to: "/settings/ai", soon: false, show: canSeeKeys.value },
    { key: "profile", done: false, to: "/profile/onboarding", soon: false, show: true },
    { key: "track", done: false, to: "/tracks", soon: false, show: true },
    { key: "extension", done: false, to: "/settings/integrations", soon: false, show: true },
  ].filter((s) => s.show),
);
</script>

<template>
  <section :aria-label="t('onboarding.title')" class="flex flex-col gap-3">
    <h2 class="font-serif text-lg font-semibold">{{ t("onboarding.title") }}</h2>
    <ol class="flex flex-col divide-y divide-rule border-y border-rule">
      <li v-for="(s, i) in steps" :key="s.key" class="flex min-h-14 items-center gap-3">
        <span
          class="grid size-6 shrink-0 place-items-center rounded-full border text-xs"
          :class="s.done ? 'border-fern-600 text-fern-600' : 'border-edge text-ink-600'"
          aria-hidden="true"
          >{{ s.done ? "✓" : i + 1 }}</span
        >
        <div class="min-w-0 flex-1">
          <NuxtLink
            v-if="!s.soon"
            :to="s.to"
            class="font-medium text-ink-900 underline-offset-2 hover:underline"
            >{{ t(`onboarding.${s.key}`) }}</NuxtLink
          >
          <span v-else class="font-medium text-ink-900">{{ t(`onboarding.${s.key}`) }}</span>
        </div>
        <FnChip v-if="s.soon">{{ t("onboarding.soon") }}</FnChip>
        <span v-else class="text-xs" :class="s.done ? 'text-ink-900' : 'text-ink-600'">
          {{ s.done ? t("onboarding.done") : t("onboarding.todo") }}
        </span>
      </li>
    </ol>
  </section>
</template>
