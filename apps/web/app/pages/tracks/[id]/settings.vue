<script setup lang="ts">
import {
  createScheduleApiV1TracksTrackIdSchedulesPost,
  deleteScheduleApiV1SchedulesScheduleIdDelete,
  getTrackApiV1TracksTrackIdGet,
  listSchedulesApiV1TracksTrackIdSchedulesGet,
  recommendedSettingsApiV1TracksTrackIdRecommendedSettingsGet,
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
import {
  FnButton,
  FnCheckbox,
  FnChoiceCards,
  FnField,
  FnInput,
  FnSectionCard,
  FnSelect,
  FnSkeleton,
  FnSkeletonGroup,
  useToast,
  type SelectOption,
} from "@kame/ui";
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

const autonomy = ref<Autonomy>("prepare");
const saving = ref(false);
const preset = ref("every_4_hours");
const timezone = ref(Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
const quietStart = ref("22:00");
const quietEnd = ref("07:00");
const dailyCap = ref(12);
const addOpen = ref(false);
const adding = ref(false);
const sourcesOpen = ref(false);
const applyingRec = ref(false);

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
  muse: "The Muse",
  recruitee: "Recruitee",
  remoteok: "Remote OK",
  remotiv: "Remotiv",
  smartrecruiters: "SmartRecruiters",
  workable: "Workable",
};
const CAREER_SITE_KEYS = new Set([
  "ashby",
  "greenhouse",
  "lever",
  "recruitee",
  "smartrecruiters",
  "workable",
]);

const sourceGroups = computed(() => {
  const buckets: Record<"career" | "boards" | "other", TrackSourceRead[]> = {
    career: [],
    boards: [],
    other: [],
  };
  for (const row of sourceRows.value) {
    if (CAREER_SITE_KEYS.has(row.source_key)) buckets.career.push(row);
    else if (SOURCE_NAMES[row.source_key]) buckets.boards.push(row);
    else buckets.other.push(row);
  }
  const labels = {
    career: t("tracks.groupAts"),
    boards: t("tracks.groupBoards"),
    other: t("tracks.groupOther"),
  };
  return (["boards", "career", "other"] as const)
    .filter((key) => buckets[key].length > 0)
    .map((key) => ({ key, label: labels[key], rows: buckets[key] }));
});

function sourceLabel(key: string): string {
  return SOURCE_NAMES[key] ?? key;
}

const recommended = useQuery({
  queryKey: computed(() => ["track-recommendation", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await recommendedSettingsApiV1TracksTrackIdRecommendedSettingsGet({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});

async function applyRecommended() {
  const row = recommended.data.value;
  if (!row) return;
  applyingRec.value = true;
  try {
    await updateTrackApiV1TracksTrackIdPatch({
      path: { track_id: trackId.value },
      body: { autonomy: row.autonomy },
      throwOnError: true,
    });
    autonomy.value = row.autonomy;
    const body = {
      preset: row.preset as
        "hourly" | "every_2_hours" | "every_4_hours" | "daily_morning" | "weekdays_2h" | "custom",
      timezone: row.timezone,
      quiet_hours: {
        start: String((row.quiet_hours as Record<string, unknown>).start ?? "22:00"),
        end: String((row.quiet_hours as Record<string, unknown>).end ?? "07:00"),
      },
      daily_cap: row.daily_cap,
    };
    const existing = firstSchedule.value;
    if (existing) {
      await updateScheduleApiV1SchedulesScheduleIdPatch({
        path: { schedule_id: String(existing.id) },
        body,
        throwOnError: true,
      });
    } else {
      await createScheduleApiV1TracksTrackIdSchedulesPost({
        path: { track_id: trackId.value },
        body,
        throwOnError: true,
      });
    }
    await qc.invalidateQueries({ queryKey: ["track", ws.currentId, trackId.value] });
    await qc.invalidateQueries({ queryKey: ["track-schedules", ws.currentId, trackId.value] });
    await qc.invalidateQueries({ queryKey: ["track-recommendation", ws.currentId, trackId.value] });
    toast.push({ title: t("common.saved"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    applyingRec.value = false;
  }
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
const firstSchedule = computed(() => scheduleRows.value[0] ?? null);

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

const autonomyOptions = computed(() => [
  {
    value: "discover",
    title: t("tracks.autonomyDiscover"),
    effect: t("tracks.stepDiscover"),
  },
  {
    value: "prepare",
    title: t("tracks.autonomyPrepare"),
    effect: t("tracks.stepPrepare"),
    badge: t("tracks.recommended"),
  },
  {
    value: "assist",
    title: t("tracks.autonomyAssist"),
    effect: t("tracks.stepAssist"),
  },
  {
    value: "auto_submit",
    title: t("tracks.autonomyAuto"),
    effect: t("tracks.stepAuto"),
    badge: t("tracks.advanced"),
  },
]);

const howMuchSummary = computed(() => {
  if (autonomy.value === "discover") return t("tracks.summaryDiscover");
  if (autonomy.value === "assist") return t("tracks.summaryAssist");
  if (autonomy.value === "auto_submit") return t("autoSubmit.reviewBefore");
  return t("tracks.summaryPrepare");
});

watch(
  () => detail.data.value?.autonomy,
  (v) => {
    if (v) autonomy.value = v;
  },
  { immediate: true },
);

const capText = computed({
  get: () => String(dailyCap.value ?? ""),
  set: (value: string | number) => {
    const text = String(value ?? "");
    dailyCap.value = text.trim() === "" ? 0 : Number(text);
  },
});

const presetOptions = computed(() => [
  { value: "every_4_hours", label: t("tracks.presetEvery4h") },
  { value: "every_2_hours", label: t("tracks.presetEvery2h") },
  { value: "daily_morning", label: t("tracks.presetDaily") },
  { value: "weekdays_2h", label: t("tracks.presetWeekdays2h") },
  { value: "hourly", label: t("tracks.presetHourly") },
]);

const timezoneOptions = computed<SelectOption[]>(() => {
  const here = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  const all = (
    typeof Intl.supportedValuesOf === "function"
      ? Intl.supportedValuesOf("timeZone")
      : [here, "UTC"]
  ).slice();
  if (!all.includes(here)) all.unshift(here);
  return all.map((z) => ({ value: z, label: z.replaceAll("_", " ") }));
});

function presetLabel(value: string): string {
  return presetOptions.value.find((p) => p.value === value)?.label ?? value;
}

function scheduleMeta(row: ScheduleRead): string {
  const quiet = row.quiet_hours as { start?: string; end?: string };
  const parts: string[] = [];
  if (quiet?.start && quiet?.end)
    parts.push(t("tracks.quietRange", { start: quiet.start, end: quiet.end }));
  parts.push(t("tracks.capPerDay", { n: row.daily_cap }));
  if (row.enabled && row.next_run_at)
    parts.push(t("tracks.nextRun", { when: fmt.dateTime(row.next_run_at) }));
  return parts.join(" · ");
}

const scheduleSummary = computed(() => {
  const row = firstSchedule.value;
  if (!row) return undefined;
  const quiet = row.quiet_hours as { start?: string; end?: string };
  const parts = [presetLabel(row.preset).toLowerCase()];
  if (quiet?.start && quiet?.end)
    parts.push(t("tracks.quietRange", { start: quiet.start, end: quiet.end }));
  parts.push(t("tracks.capPerDay", { n: row.daily_cap }));
  parts.push(row.timezone);
  return `${t("tracks.weCheck")} ${parts.join(", ")}.`;
});

const sourcesSummary = computed(() =>
  t("tracks.sourcesSummary", { n: enabledCount.value }, enabledCount.value),
);

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
    <div v-if="track" class="flex flex-col gap-5">
      <FnSkeletonGroup
        v-if="recommended.isPending.value"
        :label="t('common.loading')"
        class="flex flex-col gap-3 rounded-xl border border-brand-200 bg-brand-50 p-4 sm:p-5"
      >
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div class="flex min-w-0 flex-1 flex-col gap-2">
            <FnSkeleton class="h-3 w-40" />
            <FnSkeleton class="h-5 w-3/4 max-w-md" />
          </div>
          <FnSkeleton class="h-11 w-32 shrink-0 rounded-md" />
        </div>
        <FnSkeleton class="h-3.5 w-4/5" />
      </FnSkeletonGroup>

      <section
        v-else-if="recommended.data.value"
        class="flex flex-col gap-3 rounded-xl border border-brand-200 bg-brand-50 p-4 sm:p-5"
      >
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div class="flex flex-col gap-1">
            <p class="text-xs font-bold tracking-[0.12em] text-brand-700 uppercase">
              {{ t("tracks.recommendedForSearch") }}
            </p>
            <p class="text-base font-semibold text-ink-900">
              {{
                t("tracks.recommendedLine", {
                  preset:
                    presetOptions.find((p) => p.value === recommended.data.value?.preset)?.label ??
                    "",
                  level:
                    autonomyOptions.find((o) => o.value === recommended.data.value?.autonomy)
                      ?.title ?? "",
                  cap: recommended.data.value.daily_cap,
                })
              }}
            </p>
          </div>
          <FnButton tone="primary" size="sm" :loading="applyingRec" @click="applyRecommended">
            {{ t("tracks.useRecommended") }}
          </FnButton>
        </div>
        <ul class="flex flex-col gap-1 text-sm text-ink-600">
          <li v-for="reason in recommended.data.value.reasons" :key="reason">· {{ reason }}</li>
        </ul>
      </section>
      <FnSectionCard
        :title="t('tracks.autonomy')"
        :intro="t('tracks.howMuchIntro')"
        :summary="howMuchSummary"
      >
        <FnChoiceCards
          v-model="autonomy"
          :options="autonomyOptions"
          :label="t('tracks.autonomy')"
          :columns="2"
          @update:model-value="saveAutonomy"
        />

        <div
          v-if="autonomy === 'auto_submit' && autoCfg.data.value"
          class="flex flex-col gap-3 rounded-lg border border-rule bg-paper-0 p-4"
        >
          <h3 class="text-sm font-semibold text-ink-900">{{ t("autoSubmit.title") }}</h3>
          <p class="text-sm text-ink-600">{{ t("autoSubmit.practiceExplainer") }}</p>
          <dl class="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt class="text-ink-600">{{ t("autoSubmit.practiceRuns") }}</dt>
              <dd class="font-semibold tabular-nums">
                {{ Math.max(0, 3 - (autoCfg.data.value.dry_run_remaining ?? 0)) }} of 3 done
              </dd>
            </div>
            <div>
              <dt class="text-ink-600">{{ t("autoSubmit.threshold") }}</dt>
              <dd class="font-semibold tabular-nums">
                {{ Math.round((autoCfg.data.value.score_threshold ?? 0.85) * 100) }}
              </dd>
            </div>
          </dl>
          <div class="flex flex-wrap gap-2">
            <FnButton
              size="sm"
              tone="primary"
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
          <p class="text-sm text-ink-600">{{ t("autoSubmit.alwaysManual") }}</p>
          <ul v-if="dryRuns.data.value?.length" class="flex flex-col gap-1 text-sm text-ink-600">
            <li v-for="d in dryRuns.data.value" :key="d.id">
              {{ d.would_submit ? t("autoSubmit.wouldSubmit") : t("autoSubmit.blocked") }} ·
              {{ fmt.dateTime(d.created_at) }}
            </li>
          </ul>
        </div>
      </FnSectionCard>

      <FnSectionCard
        :title="t('tracks.schedule')"
        :intro="t('tracks.scheduleIntro')"
        :summary="scheduleSummary"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
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

        <FnSkeletonGroup v-if="schedules.isPending.value" :label="t('common.loading')">
          <ul class="divide-y divide-rule border-y border-rule">
            <li
              v-for="n in 2"
              :key="n"
              class="flex flex-wrap items-center justify-between gap-3 py-3"
            >
              <div class="flex min-w-0 flex-1 flex-col gap-2">
                <FnSkeleton class="h-4 w-2/5" />
                <FnSkeleton class="h-3 w-1/3" />
              </div>
              <div class="flex items-center gap-2">
                <FnSkeleton class="h-6 w-14 rounded-full" />
                <FnSkeleton class="h-11 w-20 rounded-md" />
              </div>
            </li>
          </ul>
        </FnSkeletonGroup>

        <p v-else-if="!scheduleRows.length" class="text-sm text-ink-600">
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
                >{{ presetLabel(s.preset) }} · {{ s.timezone.replaceAll("_", " ") }}</span
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

        <div v-if="addOpen" class="grid gap-4 rounded-lg border border-rule p-4 sm:grid-cols-2">
          <FnField v-slot="{ id }" :label="t('tracks.frequency')">
            <FnSelect :id="id" v-model="preset" :options="presetOptions" />
          </FnField>
          <FnField v-slot="{ id }" :label="t('profile.timezone')" :help="t('tracks.timezoneHelp')">
            <FnSelect :id="id" v-model="timezone" :options="timezoneOptions" />
          </FnField>
          <FnField v-slot="{ id }" :label="t('tracks.quietStart')">
            <FnInput :id="id" v-model="quietStart" type="time" />
          </FnField>
          <FnField v-slot="{ id }" :label="t('tracks.quietEnd')">
            <FnInput :id="id" v-model="quietEnd" type="time" />
          </FnField>
          <FnField v-slot="{ id }" :label="t('tracks.dailyCap')" :help="t('tracks.dailyCapHelp')">
            <FnInput :id="id" v-model="capText" type="number" inputmode="numeric" />
          </FnField>
          <div class="flex items-end gap-2 sm:justify-end">
            <FnButton tone="ghost" @click="addOpen = false">{{ t("common.cancel") }}</FnButton>
            <FnButton tone="primary" :disabled="adding" @click="addSchedule">{{
              t("tracks.addSchedule")
            }}</FnButton>
          </div>
        </div>
        <FnButton v-else size="sm" tone="quiet" class="self-start" @click="addOpen = true">{{
          t("tracks.addSchedule")
        }}</FnButton>
      </FnSectionCard>

      <FnSectionCard
        :title="t('tracks.sources')"
        :intro="t('tracks.sourcesIntro')"
        :summary="sourcesSummary"
      >
        <template #actions>
          <button
            type="button"
            class="min-h-11 rounded-md px-3 text-sm font-semibold text-brand-700 hover:bg-paper-2"
            :aria-expanded="sourcesOpen"
            @click="sourcesOpen = !sourcesOpen"
          >
            {{ sourcesOpen ? t("common.done") : t("tracks.changeSources") }}
          </button>
        </template>
        <FnSkeletonGroup
          v-if="sourcesOpen && sources.isPending.value"
          :label="t('common.loading')"
          class="flex flex-col gap-4 sm:grid sm:grid-cols-2"
        >
          <div v-for="n in 2" :key="n" class="flex flex-col gap-2">
            <FnSkeleton class="h-3 w-24" />
            <FnSkeleton v-for="row in 4" :key="row" class="h-6 w-3/5" />
          </div>
        </FnSkeletonGroup>
        <div v-else-if="sourcesOpen" class="flex flex-col gap-4 sm:grid sm:grid-cols-2">
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
      </FnSectionCard>
    </div>
  </TrackShell>
</template>
