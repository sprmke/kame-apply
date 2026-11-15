<script setup lang="ts">
import {
  runHistoryApiV1TracksTrackIdRunsGet,
  type DiscoveryRunHistoryRead,
} from "@kame/api-client";
import { FnButton, FnEmptyState, FnSectionCard, FnTable, type Column } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const route = useRoute();
const { t, locale } = useI18n();
const ws = useWorkspaceStore();
const trackId = computed(() => String(route.params.id));

const runs = useQuery<DiscoveryRunHistoryRead[]>({
  queryKey: computed(() => ["track-runs", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await runHistoryApiV1TracksTrackIdRunsGet({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    return (data ?? []) as DiscoveryRunHistoryRead[];
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
  refetchInterval: 15_000,
});

type RunRow = {
  id: string;
  status: string;
  trigger: string;
  error: string;
  linked: number;
  scored: number;
  prepared: number;
  duration_ms: number | null;
  started_at: string;
};

function count(value: unknown): number {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n : 0;
}

const rows = computed<RunRow[]>(() =>
  (runs.data.value ?? []).map((r) => ({
    id: r.id,
    status: r.status,
    trigger: r.trigger,
    error: r.error ?? "",
    linked: count(r.progress?.linked),
    scored: count(r.progress?.scored),
    prepared: count(r.progress?.prepared),
    duration_ms: r.duration_ms ?? null,
    started_at: r.started_at ?? r.created_at,
  })),
);

const live = computed<boolean>(() =>
  (runs.data.value ?? []).some((r) => r.status === "running" || r.status === "queued"),
);
const totalNew = computed(() => rows.value.reduce((sum, r) => sum + r.linked, 0));

const columns = computed<Column[]>(() => [
  { key: "status", label: t("tracks.colRun") },
  { key: "found", label: t("tracks.colFound") },
  { key: "duration", label: t("tracks.colDuration"), align: "right" },
]);

function statusLabel(status: string): string {
  if (status === "succeeded") return t("tracks.statusCompleted");
  if (status === "failed") return t("tracks.statusFailed");
  if (status === "running") return t("tracks.statusRunning");
  if (status === "queued") return t("tracks.statusQueued");
  return status;
}

function statusDot(status: string): string {
  if (status === "succeeded") return "bg-fern-600";
  if (status === "failed") return "bg-oxblood-600";
  return "bg-saffron-600";
}

function triggerLabel(trigger: string): string {
  if (trigger === "run_now") return t("tracks.triggerRunNow");
  if (trigger === "schedule") return t("tracks.triggerSchedule");
  if (trigger === "manual") return t("tracks.triggerManual");
  return trigger;
}

function durationLabel(ms: number | null): string {
  if (ms == null) return "";
  return t("tracks.durationSeconds", { n: Math.max(1, Math.round(ms / 1000)) });
}

function relative(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  const abs = Math.abs(diff);
  const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: "auto" });
  if (abs < 60_000) return rtf.format(Math.round(diff / 1000), "second");
  if (abs < 3_600_000) return rtf.format(Math.round(diff / 60_000), "minute");
  if (abs < 86_400_000) return rtf.format(Math.round(diff / 3_600_000), "hour");
  return rtf.format(Math.round(diff / 86_400_000), "day");
}

function foundLabel(row: RunRow): string {
  const parts: string[] = [];
  if (row.linked) parts.push(t("tracks.newMatches", row.linked));
  if (row.scored) parts.push(t("tracks.scoredCount", { n: row.scored }));
  if (row.prepared) parts.push(t("tracks.preparedCount", { n: row.prepared }));
  return parts.length ? parts.join(" · ") : t("tracks.nothingNew");
}
</script>

<template>
  <TrackShell :track-id="trackId">
    <FnSectionCard
      :title="t('tracks.runHistory')"
      :intro="t('tracks.historyIntro')"
      :summary="
        rows.length ? t('tracks.runsSummary', { runs: rows.length, found: totalNew }) : undefined
      "
    >
      <div v-if="live" class="flex items-center gap-1.5 text-sm text-ink-600">
        <span class="size-2 animate-pulse rounded-full bg-saffron-600" aria-hidden="true" />
        {{ t("tracks.runningNow") }}
      </div>

      <FnTable
        v-if="rows.length"
        stack
        :columns="columns"
        :rows="rows"
        row-key="id"
        density="compact"
        :caption="t('tracks.historyCaption')"
        :empty="t('tracks.noRuns')"
      >
        <template #cell-status="{ row }">
          <div class="flex flex-col gap-0.5 py-2 text-left sm:py-0">
            <span class="flex items-center gap-2 text-sm font-semibold text-ink-900">
              <span class="size-2 rounded-full" :class="statusDot(row.status)" aria-hidden="true" />
              {{ statusLabel(row.status) }}
            </span>
            <span class="text-xs text-ink-600" :title="new Date(row.started_at).toLocaleString()">
              {{ triggerLabel(row.trigger) }} · {{ relative(row.started_at) }}
            </span>
            <span
              v-if="row.error"
              class="max-w-80 truncate text-xs text-oxblood-600"
              :title="row.error"
            >
              {{ row.error }}
            </span>
            <span v-if="row.status === 'failed'" class="text-xs text-ink-600">
              {{ t("tracks.failedHint") }}
            </span>
          </div>
        </template>
        <template #cell-found="{ row }">
          <span class="text-sm" :class="row.linked ? 'text-ink-900' : 'text-ink-600'">{{
            foundLabel(row)
          }}</span>
        </template>
        <template #cell-duration="{ row }">
          <span class="text-sm text-ink-600">{{ durationLabel(row.duration_ms) }}</span>
        </template>
      </FnTable>

      <FnEmptyState
        v-else-if="!runs.isPending.value"
        :title="t('tracks.noRuns')"
        :body="t('tracks.historyEmptyBody')"
      >
        <FnButton as-child tone="primary" size="sm">
          <NuxtLink :to="`/tracks/${trackId}`">{{ t("jobs.findNow") }}</NuxtLink>
        </FnButton>
      </FnEmptyState>
    </FnSectionCard>
  </TrackShell>
</template>
