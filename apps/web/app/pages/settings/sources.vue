<script setup lang="ts">
import {
  addCareersApiV1SourcesCareersPost,
  directoryStatsApiV1SourcesDirectoryStatsGet,
  sourceHealthApiV1SourcesHealthGet,
  type SourceHealthRead,
} from "@kame/api-client";
import { FnButton, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

definePageMeta({ layout: "default" });

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const careersUrl = ref("");
const busy = ref(false);

const health = useQuery({
  queryKey: computed(() => ["source-health", ws.currentId]),
  queryFn: async () => {
    const { data } = await sourceHealthApiV1SourcesHealthGet({ throwOnError: true });
    return (data ?? []) as SourceHealthRead[];
  },
  enabled: computed(() => Boolean(ws.currentId) && ws.canManage),
});

const stats = useQuery({
  queryKey: computed(() => ["directory-stats", ws.currentId]),
  queryFn: async () => {
    const { data } = await directoryStatsApiV1SourcesDirectoryStatsGet({ throwOnError: true });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const rows = computed(() => health.data.value ?? []);
const loading = computed(() => health.isPending.value && !health.data.value);

async function addCareers() {
  if (!careersUrl.value.trim()) return;
  busy.value = true;
  try {
    await addCareersApiV1SourcesCareersPost({
      body: { url: careersUrl.value.trim() },
      throwOnError: true,
    });
    careersUrl.value = "";
    await qc.invalidateQueries({ queryKey: ["directory-stats", ws.currentId] });
    toast.push({ title: t("common.saved"), tone: "neutral" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader :title="t('sources.title')" :lede="t('settings.sourcesLede')" />
    <p v-if="stats.data.value" class="text-sm text-ink-600">
      {{ t("sources.directory") }}: {{ stats.data.value.boards_active }} {{ t("sources.boards") }}
    </p>
    <form class="flex flex-wrap gap-2" @submit.prevent="addCareers">
      <label class="flex min-w-[16rem] flex-1 flex-col gap-1 text-sm">
        <span class="text-ink-600">{{ t("tracks.careersUrl") }}</span>
        <input
          v-model="careersUrl"
          type="url"
          class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
          required
        />
      </label>
      <FnButton type="submit" tone="primary" class="self-end" :disabled="busy">{{
        t("sources.add")
      }}</FnButton>
    </form>
    <FnSkeleton v-if="loading" :lines="4" />
    <ul v-else class="divide-y divide-rule border-y border-rule">
      <li v-for="s in rows" :key="s.id" class="flex flex-wrap items-center gap-3 py-3 text-sm">
        <div class="min-w-0 flex-1">
          <p class="font-medium text-ink-900">{{ s.name }}</p>
          <p class="font-mono text-xs text-ink-600">{{ s.key }} · {{ s.kind }}</p>
        </div>
        <span v-if="s.circuit_open" class="text-brand-700">{{ t("sources.circuit") }}</span>
        <span class="text-ink-600">{{ t("sources.jobs") }} {{ s.jobs_ingested }}</span>
        <span class="text-ink-600">{{ t("sources.errors") }} {{ s.error_count }}</span>
        <span class="text-ink-600"
          >{{ t("sources.latency") }}
          {{ s.avg_latency_ms != null ? Math.round(s.avg_latency_ms) + "ms" : "n/a" }}</span
        >
        <span class="text-ink-600">{{ t("sources.blocks") }} {{ s.block_signals }}</span>
      </li>
    </ul>
  </div>
</template>
