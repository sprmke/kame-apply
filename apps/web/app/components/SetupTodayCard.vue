<script setup lang="ts">
import {
  openSetupApiV1OnboardingSetupsGet,
  getProvenanceApiV1OnboardingSetupsProvenanceGet,
  revertSetupApiV1OnboardingSetupsDraftIdRevertPost,
} from "@kame/api-client";
import { FnButton, FnChip, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const { profileId } = useActiveProfile();

const enabled = computed(() => Boolean(ws.currentId && profileId.value));
const open = useQuery({
  queryKey: computed(() => ["today-setup-open", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data } = await openSetupApiV1OnboardingSetupsGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled,
});
const provenance = useQuery({
  queryKey: computed(() => ["today-setup-provenance", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data } = await getProvenanceApiV1OnboardingSetupsProvenanceGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled,
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
    dismissed.value = localStorage.getItem(`kame.setupDone.${row.draft_id}`) === "1";
  },
  { immediate: true },
);

function dismiss() {
  if (!recent.value || !import.meta.client) return;
  localStorage.setItem(`kame.setupDone.${recent.value.draft_id}`, "1");
  dismissed.value = true;
}

async function undo() {
  const row = recent.value;
  if (!row || !window.confirm(t("setup.undoConfirm"))) return;
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
    class="flex flex-col gap-2 rounded-xl border border-brand-200 bg-brand-50 p-4 md:p-5"
    aria-labelledby="finish-setup-title"
  >
    <div class="flex flex-wrap items-center gap-2">
      <h2 id="finish-setup-title" class="text-lg font-bold text-ink-900">
        {{ t("setup.finishTitle") }}
      </h2>
      <FnChip tone="accent">{{ t("setup.finishChip") }}</FnChip>
    </div>
    <p class="text-sm text-ink-600">{{ t("setup.finishBody") }}</p>
    <div>
      <FnButton tone="primary" as-child>
        <NuxtLink :to="`/start?setup=${open.data.value.id}`">{{
          t("setup.finishAction")
        }}</NuxtLink>
      </FnButton>
    </div>
  </section>

  <section
    v-else-if="recent && !dismissed"
    class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    aria-labelledby="setup-done-title"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-2">
        <h2 id="setup-done-title" class="text-lg font-bold text-ink-900">
          {{ t("setup.doneCardTitle") }}
        </h2>
        <FnChip>{{ t("setup.doneChip") }}</FnChip>
      </div>
      <FnButton tone="ghost" @click="dismiss">{{ t("setup.donePanelDismiss") }}</FnButton>
    </div>
    <p class="text-sm text-ink-600">{{ t("setup.doneCardBody") }}</p>
    <div class="flex flex-wrap gap-2">
      <FnButton tone="quiet" as-child>
        <NuxtLink to="/profile">{{ t("setup.donePage.profile") }}</NuxtLink>
      </FnButton>
      <FnButton tone="quiet" as-child>
        <NuxtLink to="/profile/answers">{{ t("setup.donePage.answers") }}</NuxtLink>
      </FnButton>
      <FnButton tone="quiet" as-child>
        <NuxtLink to="/tracks">{{ t("setup.donePage.searches") }}</NuxtLink>
      </FnButton>
      <FnButton tone="quiet" as-child>
        <NuxtLink to="/studio">{{ t("setup.donePage.studio") }}</NuxtLink>
      </FnButton>
      <FnButton tone="ghost" :loading="undoing" @click="undo">{{ t("setup.undo") }}</FnButton>
    </div>
  </section>
</template>
