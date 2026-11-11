<script setup lang="ts">
import {
  compileCriteriaApiV1TracksTrackIdCriteriaCompilePost,
  discoverNowApiV1TracksTrackIdDiscoverPost,
  getDiscoveryRunApiV1DiscoveryRunsRunIdGet,
  getTrackApiV1TracksTrackIdGet,
  listJobsApiV1JobsGet,
  putCriteriaApiV1TracksTrackIdCriteriaPut,
  runHistoryApiV1TracksTrackIdRunsGet,
  triageJobApiV1TrackJobsTrackJobIdTriagePost,
  type BoardJobRead,
  type CriteriaV1,
  type DiscoveryRunHistoryRead,
  type DiscoveryRunRead,
  type TrackDetail,
} from "@kame/api-client";
import { FnButton, FnChip, FnFolderTab, FnPencilText, FnSkeleton, useToast } from "@kame/ui";
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
const nl = ref("");
const saving = ref(false);
const compiling = ref(false);
const moreOpen = ref(false);
const diff = ref<{ label?: string; op?: string }[]>([]);
const preview = ref<CriteriaV1 | null>(null);
const running = ref(false);
const runProgress = ref<DiscoveryRunRead["progress"] | null>(null);
const runSeconds = ref(0);
let runTimer: ReturnType<typeof setInterval> | null = null;

const place = ref("");
const radiusKm = ref(25);
const regionPreset = ref("");
const visa = ref(false);
const salaryMin = ref<number | null>(null);
const salaryCurrency = ref("USD");
const salaryPeriod = ref<"hour" | "day" | "month" | "year">("month");
const includeExpr = ref("");
const excludeExpr = ref("");
const companiesInclude = ref("");
const companiesExclude = ref("");
const tzOverlap = ref(4);
const workModes = ref<string[]>([]);

const detail = useQuery({
  queryKey: computed(() => ["track", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await getTrackApiV1TracksTrackIdGet({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    return data as TrackDetail;
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});

watch(
  () => detail.data.value,
  (d) => {
    if (!d) return;
    nl.value = d.criteria.nl_text || "";
    const c = d.criteria.structured as CriteriaV1;
    place.value = c.locations?.[0]?.place ?? "";
    radiusKm.value = c.locations?.[0]?.radius_km ?? 25;
    regionPreset.value = c.remote_eligibility?.regions?.[0] ?? "";
    visa.value = c.visa_sponsorship === true;
    salaryMin.value = c.salary?.min ?? null;
    salaryCurrency.value = c.salary?.currency ?? "USD";
    salaryPeriod.value = (c.salary?.period as typeof salaryPeriod.value) ?? "month";
    includeExpr.value = c.keywords?.include_expr ?? "";
    excludeExpr.value = c.keywords?.exclude_expr ?? "";
    companiesInclude.value = (c.companies?.include ?? []).join(", ");
    companiesExclude.value = (c.companies?.exclude ?? []).join(", ");
    tzOverlap.value = c.remote_eligibility?.timezone_overlap_hours ?? 4;
    workModes.value = [...(c.work_modes ?? [])];
  },
  { immediate: true },
);

function splitCsv(raw: string): string[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

const track = computed(() => detail.data.value ?? null);
const criteria = computed(() => track.value?.criteria.structured as CriteriaV1 | undefined);
const loading = computed(
  () => !ws.loaded || detail.isPending.value || (detail.isFetching.value && !track.value),
);
const loadError = computed(() => detail.error.value);

const matched = useQuery({
  queryKey: computed(() => ["track-jobs", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await listJobsApiV1JobsGet({
      query: {
        track_id: trackId.value,
        include_not_eligible: false,
        sort: "score",
        limit: 10,
      },
      throwOnError: true,
    });
    return (data ?? []) as BoardJobRead[];
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});
const matchedJobs = computed(() => matched.data.value ?? []);

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
  refetchInterval: computed(() => (running.value ? 5000 : 30000)),
});
const lastRun = computed(() => runs.data.value?.[0] ?? null);

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

const STOP_REASONS = new Set([
  "a",
  "an",
  "and",
  "are",
  "as",
  "at",
  "be",
  "but",
  "by",
  "for",
  "from",
  "has",
  "have",
  "in",
  "is",
  "it",
  "not",
  "of",
  "on",
  "or",
  "our",
  "that",
  "the",
  "their",
  "they",
  "this",
  "to",
  "we",
  "will",
  "with",
  "you",
  "your",
]);
const REASON_COPY: Record<string, string> = {
  "Posted < 72h": "Posted recently",
  "Posted < 7d": "Posted this week",
};
function reasonText(reason: unknown): string {
  const text =
    typeof reason === "string"
      ? reason
      : reason && typeof reason === "object"
        ? String(
            (reason as { evidence?: string; signal?: string }).evidence ||
              (reason as { signal?: string }).signal ||
              "",
          )
        : "";
  const clean = text.trim();
  return STOP_REASONS.has(clean.toLowerCase()) ? "" : (REASON_COPY[clean] ?? clean);
}

async function triageMatch(id: string, action: "shortlist" | "skip") {
  try {
    await triageJobApiV1TrackJobsTrackJobIdTriagePost({
      path: { track_job_id: id },
      body: { action, skip_reason: action === "skip" ? "not a fit" : undefined },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["track-jobs", ws.currentId, trackId.value] });
    await qc.invalidateQueries({ queryKey: ["home", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function runNow() {
  running.value = true;
  runProgress.value = null;
  try {
    const { data } = await discoverNowApiV1TracksTrackIdDiscoverPost({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    runProgress.value = data?.progress ?? null;
    // Deployed runs are queued and finish in a worker; poll until it stops changing.
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
    await qc.invalidateQueries({ queryKey: ["track-jobs", ws.currentId, trackId.value] });
    await qc.invalidateQueries({ queryKey: ["track-runs", ws.currentId, trackId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    running.value = false;
  }
}

function hue(n: number): 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 {
  return Math.min(8, Math.max(1, n || 1)) as 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
}

async function invalidate() {
  await qc.invalidateQueries({ queryKey: ["track", ws.currentId, trackId.value] });
  await qc.invalidateQueries({ queryKey: ["tracks", ws.currentId] });
}

async function saveCriteria(next: CriteriaV1) {
  saving.value = true;
  try {
    await putCriteriaApiV1TracksTrackIdCriteriaPut({
      path: { track_id: trackId.value },
      body: { criteria: next, nl_text: nl.value },
      throwOnError: true,
    });
    await invalidate();
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    saving.value = false;
  }
}

async function compile(apply: boolean) {
  if (!nl.value.trim()) return;
  compiling.value = true;
  try {
    const { data } = await compileCriteriaApiV1TracksTrackIdCriteriaCompilePost({
      path: { track_id: trackId.value },
      body: { text: nl.value, apply },
      throwOnError: true,
    });
    diff.value = data?.diff ?? [];
    preview.value = data?.criteria ?? null;
    if (apply) {
      await invalidate();
      toast.push({ title: t("common.saved"), tone: "neutral" });
    }
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    compiling.value = false;
  }
}

async function removeMustSkill(skill: string) {
  const c = criteria.value;
  if (!c) return;
  await saveCriteria({
    ...c,
    skills: {
      must: (c.skills?.must ?? []).filter((s) => s !== skill),
      nice: c.skills?.nice ?? [],
      exclude: c.skills?.exclude ?? [],
    },
  });
}

async function toggleAgencies() {
  const c = criteria.value;
  if (!c) return;
  await saveCriteria({
    ...c,
    companies: {
      include: c.companies?.include ?? [],
      exclude: c.companies?.exclude ?? [],
      sizes: c.companies?.sizes ?? [],
      industries: c.companies?.industries ?? [],
      stages: c.companies?.stages ?? [],
      exclude_agencies: !c.companies?.exclude_agencies,
    },
  });
}

function toggleMode(mode: string) {
  if (workModes.value.includes(mode)) {
    workModes.value = workModes.value.filter((m) => m !== mode);
  } else {
    workModes.value = [...workModes.value, mode];
  }
}

async function saveMore() {
  const c = criteria.value;
  if (!c) return;
  const regions = regionPreset.value ? [regionPreset.value] : (c.remote_eligibility?.regions ?? []);
  const locations = place.value.trim()
    ? [{ place: place.value.trim(), radius_km: radiusKm.value || null }]
    : [];
  await saveCriteria({
    ...c,
    work_modes: workModes.value as CriteriaV1["work_modes"],
    visa_sponsorship: visa.value ? true : null,
    locations,
    remote_eligibility: {
      anywhere: c.remote_eligibility?.anywhere ?? false,
      regions,
      countries: c.remote_eligibility?.countries ?? [],
      timezone_overlap_hours: tzOverlap.value,
      base_tz: c.remote_eligibility?.base_tz ?? null,
    },
    salary:
      salaryMin.value != null
        ? {
            min: salaryMin.value,
            max: null,
            currency: salaryCurrency.value,
            period: salaryPeriod.value,
            hide_unspecified: c.salary?.hide_unspecified ?? false,
          }
        : null,
    keywords: {
      include_expr: includeExpr.value.trim() || null,
      exclude_expr: excludeExpr.value.trim() || null,
    },
    companies: {
      include: splitCsv(companiesInclude.value),
      exclude: splitCsv(companiesExclude.value),
      sizes: c.companies?.sizes ?? [],
      industries: c.companies?.industries ?? [],
      stages: c.companies?.stages ?? [],
      exclude_agencies: c.companies?.exclude_agencies ?? false,
    },
  });
  toast.push({ title: t("common.saved"), tone: "neutral" });
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 md:px-6">
    <div v-if="loading" class="flex flex-col gap-3">
      <FnSkeleton class="h-10 w-64" />
      <FnSkeleton class="h-40 w-full" />
    </div>
    <p v-else-if="loadError" class="text-sm text-ink-600">{{ apiError(loadError) }}</p>
    <template v-else-if="track">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0 flex-1">
          <FnFolderTab :hue="hue(track.color_hue)" active>{{ track.name }}</FnFolderTab>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <FnButton tone="primary" :disabled="running" @click="runNow">{{
            running ? t("tracks.running") : t("tracks.runNow")
          }}</FnButton>
          <NuxtLink
            :to="`/jobs?track=${trackId}`"
            class="min-h-11 px-3 text-sm font-medium text-persimmon-700 underline-offset-2 hover:underline"
            >{{ t("tracks.viewMatches") }}</NuxtLink
          >
          <details class="relative text-sm">
            <summary
              class="flex min-h-11 cursor-pointer list-none items-center px-3 text-ink-600 hover:text-ink-900"
            >
              {{ t("tracks.moreTools") }}
            </summary>
            <div
              class="absolute right-0 z-10 mt-1 flex min-w-40 flex-col rounded-md border border-rule bg-paper-1 p-1 shadow-[var(--shadow-float)]"
            >
              <NuxtLink
                :to="`/tracks/${trackId}/be-found`"
                class="flex min-h-11 items-center rounded-sm px-3 hover:bg-paper-2"
                >{{ t("beFound.title") }}</NuxtLink
              >
              <NuxtLink
                :to="`/tracks/${trackId}/gaps`"
                class="flex min-h-11 items-center rounded-sm px-3 hover:bg-paper-2"
                >{{ t("gaps.title") }}</NuxtLink
              >
              <NuxtLink
                :to="`/tracks/${trackId}/settings`"
                class="flex min-h-11 items-center rounded-sm px-3 hover:bg-paper-2"
                >{{ t("tracks.settings") }}</NuxtLink
              >
            </div>
          </details>
        </div>
      </div>
      <div v-if="running" class="flex flex-col gap-1" role="status">
        <p class="flex items-center gap-2 text-sm text-ink-600">
          <span class="size-2 animate-pulse rounded-full bg-persimmon-500" aria-hidden="true" />
          Searching company boards · {{ runSeconds }}s
        </p>
        <p v-if="runProgress" class="text-sm text-ink-600">
          {{
            t("tracks.runProgress", {
              boards: runProgress.boards_checked ?? 0,
              found: runProgress.jobs_found ?? 0,
              new: runProgress.jobs_new ?? 0,
              linked: runProgress.linked ?? 0,
            })
          }}
        </p>
      </div>
      <div v-else-if="lastRun" class="flex flex-wrap items-center gap-2 text-sm text-ink-600">
        <span>
          Last search {{ fmt.dateTime(lastRun.started_at || lastRun.created_at) }} ·
          {{ lastRun.progress?.linked ? `${lastRun.progress.linked} new` : t("tracks.noNewJobs") }}
        </span>
        <NuxtLink :to="`/tracks/${trackId}/runs`" class="text-persimmon-700 underline">{{
          t("tracks.runHistory")
        }}</NuxtLink>
      </div>
      <section class="flex flex-col gap-2" :aria-label="t('tracks.matchedJobs')">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("tracks.matchedJobs") }}
          </h2>
          <NuxtLink
            :to="`/jobs?track=${trackId}`"
            class="text-sm text-ink-600 underline-offset-2 hover:underline"
            >{{ t("today.viewAll") }}</NuxtLink
          >
        </div>
        <p v-if="!matchedJobs.length" class="text-sm text-ink-600">{{ t("tracks.noJobs") }}</p>
        <ul v-else class="divide-y divide-rule border-y border-rule">
          <li
            v-for="j in matchedJobs"
            :key="j.id"
            class="flex flex-wrap items-center gap-2 py-3 text-sm"
          >
            <span class="font-mono text-xs tabular-nums text-persimmon-700">{{
              j.score != null ? Math.round(j.score) : "-"
            }}</span>
            <div class="min-w-0 flex-1">
              <p class="font-medium text-ink-900">{{ j.title }}</p>
              <p class="text-ink-600">
                {{ j.company_name }}
                <span
                  v-for="r in (j.reasons || []).slice(0, 2)"
                  :key="String(r)"
                  class="ml-1 text-ink-500"
                  >· {{ reasonText(r) }}</span
                >
              </p>
            </div>
            <div class="flex items-center gap-1">
              <FnButton size="sm" tone="ghost" @click="triageMatch(j.id, 'shortlist')"
                >Shortlist</FnButton
              >
              <FnButton size="sm" tone="ghost" @click="triageMatch(j.id, 'skip')">Skip</FnButton>
              <a
                v-if="j.apply_url"
                :href="j.apply_url"
                class="min-h-11 px-2 text-sm text-ink-900 underline-offset-2 hover:underline"
                rel="noopener noreferrer"
                target="_blank"
                >{{ t("applications.openPosting") }}</a
              >
            </div>
          </li>
        </ul>
      </section>

      <nav class="flex flex-wrap gap-1 border-b border-rule" :aria-label="t('tracks.sections')">
        <span class="relative px-3 py-2 text-sm font-medium text-ink-900"
          >{{ t("tracks.criteria")
          }}<span class="absolute inset-x-2 bottom-0 h-0.5 bg-ink-900" aria-hidden="true"
        /></span>
        <NuxtLink
          :to="`/tracks/${trackId}/runs`"
          class="px-3 py-2 text-sm text-ink-600 hover:text-ink-900"
          >{{ t("tracks.runHistory") }}</NuxtLink
        >
        <NuxtLink
          :to="`/tracks/${trackId}/settings`"
          class="px-3 py-2 text-sm text-ink-600 hover:text-ink-900"
          >{{ t("tracks.settings") }}</NuxtLink
        >
      </nav>

      <section class="flex flex-col gap-3">
        <label class="flex flex-col gap-1 text-sm">
          <span class="text-ink-600">{{ t("tracks.describe") }}</span>
          <textarea
            v-model="nl"
            class="min-h-28 border border-rule bg-paper-0 px-3 py-2 text-ink-900"
            maxlength="8000"
          ></textarea>
        </label>
        <div class="flex flex-wrap gap-2">
          <FnButton tone="primary" :disabled="compiling" @click="compile(false)">{{
            t("tracks.update")
          }}</FnButton>
          <FnButton v-if="preview" tone="ghost" :disabled="compiling" @click="compile(true)">{{
            t("tracks.applyDiff")
          }}</FnButton>
        </div>
        <ul v-if="diff.length" class="flex flex-col gap-1 text-sm">
          <li v-for="(d, i) in diff" :key="i">
            <FnPencilText>{{ d.label || d.op }}</FnPencilText>
          </li>
        </ul>
      </section>

      <section class="flex flex-col gap-3" :aria-label="t('tracks.chips')">
        <div class="flex flex-wrap gap-2">
          <FnChip
            v-for="title in criteria?.titles?.filter((x) => !x.exclude) ?? []"
            :key="title.title"
            tone="accent"
            >{{ title.title }}</FnChip
          >
          <FnChip
            v-for="s in criteria?.skills?.must ?? []"
            :key="`m-${s}`"
            tone="neutral"
            removable
            :remove-label="t('tracks.removeChip')"
            @remove="removeMustSkill(s)"
            >{{ s }}</FnChip
          >
          <FnChip v-for="s in criteria?.skills?.nice ?? []" :key="`n-${s}`" tone="pencil">{{
            s
          }}</FnChip>
          <FnChip
            v-if="criteria?.companies?.exclude_agencies"
            tone="neutral"
            removable
            :remove-label="t('tracks.removeChip')"
            @remove="toggleAgencies"
            >{{ t("tracks.noAgencies") }}</FnChip
          >
          <button
            v-else
            type="button"
            class="min-h-11 text-sm text-ink-600 underline-offset-2 hover:underline"
            @click="toggleAgencies"
          >
            {{ t("tracks.noAgencies") }}
          </button>
        </div>
        <p class="text-sm text-ink-600">{{ t("tracks.criteriaHint") }}</p>
      </section>

      <section class="flex flex-col gap-3 border-t border-rule pt-4">
        <button
          type="button"
          class="min-h-11 self-start text-sm font-medium text-ink-900"
          :aria-expanded="moreOpen"
          @click="moreOpen = !moreOpen"
        >
          {{ moreOpen ? t("tracks.hideFilters") : t("tracks.moreFilters") }}
        </button>
        <div v-if="moreOpen" class="grid gap-4 md:grid-cols-2">
          <fieldset class="flex flex-col gap-2">
            <legend class="text-sm text-ink-600">{{ t("tracks.workModes") }}</legend>
            <label v-for="m in ['remote', 'hybrid', 'on_site']" :key="m" class="flex gap-2 text-sm">
              <input type="checkbox" :checked="workModes.includes(m)" @change="toggleMode(m)" />
              {{ t(`tracks.mode_${m}`) }}
            </label>
          </fieldset>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-ink-600">{{ t("tracks.location") }}</span>
            <input
              v-model="place"
              type="text"
              class="min-h-11 border border-rule bg-paper-0 px-3"
              maxlength="200"
            />
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-ink-600">{{ t("tracks.radius") }}</span>
            <input
              v-model.number="radiusKm"
              type="number"
              min="1"
              max="500"
              class="min-h-11 border border-rule bg-paper-0 px-3"
            />
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-ink-600">{{ t("tracks.region") }}</span>
            <select v-model="regionPreset" class="min-h-11 border border-rule bg-paper-0 px-3">
              <option value="">{{ t("tracks.regionAny") }}</option>
              <option
                v-for="r in ['APAC', 'EU', 'LATAM', 'MENA', 'NA', 'AFRICA']"
                :key="r"
                :value="r"
              >
                {{ r }}
              </option>
            </select>
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-ink-600">{{ t("tracks.tzOverlap") }}</span>
            <input v-model.number="tzOverlap" type="range" min="0" max="12" class="min-h-11" />
            <span class="font-mono text-xs text-ink-600">{{ tzOverlap }}h</span>
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="visa" type="checkbox" />
            {{ t("tracks.visa") }}
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-ink-600">{{ t("tracks.salaryMin") }}</span>
            <input
              v-model.number="salaryMin"
              type="number"
              min="0"
              class="min-h-11 border border-rule bg-paper-0 px-3"
            />
          </label>
          <div class="flex gap-2">
            <label class="flex flex-1 flex-col gap-1 text-sm">
              <span class="text-ink-600">{{ t("tracks.currency") }}</span>
              <input
                v-model="salaryCurrency"
                type="text"
                maxlength="3"
                class="min-h-11 border border-rule bg-paper-0 px-3 uppercase"
              />
            </label>
            <label class="flex flex-1 flex-col gap-1 text-sm">
              <span class="text-ink-600">{{ t("tracks.period") }}</span>
              <select v-model="salaryPeriod" class="min-h-11 border border-rule bg-paper-0 px-3">
                <option value="hour">hour</option>
                <option value="day">day</option>
                <option value="month">month</option>
                <option value="year">year</option>
              </select>
            </label>
          </div>
          <label class="flex flex-col gap-1 text-sm md:col-span-2">
            <span class="text-ink-600">{{ t("tracks.keywordsInclude") }}</span>
            <input
              v-model="includeExpr"
              type="text"
              class="min-h-11 border border-rule bg-paper-0 px-3 font-mono text-sm"
              maxlength="2000"
            />
          </label>
          <label class="flex flex-col gap-1 text-sm md:col-span-2">
            <span class="text-ink-600">{{ t("tracks.keywordsExclude") }}</span>
            <input
              v-model="excludeExpr"
              type="text"
              class="min-h-11 border border-rule bg-paper-0 px-3 font-mono text-sm"
              maxlength="2000"
            />
          </label>
          <label class="flex flex-col gap-1 text-sm md:col-span-2">
            <span class="text-ink-600">{{ t("tracks.companiesInclude") }}</span>
            <input
              v-model="companiesInclude"
              type="text"
              class="min-h-11 border border-rule bg-paper-0 px-3 text-sm"
              maxlength="2000"
            />
          </label>
          <label class="flex flex-col gap-1 text-sm md:col-span-2">
            <span class="text-ink-600">{{ t("tracks.companiesExclude") }}</span>
            <input
              v-model="companiesExclude"
              type="text"
              class="min-h-11 border border-rule bg-paper-0 px-3 text-sm"
              maxlength="2000"
            />
          </label>
          <FnButton tone="primary" class="self-start" :disabled="saving" @click="saveMore">{{
            t("common.save")
          }}</FnButton>
        </div>
      </section>
    </template>
  </div>
</template>
