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
  updateScheduleApiV1SchedulesScheduleIdPatch,
  updateTrackApiV1TracksTrackIdPatch,
  client,
  type ScheduleRead,
  type TrackSourceRead,
} from "@kame/api-client";
import { FnButton, FnCheckbox, FnField, FnInput, FnSelect, useToast } from "@kame/ui";
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
type Autonomy = "discover" | "prepare" | "assist" | "auto_submit";

const autonomy = ref<Autonomy>("discover");
const saving = ref(false);
const preset = ref("every_2_hours");
const timezone = ref(Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
const quietStart = ref("23:00");
const quietEnd = ref("07:00");
const dailyCap = ref(12);
const addOpen = ref(false);
const adding = ref(false);
const sourcesOpen = ref(false);

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
const paused = computed(() => track.value?.status === "paused");

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
const enabledCount = computed(() => sourceRows.value.filter((r) => r.enabled).length);

const SOURCE_NAMES: Record<string, string> = {
  arbeitnow: "Arbeitnow",
  ashby: "Ashby",
  greenhouse: "Greenhouse",
  himalayas: "Himalayas",
  jobicy: "Jobicy",
  lever: "Lever",
  muse: "Muse",
  recruitee: "Recruitee",
  remoteok: "Remote OK",
  remotiv: "Remotiv",
  smartrecruiters: "SmartRecruiters",
  workable: "Workable",
};
const ATS_KEYS = new Set([
  "ashby",
  "greenhouse",
  "lever",
  "recruitee",
  "smartrecruiters",
  "workable",
]);

const sourceGroups = computed(() => {
  const buckets: Record<"ats" | "boards" | "other", TrackSourceRead[]> = {
    ats: [],
    boards: [],
    other: [],
  };
  for (const row of sourceRows.value) {
    if (ATS_KEYS.has(row.source_key)) buckets.ats.push(row);
    else if (SOURCE_NAMES[row.source_key]) buckets.boards.push(row);
    else buckets.other.push(row);
  }
  const labels = {
    ats: t("tracks.groupAts"),
    boards: t("tracks.groupBoards"),
    other: t("tracks.groupOther"),
  };
  return (["ats", "boards", "other"] as const)
    .filter((key) => buckets[key].length > 0)
    .map((key) => ({ key, label: labels[key], rows: buckets[key] }));
});

function sourceLabel(key: string): string {
  return SOURCE_NAMES[key] ?? key;
}

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

const autonomyOptions = computed<{ value: typeof autonomy.value; label: string; hint: string }[]>(
  () => [
    {
      value: "discover",
      label: t("tracks.autonomyDiscover"),
      hint: t("tracks.stepDiscover"),
    },
    {
      value: "prepare",
      label: t("tracks.autonomyPrepare"),
      hint: t("tracks.stepPrepare"),
    },
    {
      value: "assist",
      label: t("tracks.autonomyAssist"),
      hint: t("tracks.stepAssist"),
    },
    {
      value: "auto_submit",
      label: t("tracks.autonomyAuto"),
      hint: t("tracks.stepAuto"),
    },
  ],
);

watch(
  () => detail.data.value?.autonomy,
  (v) => {
    if (v) autonomy.value = v;
  },
  { immediate: true },
);

const capText = computed({
  get: () => String(dailyCap.value ?? ""),
  set: (value: string) => {
    dailyCap.value = value.trim() === "" ? 0 : Number(value);
  },
});

const presetOptions = computed(() => [
  { value: "hourly", label: t("tracks.presetHourly") },
  { value: "every_2_hours", label: t("tracks.presetEvery2h") },
  { value: "every_4_hours", label: t("tracks.presetEvery4h") },
  { value: "daily_morning", label: t("tracks.presetDaily") },
  { value: "weekdays_2h", label: t("tracks.presetWeekdays2h") },
]);

function presetLabel(value: string): string {
  return presetOptions.value.find((p) => p.value === value)?.label ?? value;
}

function scheduleMeta(row: ScheduleRead): string {
  const quiet = row.quiet_hours as { start?: string; end?: string };
  const parts: string[] = [];
  if (quiet?.start && quiet?.end) {
    parts.push(t("tracks.quietRange", { start: quiet.start, end: quiet.end }));
  }
  parts.push(t("tracks.capPerDay", { n: row.daily_cap }));
  if (row.enabled && row.next_run_at) {
    parts.push(t("tracks.nextRun", { when: fmt.dateTime(row.next_run_at) }));
  }
  return parts.join(" · ");
}

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
  const previous = track.value?.autonomy;
  try {
    await updateTrackApiV1TracksTrackIdPatch({
      path: { track_id: trackId.value },
      body: { autonomy: autonomy.value },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["track", ws.currentId, trackId.value] });
    toast.push({ title: t("common.saved"), tone: "neutral" });
  } catch (e) {
    if (previous) autonomy.value = previous;
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
    addOpen.value = false;
    toast.push({ title: t("common.saved"), tone: "neutral" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    adding.value = false;
  }
}

async function setScheduleEnabled(row: ScheduleRead, enabled: boolean) {
  try {
    await updateScheduleApiV1SchedulesScheduleIdPatch({
      path: { schedule_id: String(row.id) },
      body: { enabled },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["track-schedules", ws.currentId, trackId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
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
    if (paused.value) {
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
  <TrackShell :track-id="trackId">
    <div v-if="track" class="flex flex-col gap-6">
      <section
        class="flex flex-col gap-4 rounded-xl border border-rule bg-paper-1 p-5 shadow-[var(--shadow-card)] md:p-6"
      >
        <h2 class="text-lg font-bold text-ink-900">{{ t("tracks.autonomy") }}</h2>
        <fieldset :disabled="saving">
          <legend class="sr-only">{{ t("tracks.autonomy") }}</legend>
          <div class="grid gap-2 sm:grid-cols-2">
            <label
              v-for="(opt, i) in autonomyOptions"
              :key="opt.value"
              class="flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors"
              :class="
                autonomy === opt.value
                  ? 'border-brand-500 bg-brand-50'
                  : 'border-rule bg-paper-1 hover:border-edge'
              "
            >
              <input
                v-model="autonomy"
                type="radio"
                name="autonomy"
                class="mt-1 size-4 shrink-0 accent-brand-600"
                :value="opt.value"
                @change="saveAutonomy"
              />
              <span class="flex min-w-0 flex-col gap-1">
                <span class="flex items-baseline gap-2">
                  <span class="text-xs tabular-nums text-ink-400" aria-hidden="true">{{
                    i + 1
                  }}</span>
                  <span class="text-sm font-semibold text-ink-900">{{ opt.label }}</span>
                </span>
                <span class="text-sm text-ink-600">{{ opt.hint }}</span>
              </span>
            </label>
          </div>
        </fieldset>

        <div
          v-if="autonomy === 'auto_submit' && autoCfg.data.value"
          class="flex flex-col gap-3 rounded-lg border border-rule bg-paper-0 p-4"
        >
          <h3 class="text-sm font-semibold text-ink-900">{{ t("autoSubmit.title") }}</h3>
          <p class="text-sm text-ink-600">
            {{ t("autoSubmit.dryLeft") }} {{ autoCfg.data.value.dry_run_remaining }} ·
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
          <ul v-if="dryRuns.data.value?.length" class="flex flex-col gap-1 text-sm text-ink-600">
            <li v-for="d in dryRuns.data.value" :key="d.id">
              {{ d.would_submit ? t("autoSubmit.wouldSubmit") : t("autoSubmit.blocked") }} ·
              {{ fmt.dateTime(d.created_at) }}
            </li>
          </ul>
        </div>
      </section>

      <section
        class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-5 shadow-[var(--shadow-card)] md:p-6"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-lg font-bold text-ink-900">{{ t("tracks.sources") }}</h2>
          <div class="flex items-center gap-3">
            <span class="text-sm text-ink-600">{{
              t("tracks.sourcesOn", { on: enabledCount, total: sourceRows.length })
            }}</span>
            <button
              type="button"
              class="min-h-11 rounded-md px-3 text-sm font-semibold text-brand-700 hover:bg-paper-2"
              :aria-expanded="sourcesOpen"
              @click="sourcesOpen = !sourcesOpen"
            >
              {{ sourcesOpen ? t("common.done") : t("tracks.changeSources") }}
            </button>
          </div>
        </div>
        <div v-if="sourcesOpen" class="grid gap-5 sm:grid-cols-2">
          <div v-for="group in sourceGroups" :key="group.key" class="flex flex-col gap-1">
            <h3 class="text-xs font-semibold tracking-wide text-ink-600 uppercase">
              {{ group.label }}
            </h3>
            <label
              v-for="row in group.rows"
              :key="row.id"
              class="flex min-h-11 items-center gap-3 text-sm text-ink-900"
            >
              <input
                type="checkbox"
                class="size-5 rounded border-rule accent-brand-600"
                :checked="row.enabled"
                @change="toggleSource(row)"
              />
              {{ sourceLabel(row.source_key) }}
            </label>
          </div>
        </div>
      </section>

      <section
        class="flex flex-col gap-4 rounded-xl border border-rule bg-paper-1 p-5 shadow-[var(--shadow-card)] md:p-6"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-lg font-bold text-ink-900">{{ t("tracks.schedule") }}</h2>
          <div class="flex items-center gap-2">
            <span class="inline-flex items-center gap-1.5 text-sm text-ink-600">
              <span
                class="size-1.5 rounded-full"
                :class="paused ? 'bg-saffron-600' : 'bg-fern-600'"
                aria-hidden="true"
              />
              {{ paused ? t("tracks.paused") : t("tracks.active") }}
            </span>
            <FnButton size="sm" tone="quiet" @click="togglePause">{{
              paused ? t("tracks.resume") : t("tracks.pause")
            }}</FnButton>
          </div>
        </div>

        <p v-if="!scheduleRows.length" class="text-sm text-ink-600">
          {{ t("tracks.noSchedules") }}
        </p>
        <ul v-else class="divide-y divide-rule border-y border-rule">
          <li
            v-for="s in scheduleRows"
            :key="s.id"
            class="flex flex-wrap items-center justify-between gap-3 py-3"
          >
            <div class="flex min-w-0 flex-col gap-0.5">
              <span class="text-sm font-semibold text-ink-900"
                >{{ presetLabel(s.preset) }} · {{ s.timezone }}</span
              >
              <span class="text-xs text-ink-600">{{ scheduleMeta(s) }}</span>
              <span v-if="s.last_skip_reason" class="text-xs text-saffron-600">{{
                s.last_skip_reason
              }}</span>
            </div>
            <div class="flex items-center gap-2">
              <FnCheckbox
                :model-value="s.enabled"
                :label="s.enabled ? t('tracks.scheduleOn') : t('tracks.scheduleOff')"
                @update:model-value="(value) => setScheduleEnabled(s, Boolean(value))"
              />
              <FnButton size="sm" tone="ghost" @click="removeSchedule(String(s.id))">{{
                t("common.delete")
              }}</FnButton>
            </div>
          </li>
        </ul>

        <div v-if="addOpen" class="grid gap-4 rounded-lg border border-rule p-4 md:grid-cols-2">
          <FnField :label="t('tracks.frequency')">
            <template #default="{ id }">
              <FnSelect :id="id" v-model="preset" :options="presetOptions" />
            </template>
          </FnField>
          <FnField :label="t('profile.timezone')">
            <template #default="{ id }">
              <FnInput :id="id" v-model="timezone" />
            </template>
          </FnField>
          <FnField :label="t('tracks.quietStart')">
            <template #default="{ id }">
              <FnInput :id="id" v-model="quietStart" type="time" />
            </template>
          </FnField>
          <FnField :label="t('tracks.quietEnd')">
            <template #default="{ id }">
              <FnInput :id="id" v-model="quietEnd" type="time" />
            </template>
          </FnField>
          <FnField :label="t('tracks.dailyCap')">
            <template #default="{ id }">
              <FnInput :id="id" v-model="capText" type="number" />
            </template>
          </FnField>
          <div class="flex items-end gap-2 md:justify-end">
            <FnButton tone="ghost" @click="addOpen = false">{{ t("common.cancel") }}</FnButton>
            <FnButton tone="primary" :disabled="adding" @click="addSchedule">{{
              t("tracks.addSchedule")
            }}</FnButton>
          </div>
        </div>
        <FnButton v-else size="sm" tone="quiet" class="self-start" @click="addOpen = true">{{
          t("tracks.addSchedule")
        }}</FnButton>
      </section>
    </div>
  </TrackShell>
</template>
