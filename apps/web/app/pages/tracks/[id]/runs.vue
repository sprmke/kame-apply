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
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 md:px-6">
    <div v-if="detail.isPending.value || runs.isPending.value">
      <FnSkeleton class="h-10 w-48" />
    </div>
    <p v-else-if="detail.error.value" class="text-sm text-ink-600">
      {{ apiError(detail.error.value) }}
    </p>
    <template v-else-if="track">
      <PageHeader :title="track.name" />
      <nav class="flex flex-wrap gap-1 border-b border-rule" :aria-label="t('tracks.sections')">
        <NuxtLink
          :to="`/tracks/${trackId}`"
          class="px-3 py-2 text-sm text-ink-600 hover:text-ink-900"
          >{{ t("tracks.criteria") }}</NuxtLink
        >
        <NuxtLink
          :to="`/tracks/${trackId}/settings`"
          class="px-3 py-2 text-sm text-ink-600 hover:text-ink-900"
          >{{ t("tracks.settings") }}</NuxtLink
        >
        <span class="relative px-3 py-2 text-sm font-medium text-ink-900"
          >{{ t("tracks.runHistory")
          }}<span class="absolute inset-x-2 bottom-0 h-0.5 bg-ink-900" aria-hidden="true"
        /></span>
      </nav>

      <p v-if="!rows.length" class="text-sm text-ink-600">{{ t("tracks.noRuns") }}</p>
      <ul v-else class="divide-y divide-rule border-y border-rule">
        <li
          v-for="r in rows"
          :key="r.id"
          class="grid gap-1 py-3 text-sm md:grid-cols-[1fr_auto] md:items-center"
        >
          <div class="flex flex-col gap-0.5">
            <span class="font-medium text-ink-900">{{ r.status }} · {{ r.trigger }}</span>
            <span class="font-mono text-[0.6875rem] text-ink-600">
              {{
                t("tracks.runStats", {
                  linked: r.progress?.linked ?? 0,
                  scored: r.progress?.scored ?? 0,
                  prepared: r.progress?.prepared ?? 0,
                  ms: r.duration_ms ?? "—",
                })
              }}
            </span>
            <span v-if="r.error" class="text-persimmon-700">{{ r.error }}</span>
          </div>
          <span class="font-mono text-[0.6875rem] text-ink-600">{{
            r.started_at ? fmt.dateTime(r.started_at) : fmt.dateTime(r.created_at)
          }}</span>
        </li>
      </ul>
    </template>
  </div>
</template>
