<script setup lang="ts">
import {
  getOpenSetupApiV1OnboardingSetupsGet,
  getSetupProvenanceApiV1OnboardingSetupsProvenanceGet,
  revertSetupApiV1OnboardingSetupsDraftIdRevertPost,
} from "@kame/api-client";
import { FnButton, FnChip, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useActiveProfile } from "~/composables/useActiveProfile";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const qc = useQueryClient();
const { profileId } = useActiveProfile();

const open = useQuery({
  queryKey: computed(() => ["today-setup-open", profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data } = await getOpenSetupApiV1OnboardingSetupsGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(profileId.value)),
});

const provenance = useQuery({
  queryKey: computed(() => ["today-setup-provenance", profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data } = await getSetupProvenanceApiV1OnboardingSetupsProvenanceGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(profileId.value)),
});

const dismissed = ref(false);
const undoing = ref(false);
const recent = computed(() => {
  const row = provenance.data.value;
  if (!row) return null;
  const age = Date.now() - new Date(row.applied_at).getTime();
  return age <= 7 * 86_400_000 ? row : null;
});

watch(
  recent,
  (row) => {
    if (!row || !import.meta.client) return;
    dismissed.value = localStorage.getItem(`kame.setupCard.${row.draft_id}`) === "1";
  },
  { immediate: true },
);

function dismiss() {
  if (!recent.value || !import.meta.client) return;
  localStorage.setItem(`kame.setupCard.${recent.value.draft_id}`, "1");
  dismissed.value = true;
}

async function undo() {
  const row = recent.value;
  if (!row) return;
  if (!window.confirm(t("setup.undoConfirm"))) return;
  undoing.value = true;
  try {
    await revertSetupApiV1OnboardingSetupsDraftIdRevertPost({
      path: { draft_id: row.draft_id },
      throwOnError: true,
    });
    await qc.invalidateQueries();
    toast.push({ title: t("setup.undone"), tone: "success" });
    dismissed.value = true;
  } catch (error) {
    toast.push({ title: apiError(error), tone: "danger" });
  } finally {
    undoing.value = false;
  }
}
</script>

<template>
  <section
    v-if="open.data.value"
    class="flex flex-col gap-2 rounded-xl border border-brand-200 bg-brand-50 p-4"
  >
    <div class="flex flex-wrap items-center gap-2">
      <h2 class="text-lg font-bold text-ink-900">{{ t("setup.openTitle") }}</h2>
      <FnChip tone="accent">{{ t("setup.openChip") }}</FnChip>
    </div>
    <p class="text-sm text-ink-600">{{ t("setup.openBody") }}</p>
    <div>
      <FnButton tone="quiet" as-child>
        <NuxtLink :to="`/start?setup=${open.data.value.id}`">{{ t("setup.openAction") }}</NuxtLink>
      </FnButton>
    </div>
  </section>

  <section
    v-else-if="recent && !dismissed"
    class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-2">
        <h2 class="text-lg font-bold text-ink-900">{{ t("setup.doneTitle") }}</h2>
        <FnChip>{{ t("setup.doneChip") }}</FnChip>
      </div>
      <FnButton tone="ghost" @click="dismiss">{{ t("setup.doneDismiss") }}</FnButton>
    </div>
    <p class="text-sm text-ink-600">{{ t("setup.doneBody") }}</p>
    <div class="flex flex-wrap gap-2">
      <FnButton tone="quiet" as-child>
        <NuxtLink to="/profile">{{ t("setup.doneProfile") }}</NuxtLink>
      </FnButton>
      <FnButton tone="quiet" as-child>
        <NuxtLink to="/profile/answers">{{ t("setup.doneAnswers") }}</NuxtLink>
      </FnButton>
      <FnButton tone="quiet" as-child>
        <NuxtLink to="/tracks">{{ t("setup.doneSearches") }}</NuxtLink>
      </FnButton>
      <FnButton tone="quiet" as-child>
        <NuxtLink to="/studio">{{ t("setup.doneStudio") }}</NuxtLink>
      </FnButton>
      <FnButton tone="ghost" :loading="undoing" @click="undo">{{ t("setup.undo") }}</FnButton>
    </div>
  </section>
</template>
