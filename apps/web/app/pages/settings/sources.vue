<script setup lang="ts">
import {
  addCareersApiV1SourcesCareersPost,
  directoryStatsApiV1SourcesDirectoryStatsGet,
  sourceHealthApiV1SourcesHealthGet,
  type SourceHealthRead,
} from "@kame/api-client";
import { FnButton, FnField, FnInput, FnSkeleton, useToast } from "@kame/ui";
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

function kindLabel(kind: string): string {
  if (kind === "api") return t("sources.kindApi");
  if (kind === "feed") return t("sources.kindFeed");
  if (kind === "ats") return t("sources.kindCareer");
  if (kind === "email") return t("sources.kindEmail");
  return t("sources.kindOther");
}

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
      {{ t("sources.directoryLine", { n: stats.data.value.boards_active }) }}
    </p>
    <p class="text-sm leading-6 text-ink-600">{{ t("sources.legend") }}</p>
    <form class="flex flex-wrap items-end gap-2" @submit.prevent="addCareers">
      <FnField v-slot="{ id }" :label="t('sources.careersLabel')" class="min-w-[16rem] flex-1">
        <FnInput :id="id" v-model="careersUrl" type="url" inputmode="url" required />
      </FnField>
      <FnButton type="submit" tone="primary" :disabled="busy">{{ t("sources.add") }}</FnButton>
    </form>
    <FnSkeleton v-if="loading" :lines="4" />
    <ul v-else class="divide-y divide-rule border-y border-rule">
      <li v-for="s in rows" :key="s.id" class="flex flex-wrap items-center gap-3 py-3 text-sm">
        <div class="min-w-0 flex-1">
          <p class="font-medium text-ink-900">{{ s.name }}</p>
          <p class="text-xs text-ink-600">{{ kindLabel(s.kind) }}</p>
        </div>
        <span v-if="s.circuit_open" class="text-brand-700">{{ t("sources.circuit") }}</span>
        <span class="text-ink-600">{{ t("sources.jobs") }} {{ s.jobs_ingested }}</span>
        <span class="text-ink-600">{{ t("sources.errors") }} {{ s.error_count }}</span>
        <span class="text-ink-600"
          >{{ t("sources.latency") }}
          {{
            s.avg_latency_ms != null ? Math.round(s.avg_latency_ms) + " ms" : t("sources.noData")
          }}</span
        >
        <span class="text-ink-600">{{ t("sources.blocks") }} {{ s.block_signals }}</span>
      </li>
    </ul>
  </div>
</template>
