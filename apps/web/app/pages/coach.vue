<script setup lang="ts">
import { client } from "@kame/api-client";
import { FnButton, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { useWorkspaceStore } from "~/stores/workspace";

type CoachRow = {
  id: string;
  display_name: string;
  headline: string | null;
  is_default: boolean;
  application_count: number;
};

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const { selectProfile } = useActiveProfile();
const creating = ref(false);
const newName = ref("");

const coach = useQuery({
  queryKey: computed(() => ["coach-profiles", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({ url: "/api/v1/coach/profiles", throwOnError: true });
    return data as CoachRow[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

async function openProfile(id: string) {
  selectProfile(id);
  await navigateTo("/profile");
}

async function addProfile() {
  const name = newName.value.trim();
  if (!name) return;
  creating.value = true;
  try {
    const { data } = await client.post({
      url: "/api/v1/profiles",
      body: { display_name: name },
      throwOnError: true,
    });
    selectProfile((data as { id: string }).id);
    newName.value = "";
    await qc.invalidateQueries({ queryKey: ["coach-profiles", ws.currentId] });
    await qc.invalidateQueries({ queryKey: ["profiles", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    creating.value = false;
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-6">
    <h1 class="font-serif text-2xl font-semibold text-ink-900">{{ t("coach.title") }}</h1>

    <div v-if="coach.isPending.value"><FnSkeleton class="h-32 w-full" /></div>
    <ul v-else class="divide-y divide-rule border-y border-rule">
      <li
        v-for="row in coach.data.value ?? []"
        :key="row.id"
        class="flex flex-wrap items-center justify-between gap-3 py-3"
      >
        <button type="button" class="min-w-0 flex-1 text-left" @click="openProfile(row.id)">
          <span class="font-medium text-ink-900">{{ row.display_name }}</span>
          <span v-if="row.headline" class="mt-0.5 block text-sm text-ink-600">{{
            row.headline
          }}</span>
        </button>
        <span class="font-mono text-xs text-ink-600"
          >{{ row.application_count }} {{ t("coach.apps") }}</span
        >
        <FnButton size="sm" tone="quiet" @click="openProfile(row.id)">{{
          t("coach.open")
        }}</FnButton>
      </li>
      <li v-if="!(coach.data.value ?? []).length" class="py-6 text-sm text-ink-600">
        {{ t("coach.empty") }}
      </li>
    </ul>

    <form class="flex flex-wrap gap-2" @submit.prevent="addProfile">
      <input
        v-model="newName"
        type="text"
        class="min-h-11 min-w-[12rem] flex-1 border border-rule bg-paper-0 px-2 text-sm"
        :placeholder="t('coach.namePlaceholder')"
        :aria-label="t('coach.namePlaceholder')"
      />
      <FnButton type="submit" :disabled="creating || !newName.trim()">{{
        t("coach.add")
      }}</FnButton>
    </form>
  </div>
</template>
