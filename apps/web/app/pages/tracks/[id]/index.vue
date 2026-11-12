<script setup lang="ts">
import {
  discoverNowApiV1TracksTrackIdDiscoverPost,
  getDiscoveryRunApiV1DiscoveryRunsRunIdGet,
  listJobsApiV1JobsGet,
  runHistoryApiV1TracksTrackIdRunsGet,
  type BoardJobRead,
  type DiscoveryRunHistoryRead,
  type DiscoveryRunRead,
} from "@kame/api-client";
import { FnButton, FnEmptyState, FnRiskSeal, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const route = useRoute();
const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const fmt = useFormat();

const trackId = computed(() => String(route.params.id));
const running = ref(false);
const runProgress = ref<DiscoveryRunRead["progress"] | null>(null);
const runSeconds = ref(0);
let runTimer: ReturnType<typeof setInterval> | null = null;

const runs = useQuery({
  queryKey: computed(() => ["track-runs", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await runHistoryApiV1TracksTrackIdRunsGet({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    return (data ?? []) as DiscoveryRunHistoryRead[];
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
  refetchInterval: computed(() => (running.value ? 5000 : 30_000)),
});
const lastRun = computed(() => runs.data.value?.[0] ?? null);
const lastRunNew = computed(() => Number(lastRun.value?.progress?.linked ?? 0));

const jobs = useQuery({
  queryKey: computed(() => ["track-match-preview", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await listJobsApiV1JobsGet({
      query: {
        track_id: trackId.value,
        include_not_eligible: false,
        sort: "score",
        limit: 12,
      },
      throwOnError: true,
    });
    return (data ?? []) as BoardJobRead[];
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});

watch(running, (value) => {
  if (runTimer) clearInterval(runTimer);
  runTimer = null;
  if (!value) return;
  runSeconds.value = 0;
  runTimer = setInterval(() => {
    runSeconds.value += 1;
  }, 1000);
});

onUnmounted(() => {
  if (runTimer) clearInterval(runTimer);
});

async function runNow() {
  running.value = true;
  runProgress.value = null;
  try {
    const { data } = await discoverNowApiV1TracksTrackIdDiscoverPost({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    runProgress.value = data?.progress ?? null;
    if (data && (data.status === "queued" || data.status === "running")) {
      for (let i = 0; i < 60; i += 1) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        try {
          const { data: latest } = await getDiscoveryRunApiV1DiscoveryRunsRunIdGet({
            path: { run_id: String(data.id) },
            throwOnError: true,
          });
          runProgress.value = latest?.progress ?? runProgress.value;
          if (latest && latest.status !== "queued" && latest.status !== "running") break;
        } catch {
          break;
        }
      }
    }
    await qc.invalidateQueries({ queryKey: ["track-runs", ws.currentId, trackId.value] });
    await qc.invalidateQueries({ queryKey: ["track-match-preview", ws.currentId, trackId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    running.value = false;
  }
}

const rows = computed(() => jobs.data.value ?? []);

function workModeLabel(mode: string | null | undefined): string {
  return mode ? t(`tracks.mode_${mode}`) : "";
}

function sealLevel(level: string | null | undefined): "clear" | "caution" | "danger" {
  if (level === "red") return "danger";
  if (level === "yellow") return "caution";
  return "clear";
}

function sealLabel(level: string | null | undefined): string {
  if (level === "red") return t("jobs.highRisk");
  if (level === "yellow") return t("jobs.caution");
  return t("jobs.clear");
}

function salaryLine(s: Record<string, unknown> | undefined): string {
  if (!s || s.min == null) return "";
  const min = Number(s.min);
  const max = s.max != null ? Number(s.max) : null;
  const range = max != null ? `${min}-${max}` : `${min}`;
  return [s.currency, range, s.period ? `/ ${s.period}` : ""].filter(Boolean).join(" ");
}
</script>

<template>
  <TrackShell :track-id="trackId">
    <div class="flex flex-col gap-5">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="min-w-0 text-sm text-ink-600">
          <template v-if="running">
            <span class="inline-flex items-center gap-2">
              <span class="size-2 animate-pulse rounded-full bg-ink-600" aria-hidden="true" />
              {{ t("tracks.searchingBoards") }} · {{ runSeconds }}s
            </span>
            <span v-if="runProgress" class="mt-1 block">
              {{
                t("tracks.runProgress", {
                  boards: runProgress.boards_checked ?? 0,
                  found: runProgress.jobs_found ?? 0,
                  new: runProgress.jobs_new ?? 0,
                  linked: runProgress.linked ?? 0,
                })
              }}
            </span>
          </template>
          <span v-else-if="lastRun">
            {{
              t("tracks.lastSearch", {
                when: fmt.dateTime(lastRun.started_at || lastRun.created_at),
              })
            }}
            · {{ t("tracks.newMatches", lastRunNew) }}
          </span>
          <span v-else>{{ t("tracks.neverRun") }}</span>
        </div>
        <div class="flex flex-wrap gap-2 sm:shrink-0">
          <FnButton tone="primary" :disabled="running" @click="runNow">
            {{ running ? t("tracks.running") : t("jobs.findNow") }}
          </FnButton>
          <FnButton as-child tone="quiet">
            <NuxtLink :to="`/jobs?track=${trackId}`">{{ t("tracks.viewMatches") }}</NuxtLink>
          </FnButton>
        </div>
      </div>

      <div v-if="jobs.isPending.value" class="flex flex-col gap-3">
        <FnSkeleton class="h-20 w-full" />
        <FnSkeleton class="h-20 w-full" />
      </div>

      <FnEmptyState
        v-else-if="!rows.length"
        :title="t('tracks.noMatchesYet')"
        :body="t('tracks.noMatchesBody')"
      >
        <FnButton tone="primary" :disabled="running" @click="runNow">
          {{ t("jobs.findNow") }}
        </FnButton>
      </FnEmptyState>

      <ul v-else class="flex flex-col gap-2">
        <li v-for="job in rows" :key="job.id">
          <NuxtLink
            :to="`/jobs?track=${trackId}&job=${job.id}`"
            class="flex items-start gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)] transition-colors hover:border-brand-200 hover:bg-brand-50"
          >
            <span
              class="grid min-w-10 place-items-center rounded-md bg-paper-2 px-1.5 py-1 text-sm font-bold tabular-nums text-brand-700"
              >{{ job.score != null ? Math.round(job.score) : "-" }}</span
            >
            <span class="min-w-0 flex-1">
              <span class="block font-semibold text-ink-900">{{ job.title }}</span>
              <span class="block text-sm text-ink-600">
                {{ job.company_name }}
                <template v-if="job.work_mode"> · {{ workModeLabel(job.work_mode) }}</template>
                <template v-if="salaryLine(job.salary as Record<string, unknown>)">
                  · {{ salaryLine(job.salary as Record<string, unknown>) }}
                </template>
              </span>
            </span>
            <FnRiskSeal
              v-if="job.risk_level === 'yellow' || job.risk_level === 'red'"
              :level="sealLevel(job.risk_level)"
              :label="sealLabel(job.risk_level)"
            />
            <NavIcon name="ph:caret-right" :size="16" class="mt-1 shrink-0 text-ink-400" />
          </NuxtLink>
        </li>
      </ul>
    </div>
  </TrackShell>
</template>
