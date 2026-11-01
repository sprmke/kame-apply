<script setup lang="ts">
import { FnSkeleton } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

definePageMeta({ layout: "default" });

const { t } = useI18n();
const ws = useWorkspaceStore();
const auth = useAuthStore();
const cfg = useRuntimeConfig().public;

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
    <FnSkeleton v-if="dash.isPending.value && !dash.data.value" class="h-32" />
    <template v-else-if="dash.data.value">
      <div class="border-t border-rule pt-4">
        <h2 class="font-medium">{{ t("ops.aiCost") }}</h2>
        <p class="mt-1 text-sm text-ink-600">
          {{ t("ops.spent") }}: ${{ spentUsd }} · {{ t("ops.budget") }}: ${{ budgetUsd }}
        </p>
        <ul class="mt-2 space-y-1 text-sm">
          <li v-for="f in dash.data.value.ai_cost.by_feature" :key="f.feature">
            {{ f.feature }}: {{ (f.cost_micros / 1_000_000).toFixed(3) }} ({{ f.calls }})
          </li>
        </ul>
      </div>
      <div class="border-t border-rule pt-4">
        <h2 class="font-medium">{{ t("ops.sources") }}</h2>
        <ul class="mt-2 space-y-1 text-sm">
          <li v-for="s in dash.data.value.sources" :key="s.id">
            {{ s.name }}
            <span class="text-ink-600"
              >· {{ s.circuit_open ? "open" : "ok" }} · {{ s.jobs_ingested }} jobs</span
            >
          </li>
        </ul>
      </div>
      <div class="border-t border-rule pt-4">
        <h2 class="font-medium">{{ t("ops.runs") }}</h2>
        <p v-if="!dash.data.value.recent_runs.length" class="mt-1 text-sm text-ink-600">
          {{ t("ops.emptyRuns") }}
        </p>
        <ul v-else class="mt-2 space-y-1 font-mono text-xs">
          <li v-for="r in dash.data.value.recent_runs" :key="r.id">
            {{ r.status }} · {{ r.trigger }} · {{ r.created_at }}
          </li>
        </ul>
      </div>
    </template>
  </section>
</template>
