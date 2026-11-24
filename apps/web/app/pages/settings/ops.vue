<script setup lang="ts">
import { FnEmptyState, FnSectionCard, FnSkeleton, FnSkeletonGroup } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

definePageMeta({ layout: "default" });

const { t } = useI18n();
const ws = useWorkspaceStore();
const auth = useAuthStore();
const cfg = useRuntimeConfig().public;
const fmt = useFormat();

const dash = useQuery({
  queryKey: computed(() => ["ops-dashboard", ws.currentId]),
  queryFn: async () => {
    const token = await auth.ensureFresh();
    const base = String(cfg.apiBase || "").replace(/\/$/, "");
    const res = await fetch(`${base}/api/v1/ops/dashboard`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(ws.currentId ? { "X-Workspace-Id": ws.currentId } : {}),
      },
      credentials: "include",
    });
    if (!res.ok) throw new Error(String(res.status));
    return res.json() as Promise<{
      sources: Array<{
        id: string;
        name: string;
        circuit_open: boolean;
        jobs_ingested: number;
      }>;
      recent_runs: Array<{
        id: string;
        status: string;
        trigger: string;
        created_at: string | null;
      }>;
      ai_cost: {
        spent_micros: number;
        budget_cents: number;
        by_feature: Array<{ feature: string; cost_micros: number; calls: number }>;
      };
    }>;
  },
  enabled: computed(() => Boolean(ws.currentId) && ws.canManage),
});

function featureLabel(feature: string): string {
  const labels: Record<string, string> = {
    resume_tailoring: "Resume tailoring",
    resume_critique: "Resume check",
    cover_letter: "Cover letters",
    answer_draft: "Answer drafts",
    search_plan: "Search setup",
    reply_classify: "Reading replies",
    contacts_parse: "Reading contacts",
    search_plan_eval: "Search setup check",
  };
  return labels[feature] ?? feature.replaceAll("_", " ");
}

const statusKey: Record<string, string> = {
  succeeded: "completed",
  failed: "stopped",
  running: "running",
  queued: "queued",
};

function triggerLabel(value: string): string {
  const words = value.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const spentUsd = computed(() =>
  (((dash.data.value?.ai_cost?.spent_micros ?? 0) as number) / 1_000_000).toFixed(2),
);
const budgetUsd = computed(() =>
  (((dash.data.value?.ai_cost?.budget_cents ?? 0) as number) / 100).toFixed(2),
);
</script>

<template>
  <section class="flex max-w-3xl flex-col gap-6">
    <PageHeader :title="t('ops.title')" />

    <FnSkeletonGroup
      v-if="dash.isPending.value && !dash.data.value"
      :label="t('common.loading')"
      class="flex flex-col gap-6"
    >
      <SkeletonSectionCard v-for="n in 3" :key="n" :intro="false">
        <ul class="flex flex-col gap-2 text-sm">
          <li v-for="row in 3" :key="row" class="flex items-baseline justify-between gap-4">
            <FnSkeleton class="h-4 w-2/5" />
            <FnSkeleton class="h-3.5 w-24" />
          </li>
        </ul>
      </SkeletonSectionCard>
    </FnSkeletonGroup>

    <FnEmptyState v-else-if="dash.isError.value" :title="t('ops.loadError')" tone="danger" />

    <template v-else-if="dash.data.value">
      <FnSectionCard
        :title="t('ops.aiCost')"
        :summary="`${t('ops.spent')} $${spentUsd} · ${t('ops.budget')} $${budgetUsd}`"
      >
        <ul v-if="dash.data.value.ai_cost.by_feature.length" class="flex flex-col gap-1 text-sm">
          <li
            v-for="f in dash.data.value.ai_cost.by_feature"
            :key="f.feature"
            class="flex items-baseline justify-between gap-4"
          >
            <span class="text-ink-900">{{ featureLabel(f.feature) }}</span>
            <span class="text-ink-600 tabular-nums"
              >${{ (f.cost_micros / 1_000_000).toFixed(3) }} · {{ f.calls }}</span
            >
          </li>
        </ul>
        <p v-else class="text-sm text-ink-600">{{ t("ops.noCost") }}</p>
      </FnSectionCard>

      <FnSectionCard :title="t('ops.sources')">
        <ul v-if="dash.data.value.sources.length" class="flex flex-col gap-1 text-sm">
          <li
            v-for="s in dash.data.value.sources"
            :key="s.id"
            class="flex flex-wrap items-baseline justify-between gap-x-4"
          >
            <span class="text-ink-900">{{ s.name }}</span>
            <span class="text-ink-600">
              {{ s.circuit_open ? t("sources.circuit") : t("sources.ok") }} · {{ s.jobs_ingested }}
              {{ t("sources.jobs") }}
            </span>
          </li>
        </ul>
        <p v-else class="text-sm text-ink-600">{{ t("ops.noSources") }}</p>
      </FnSectionCard>

      <FnSectionCard :title="t('ops.runs')">
        <ul v-if="dash.data.value.recent_runs.length" class="flex flex-col gap-1 text-sm">
          <li
            v-for="r in dash.data.value.recent_runs"
            :key="r.id"
            class="flex flex-wrap items-baseline justify-between gap-x-4"
          >
            <span class="text-ink-900">{{
              t(`ops.status_${statusKey[r.status] ?? "unknown"}`)
            }}</span>
            <span class="text-ink-600">
              {{ triggerLabel(r.trigger) }} ·
              {{ r.created_at ? fmt.dateTime(r.created_at) : "" }}
            </span>
          </li>
        </ul>
        <p v-else class="text-sm text-ink-600">{{ t("ops.emptyRuns") }}</p>
      </FnSectionCard>
    </template>
  </section>
</template>
