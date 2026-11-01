<script setup lang="ts">
import { client } from "@kame/api-client";
import { FnButton, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

type GapItem = {
  id: string;
  skill: string;
  suggestion: string;
  resource_url: string;
  status: string;
};

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const route = useRoute();
const trackId = computed(() => String(route.params.id));
const refreshing = ref(false);
const updating = ref<string | null>(null);

const gaps = useQuery({
  queryKey: computed(() => ["gap-plan", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await client.get({
      url: `/api/v1/tracks/${trackId.value}/gap-plan`,
      throwOnError: true,
    });
    return data as GapItem[];
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});

async function refresh() {
  refreshing.value = true;
  try {
    await client.post({
      url: `/api/v1/tracks/${trackId.value}/gap-plan/refresh`,
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["gap-plan", ws.currentId, trackId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    refreshing.value = false;
  }
}

async function setStatus(id: string, status: string) {
  updating.value = id;
  try {
    await client.patch({
      url: `/api/v1/gap-plan/${id}`,
      body: { status },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["gap-plan", ws.currentId, trackId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    updating.value = null;
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <NuxtLink :to="`/tracks/${trackId}`" class="text-sm text-persimmon-700 underline">{{
          t("nav.tracks")
        }}</NuxtLink>
        <h1 class="mt-2 font-serif text-2xl font-semibold text-ink-900">
          {{ t("gaps.title") }}
        </h1>
      </div>
      <FnButton :disabled="refreshing" @click="refresh">{{ t("gaps.refresh") }}</FnButton>
    </div>

    <div v-if="gaps.isPending.value"><FnSkeleton class="h-32 w-full" /></div>
    <ul v-else class="divide-y divide-rule border-y border-rule">
      <li v-for="g in gaps.data.value ?? []" :key="g.id" class="flex flex-col gap-2 py-4">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <h2 class="font-medium text-ink-900">{{ g.skill }}</h2>
          <span class="font-mono text-xs text-ink-600">{{ g.status }}</span>
        </div>
        <p class="text-sm text-ink-700">{{ g.suggestion }}</p>
        <a
          v-if="g.resource_url"
          :href="g.resource_url"
          target="_blank"
          rel="noopener"
          class="text-sm text-persimmon-700 underline"
          >{{ t("gaps.resource") }}</a
        >
        <div class="flex flex-wrap gap-2">
          <FnButton
            size="sm"
            tone="quiet"
            :disabled="updating === g.id"
            @click="setStatus(g.id, 'in_progress')"
            >{{ t("gaps.inProgress") }}</FnButton
          >
          <FnButton size="sm" :disabled="updating === g.id" @click="setStatus(g.id, 'done')">{{
            t("gaps.done")
          }}</FnButton>
          <FnButton
            size="sm"
            tone="quiet"
            :disabled="updating === g.id"
            @click="setStatus(g.id, 'skipped')"
            >{{ t("gaps.skip") }}</FnButton
          >
        </div>
      </li>
      <li v-if="!(gaps.data.value ?? []).length" class="py-6 text-sm text-ink-600">
        {{ t("gaps.empty") }}
      </li>
    </ul>
  </div>
</template>
