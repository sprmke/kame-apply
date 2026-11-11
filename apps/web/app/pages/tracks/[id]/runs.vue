<script setup lang="ts">
import {
  getTrackApiV1TracksTrackIdGet,
  runHistoryApiV1TracksTrackIdRunsGet,
  type DiscoveryRunHistoryRead,
} from "@kame/api-client";
import { FnSkeleton } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const route = useRoute();
const { t } = useI18n();
const apiError = useApiError();
const ws = useWorkspaceStore();
const fmt = useFormat();
const trackId = computed(() => String(route.params.id));

const detail = useQuery({
  queryKey: computed(() => ["track", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await getTrackApiV1TracksTrackIdGet({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});

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
  refetchInterval: 10_000,
});

const rows = computed(() => runs.data.value ?? []);
const track = computed(() => detail.data.value ?? null);

function statusLabel(status: string): string {
  if (status === "succeeded") return "Completed";
  if (status === "failed") return "Failed";
  if (status === "running") return "Running";
  if (status === "queued") return "Queued";
  return status;
}

function triggerLabel(trigger: string): string {
  if (trigger === "run_now") return "Run now";
  if (trigger === "schedule") return "Scheduled";
  if (trigger === "manual") return "Manual";
  return trigger;
}

function durationLabel(ms: number | null | undefined): string {
  if (ms == null) return "—";
  return `${Math.max(1, Math.round(ms / 1000))}s`;
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-8 md:px-6">
    <div v-if="detail.isPending.value || runs.isPending.value">
      <FnSkeleton class="h-10 w-48" />
    </div>
    <p v-else-if="detail.error.value" class="text-sm text-ink-600">
      {{ apiError(detail.error.value) }}
    </p>
    <template v-else-if="track">
      <PageHeader :title="track.name" />
      <nav
        class="flex flex-wrap gap-1 rounded-lg bg-paper-2 p-1"
        :aria-label="t('tracks.sections')"
      >
        <NuxtLink
          :to="`/tracks/${trackId}`"
          class="rounded-md px-4 py-2 text-sm font-semibold text-ink-600 hover:text-ink-900"
          >{{ t("tracks.criteria") }}</NuxtLink
        >
        <NuxtLink
          :to="`/tracks/${trackId}/settings`"
          class="rounded-md px-4 py-2 text-sm font-semibold text-ink-600 hover:text-ink-900"
          >{{ t("tracks.settings") }}</NuxtLink
        >
        <span
          class="rounded-md bg-paper-1 px-4 py-2 text-sm font-semibold text-brand-700 shadow-[var(--shadow-card)]"
          >{{ t("tracks.runHistory") }}</span
        >
      </nav>

      <div
        v-if="!rows.length"
        class="flex flex-col items-start gap-3 rounded-xl border border-dashed border-rule bg-paper-1 p-6"
      >
        <p class="text-sm text-ink-600">{{ t("tracks.noRuns") }}</p>
        <NuxtLink :to="`/tracks/${trackId}`" class="text-sm font-medium text-brand-700 underline">{{
          t("tracks.runNow")
        }}</NuxtLink>
      </div>
      <ul
        v-else
        class="divide-y divide-rule overflow-hidden rounded-xl border border-rule bg-paper-1 shadow-[var(--shadow-card)]"
      >
        <li
          v-for="r in rows"
          :key="r.id"
          class="grid gap-1 px-5 py-4 text-sm md:grid-cols-[1fr_auto] md:items-center"
        >
          <div class="flex flex-col gap-0.5">
            <span class="font-medium text-ink-900"
              >{{ statusLabel(r.status) }} · {{ triggerLabel(r.trigger) }}</span
            >
            <span class="font-mono text-[0.6875rem] text-ink-600">
              {{
                t("tracks.runStats", {
                  linked: r.progress?.linked ?? 0,
                  scored: r.progress?.scored ?? 0,
                  prepared: r.progress?.prepared ?? 0,
                  duration: durationLabel(r.duration_ms),
                })
              }}
            </span>
            <span v-if="r.error" class="text-brand-700">{{ r.error }}</span>
          </div>
          <span class="font-mono text-[0.6875rem] text-ink-600">{{
            r.started_at ? fmt.dateTime(r.started_at) : fmt.dateTime(r.created_at)
          }}</span>
        </li>
      </ul>
    </template>
  </div>
</template>
