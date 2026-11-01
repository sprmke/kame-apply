<script setup lang="ts">
import {
  createScheduleApiV1TracksTrackIdSchedulesPost,
  deleteScheduleApiV1SchedulesScheduleIdDelete,
  getTrackApiV1TracksTrackIdGet,
  listSchedulesApiV1TracksTrackIdSchedulesGet,
  patchTrackSourceApiV1TracksTrackIdSourcesSourceIdPatch,
  pauseTrackApiV1TracksTrackIdPausePost,
  resumeTrackApiV1TracksTrackIdResumePost,
  trackSourcesApiV1TracksTrackIdSourcesGet,
  updateTrackApiV1TracksTrackIdPatch,
  client,
  type ScheduleRead,
  type TrackSourceRead,
} from "@kame/api-client";
import { FnButton, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const route = useRoute();
const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const trackId = computed(() => String(route.params.id));
const autonomy = ref("discover");
const saving = ref(false);
const preset = ref("every_2_hours");
const timezone = ref("Asia/Manila");
const quietStart = ref("23:00");
const quietEnd = ref("07:00");
const dailyCap = ref(12);
const adding = ref(false);

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

const track = computed(() => detail.data.value ?? null);
const loading = computed(
  () => !ws.loaded || detail.isPending.value || (detail.isFetching.value && !track.value),
);
const loadError = computed(() => detail.error.value);

const sources = useQuery({
  queryKey: computed(() => ["track-sources", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await trackSourcesApiV1TracksTrackIdSourcesGet({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    return (data ?? []) as TrackSourceRead[];
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});
const sourceRows = computed(() => sources.data.value ?? []);

const schedules = useQuery({
  queryKey: computed(() => ["track-schedules", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await listSchedulesApiV1TracksTrackIdSchedulesGet({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    return (data ?? []) as ScheduleRead[];
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});
const scheduleRows = computed(() => schedules.data.value ?? []);

type AutoCfg = {
  live_enabled: boolean;
  dry_run_remaining: number;
  score_threshold: number;
  kill_switch: boolean;
  workspace_kill_switch: boolean;
  global_enabled: boolean;
};

const autoCfg = useQuery({
  queryKey: computed(() => ["auto-submit", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await client.get({
      url: `/api/v1/tracks/${trackId.value}/auto-submit`,
      throwOnError: true,
    });
    return data as AutoCfg;
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});

const dryRuns = useQuery({
  queryKey: computed(() => ["auto-dry-runs", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await client.get({
      url: `/api/v1/tracks/${trackId.value}/auto-submit/dry-runs`,
      throwOnError: true,
    });
    return (data ?? []) as { id: string; would_submit: boolean; created_at: string }[];
  },
  enabled: computed(() =>
    Boolean(ws.currentId && trackId.value && autonomy.value === "auto_submit"),
  ),
});

async function saveAuto(patch: Partial<AutoCfg>) {
  try {
    await client.put({
      url: `/api/v1/tracks/${trackId.value}/auto-submit`,
      body: patch,
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["auto-submit", ws.currentId, trackId.value] });
    toast.push({ title: t("common.saved") });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

watch(
  () => detail.data.value?.autonomy,
  (v) => {
    if (v) autonomy.value = v;
  },
  { immediate: true },
);

async function toggleSource(row: TrackSourceRead) {
  try {
    await patchTrackSourceApiV1TracksTrackIdSourcesSourceIdPatch({
      path: { track_id: trackId.value, source_id: row.source_id },
      body: { enabled: !row.enabled },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["track-sources", ws.currentId, trackId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function saveAutonomy() {
  saving.value = true;
  try {
    await updateTrackApiV1TracksTrackIdPatch({
      path: { track_id: trackId.value },
      body: { autonomy: autonomy.value as "discover" | "prepare" | "assist" | "auto_submit" },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["track", ws.currentId, trackId.value] });
    toast.push({ title: t("common.saved"), tone: "neutral" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    saving.value = false;
  }
}

async function addSchedule() {
  adding.value = true;
  try {
    await createScheduleApiV1TracksTrackIdSchedulesPost({
      path: { track_id: trackId.value },
      body: {
        preset: preset.value as
          "hourly" | "every_2_hours" | "every_4_hours" | "daily_morning" | "weekdays_2h" | "custom",
        timezone: timezone.value,
        quiet_hours: { start: quietStart.value, end: quietEnd.value },
        daily_cap: dailyCap.value,
      },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["track-schedules", ws.currentId, trackId.value] });
    toast.push({ title: t("common.saved"), tone: "neutral" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    adding.value = false;
  }
}

async function removeSchedule(id: string) {
  try {
    await deleteScheduleApiV1SchedulesScheduleIdDelete({
      path: { schedule_id: id },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["track-schedules", ws.currentId, trackId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function togglePause() {
  try {
    if (track.value?.status === "paused") {
      await resumeTrackApiV1TracksTrackIdResumePost({
        path: { track_id: trackId.value },
        throwOnError: true,
      });
    } else {
      await pauseTrackApiV1TracksTrackIdPausePost({
        path: { track_id: trackId.value },
        throwOnError: true,
      });
    }
    await qc.invalidateQueries({ queryKey: ["track", ws.currentId, trackId.value] });
    await qc.invalidateQueries({ queryKey: ["track-schedules", ws.currentId, trackId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 md:px-6">
    <div v-if="loading">
      <FnSkeleton class="h-10 w-48" />
    </div>
    <p v-else-if="loadError" class="text-sm text-ink-600">{{ apiError(loadError) }}</p>
    <template v-else-if="track">
      <PageHeader :title="track.name" />
      <nav class="flex flex-wrap gap-1 border-b border-rule" :aria-label="t('tracks.sections')">
        <NuxtLink
          :to="`/tracks/${trackId}`"
          class="px-3 py-2 text-sm text-ink-600 hover:text-ink-900"
          >{{ t("tracks.criteria") }}</NuxtLink
        >
        <NuxtLink
          :to="`/tracks/${trackId}/runs`"
          class="px-3 py-2 text-sm text-ink-600 hover:text-ink-900"
          >{{ t("tracks.runHistory") }}</NuxtLink
        >
        <span class="relative px-3 py-2 text-sm font-medium text-ink-900"
          >{{ t("tracks.settings")
          }}<span class="absolute inset-x-2 bottom-0 h-0.5 bg-ink-900" aria-hidden="true"
        /></span>
      </nav>

      <section class="flex flex-col gap-3">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("tracks.autonomy") }}
        </h2>
        <select
          v-model="autonomy"
          class="min-h-11 max-w-xs border border-rule bg-paper-0 px-3 text-sm"
        >
          <option value="discover">{{ t("tracks.autonomyDiscover") }}</option>
          <option value="prepare">{{ t("tracks.autonomyPrepare") }}</option>
          <option value="assist">{{ t("tracks.autonomyAssist") }}</option>
          <option value="auto_submit">{{ t("tracks.autonomyAuto") }}</option>
        </select>
        <div class="flex flex-wrap gap-2">
          <FnButton tone="primary" :disabled="saving" @click="saveAutonomy">{{
            t("common.save")
          }}</FnButton>
          <FnButton tone="quiet" @click="togglePause">{{
            track.status === "paused" ? t("tracks.resume") : t("tracks.pause")
          }}</FnButton>
        </div>
      </section>

      <section
        v-if="autonomy === 'auto_submit' && autoCfg.data.value"
        class="flex flex-col gap-3 border-t border-rule pt-4"
      >
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("autoSubmit.title") }}
        </h2>
        <p class="text-sm text-ink-700">
          {{ t("autoSubmit.dryLeft") }} {{ autoCfg.data.value.dry_run_remaining }}
        </p>
        <p class="text-sm text-ink-700">
          {{ t("autoSubmit.threshold") }} {{ autoCfg.data.value.score_threshold }}
        </p>
        <div class="flex flex-wrap gap-2">
          <FnButton
            size="sm"
            :disabled="autoCfg.data.value.dry_run_remaining > 0"
            @click="saveAuto({ live_enabled: true, dry_run_remaining: 0 })"
            >{{ t("autoSubmit.enableLive") }}</FnButton
          >
          <FnButton
            size="sm"
            tone="quiet"
            @click="saveAuto({ kill_switch: !autoCfg.data.value.kill_switch })"
            >{{
              autoCfg.data.value.kill_switch ? t("autoSubmit.clearKill") : t("autoSubmit.kill")
            }}</FnButton
          >
        </div>
        <ul class="text-sm text-ink-600">
          <li v-for="d in dryRuns.data.value ?? []" :key="d.id">
            {{ d.would_submit ? t("autoSubmit.wouldSubmit") : t("autoSubmit.blocked") }} ·
            {{ d.created_at }}
          </li>
        </ul>
      </section>

      <section class="flex flex-col gap-2 border-t border-rule pt-4">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("tracks.sourcesEnabled") }}
        </h2>
        <ul class="divide-y divide-rule border-y border-rule">
          <li
            v-for="row in sourceRows"
            :key="row.id"
            class="flex min-h-11 items-center justify-between gap-3 py-2 text-sm"
          >
            <span class="font-mono text-ink-900">{{ row.source_key }}</span>
            <label class="flex items-center gap-2">
              <input type="checkbox" :checked="row.enabled" @change="toggleSource(row)" />
            </label>
          </li>
        </ul>
      </section>

      <section class="flex flex-col gap-3 border-t border-rule pt-4">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("tracks.schedule") }}
        </h2>
        <ul v-if="scheduleRows.length" class="divide-y divide-rule border-y border-rule">
          <li
            v-for="s in scheduleRows"
            :key="s.id"
            class="flex min-h-11 items-center justify-between gap-3 py-2 text-sm"
          >
            <div class="flex min-w-0 flex-col">
              <span class="text-ink-900">{{ s.preview }}</span>
              <span class="font-mono text-[0.6875rem] text-ink-600"
                >{{ s.scope }} · cap {{ s.daily_cap }} ·
                {{ s.enabled ? t("tracks.scheduleOn") : t("tracks.scheduleOff") }}</span
              >
            </div>
            <FnButton tone="quiet" size="sm" @click="removeSchedule(String(s.id))">{{
              t("common.delete")
            }}</FnButton>
          </li>
        </ul>
        <div class="grid max-w-md gap-2">
          <select v-model="preset" class="min-h-11 border border-rule bg-paper-0 px-3 text-sm">
            <option value="hourly">{{ t("tracks.presetHourly") }}</option>
            <option value="every_2_hours">{{ t("tracks.presetEvery2h") }}</option>
            <option value="every_4_hours">{{ t("tracks.presetEvery4h") }}</option>
            <option value="daily_morning">{{ t("tracks.presetDaily") }}</option>
            <option value="weekdays_2h">{{ t("tracks.presetWeekdays2h") }}</option>
          </select>
          <input
            v-model="timezone"
            class="min-h-11 border border-rule bg-paper-0 px-3 text-sm"
            :aria-label="t('profile.timezone')"
          />
          <div class="flex gap-2">
            <input
              v-model="quietStart"
              class="min-h-11 w-full border border-rule bg-paper-0 px-3 text-sm"
              :aria-label="t('tracks.quietStart')"
            />
            <input
              v-model="quietEnd"
              class="min-h-11 w-full border border-rule bg-paper-0 px-3 text-sm"
              :aria-label="t('tracks.quietEnd')"
            />
          </div>
          <input
            v-model.number="dailyCap"
            type="number"
            min="0"
            max="48"
            class="min-h-11 border border-rule bg-paper-0 px-3 text-sm"
            :aria-label="t('tracks.dailyCap')"
          />
          <FnButton tone="primary" class="self-start" :disabled="adding" @click="addSchedule">{{
            t("tracks.addSchedule")
          }}</FnButton>
        </div>
      </section>

      <section class="flex flex-col gap-2 border-t border-rule pt-4">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("tracks.resume") }}
        </h2>
        <NuxtLink :to="`/studio?track=${trackId}`" class="text-sm text-persimmon-700 underline">
          {{ t("tracks.openStudio") }}
        </NuxtLink>
      </section>
    </template>
  </div>
</template>
