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
  client,
  type BoardJobRead,
  type CriteriaV1,
  type DiscoveryRunHistoryRead,
  type DiscoveryRunRead,
  type TrackDetail,
} from "@kame/api-client";
import { FnButton, FnChip, FnFolderTab, FnPencilText, FnSkeleton, useToast } from "@kame/ui";
import type { Ref } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useExperience } from "~/composables/useExperience";
import type { Facet } from "~/composables/useExperience";
import { useWorkspaceStore } from "~/stores/workspace";

const route = useRoute();
const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const fmt = useFormat();
const exp = useExperience();

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
const shifts = ref<string[]>([]);
const employmentTypes = ref<string[]>([]);
const salaryIncludes = ref<string[]>([]);
const relocation = ref(false);
const postingAge = ref<number | null>(null);
const facetValues = ref<Record<string, string[]>>({});
const showAll = ref(false);
const languagesDraft = ref("");
const educationDraft = ref("");
const clearanceDraft = ref("");
const minScoreDraft = ref<number | null>(null);

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

function splitCsv(raw: string): string[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

const track = computed(() => detail.data.value ?? null);
const criteria = computed(() => track.value?.criteria.structured as CriteriaV1 | undefined);
const industry = computed(() => track.value?.industry || exp.primary.value);
const manifest = computed(() => exp.manifestFor(industry.value));
const facets = computed(() => exp.facetsFor(industry.value));

function stateOf(field: string): "visible" | "collapsed" | "hidden" {
  return exp.stateOf(field, industry.value);
}

function labelFor(field: string, fallback: string): string {
  return exp.labelOf(field, industry.value, t(fallback));
}

function showField(field: string): boolean {
  return stateOf(field) === "visible" || showAll.value;
}

function toggleShowAll() {
  showAll.value = !showAll.value;
  if (showAll.value) moreOpen.value = true;
}

function inMore(field: string): boolean {
  return stateOf(field) === "collapsed";
}

const hiddenWithValues = computed(() => {
  const c = criteria.value;
  if (!c) return [] as string[];
  const out: string[] = [];
  const rem = c.remote_eligibility;
  if (
    stateOf("remote_eligibility") === "hidden" &&
    rem &&
    (rem.anywhere || rem.regions?.length || rem.countries?.length)
  ) {
    out.push(labelFor("remote_eligibility", "tracks.tzOverlap"));
  }
  if (stateOf("education") === "hidden" && c.education) {
    out.push(labelFor("education", "tracks.education"));
  }
  if (stateOf("clearance") === "hidden" && c.clearance) {
    out.push(labelFor("clearance", "tracks.clearance"));
  }
  return out;
});

const loading = computed(
  () => !ws.loaded || detail.isPending.value || (detail.isFetching.value && !track.value),
);
const loadError = computed(() => detail.error.value);

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
    shifts.value = [...(c.shifts ?? [])];
    employmentTypes.value = [...(c.employment_types ?? [])];
    salaryIncludes.value = [...(c.salary?.includes ?? [])];
    relocation.value = c.relocation === true;
    postingAge.value = c.posting_max_age_days ?? null;
    languagesDraft.value = (c.languages ?? []).join(", ");
    educationDraft.value = c.education ?? "";
    clearanceDraft.value = c.clearance ?? "";
    minScoreDraft.value = c.min_match_score ?? null;
    hydrateFacets(c);
  },
  { immediate: true },
);

function hydrateFacets(c: CriteriaV1) {
  const next: Record<string, string[]> = {};
  for (const facet of facets.value) {
    const raw = (c.facets ?? {})[facet.key];
    next[facet.key] = Array.isArray(raw) ? [...raw] : [];
  }
  facetValues.value = next;
}

watch(facets, () => {
  const c = criteria.value;
  if (c) hydrateFacets(c);
});

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

type Coverage = {
  industry: string;
  country: string;
  level: "strong" | "partial" | "thin" | "none";
  note: string;
};
type WhereLook = {
  industry: string;
  queries: { keywords: string; location: string; country: string; category: string | null }[];
  adapters: { key: string; name: string; configured: boolean; terms_note: string }[];
  alerts: string[];
};

const coverageCountry = computed(
  () => criteria.value?.locations?.[0]?.country?.toUpperCase() ?? "",
);
const coveragePlace = computed(
  () => criteria.value?.locations?.[0]?.place || coverageCountry.value,
);
const coverage = useQuery({
  queryKey: computed(() => ["coverage", industry.value, coverageCountry.value]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/sources/coverage",
      query: { industry: industry.value, country: coverageCountry.value },
      throwOnError: true,
    });
    return data as Coverage;
  },
  enabled: computed(() => Boolean(ws.currentId && coverageCountry.value && industry.value)),
});
const whereLook = useQuery({
  queryKey: computed(() => ["track-where", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await client.get({
      url: `/api/v1/tracks/${trackId.value}/where`,
      throwOnError: true,
    });
    return data as WhereLook;
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});
const thinCoverage = computed(() =>
  Boolean(
    coverage.data.value && coverage.data.value.level !== "strong" && matchedJobs.value.length < 5,
  ),
);

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
  "can",
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
  await qc.invalidateQueries({ queryKey: ["track-where", ws.currentId, trackId.value] });
  await qc.invalidateQueries({ queryKey: ["coverage"] });
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

function toggleValue(list: Ref<string[]>, value: string) {
  list.value = list.value.includes(value)
    ? list.value.filter((item) => item !== value)
    : [...list.value, value];
}

function toggleShift(value: string) {
  toggleValue(shifts, value);
}

function toggleEmployment(value: string) {
  toggleValue(employmentTypes, value);
}

function toggleInclude(value: string) {
  toggleValue(salaryIncludes, value);
}

function toggleFacet(facet: Facet, option: string) {
  const current = facetValues.value[facet.key] ?? [];
  let next: string[];
  if (facet.kind === "single") {
    next = current.includes(option) ? [] : [option];
  } else {
    next = current.includes(option)
      ? current.filter((item) => item !== option)
      : [...current, option];
  }
  facetValues.value = { ...facetValues.value, [facet.key]: next };
}

async function saveMore() {
  const c = criteria.value;
  if (!c) return;
  const regions = regionPreset.value ? [regionPreset.value] : (c.remote_eligibility?.regions ?? []);
  let locations: CriteriaV1["locations"] = [];
  if (place.value.trim()) {
    const base = { place: place.value.trim(), radius_km: radiusKm.value || null };
    try {
      const { data } = await client.get({
        url: "/api/v1/tracks/geo/lookup",
        query: { place: base.place },
        throwOnError: true,
      });
      const hit = data as { lat: number; lon: number; country: string | null };
      locations = [{ ...base, lat: hit.lat, lon: hit.lon, country: hit.country }];
    } catch {
      locations = [base];
    }
  }
  await saveCriteria({
    ...c,
    work_modes: workModes.value as CriteriaV1["work_modes"],
    visa_sponsorship: visa.value ? true : null,
    locations,
    remote_eligibility: {
      anywhere: c.remote_eligibility?.anywhere ?? false,
      regions,
      countries: c.remote_eligibility?.countries ?? [],
      timezone_overlap_hours:
        c.remote_eligibility?.timezone_overlap_hours != null ||
        Boolean(regionPreset.value) ||
        showAll.value
          ? tzOverlap.value
          : null,
      base_tz: c.remote_eligibility?.base_tz ?? null,
    },
    salary:
      salaryMin.value != null
        ? {
            min: salaryMin.value,
            max: null,
            currency: salaryCurrency.value,
            period: salaryPeriod.value,
            includes: salaryIncludes.value as NonNullable<CriteriaV1["salary"]>["includes"],
            hide_unspecified: c.salary?.hide_unspecified ?? false,
          }
        : null,
    shifts: shifts.value as CriteriaV1["shifts"],
    employment_types: employmentTypes.value as CriteriaV1["employment_types"],
    relocation: relocation.value ? true : null,
    posting_max_age_days: postingAge.value,
    languages: splitCsv(languagesDraft.value).map((item) => item.toLowerCase()),
    education: educationDraft.value.trim() || null,
    clearance: clearanceDraft.value.trim() || null,
    min_match_score: minScoreDraft.value,
    facets: Object.fromEntries(
      Object.entries(facetValues.value).filter(([, values]) => values.length > 0),
    ),
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
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-8 md:px-6">
    <div v-if="loading" class="flex flex-col gap-3">
      <FnSkeleton class="h-10 w-64" />
      <FnSkeleton class="h-40 w-full" />
    </div>
    <p v-else-if="loadError" class="text-sm text-ink-600">{{ apiError(loadError) }}</p>
    <template v-else-if="track">
      <div
        class="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-rule bg-paper-1 p-6 shadow-[var(--shadow-card)]"
      >
        <div class="min-w-0 flex-1">
          <FnFolderTab :hue="hue(track.color_hue)" active>{{ track.name }}</FnFolderTab>
        </div>
        <div class="flex w-full flex-wrap items-center gap-2 lg:w-auto">
          <FnButton tone="primary" :disabled="running" @click="runNow">{{
            running ? t("tracks.running") : t("tracks.runNow")
          }}</FnButton>
          <NuxtLink
            :to="`/jobs?track=${trackId}`"
            class="inline-flex min-h-11 items-center rounded-md border border-rule bg-paper-1 px-4 text-sm font-semibold text-brand-700 shadow-[var(--shadow-card)] transition-colors hover:border-brand-200 hover:bg-brand-50"
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
          <span class="size-2 animate-pulse rounded-full bg-ink-600" aria-hidden="true" />
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
        <NuxtLink :to="`/tracks/${trackId}/runs`" class="text-brand-700 underline">{{
          t("tracks.runHistory")
        }}</NuxtLink>
      </div>
      <section
        class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-5 shadow-[var(--shadow-card)]"
        :aria-label="t('tracks.matchedJobs')"
      >
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
        <div
          v-if="thinCoverage"
          class="flex flex-col gap-2 rounded-lg border border-brand-200 bg-brand-50 p-3 text-sm"
        >
          <p class="font-medium text-ink-900">
            {{
              t("tracks.coverageTitle", {
                field: exp.packLabel(industry),
                country: coveragePlace,
              })
            }}
          </p>
          <p class="text-ink-600">{{ t("tracks.coverageBody") }}</p>
          <NuxtLink
            to="/settings/alerts"
            class="font-semibold text-brand-700 underline underline-offset-2"
            >{{ t("tracks.addAlert") }}</NuxtLink
          >
        </div>
        <ul v-else class="divide-y divide-rule border-y border-rule">
          <li
            v-for="j in matchedJobs"
            :key="j.id"
            class="flex flex-wrap items-center gap-2 py-3 text-sm"
          >
            <span class="font-mono text-xs tabular-nums text-brand-700">{{
              j.score != null ? Math.round(j.score) : "-"
            }}</span>
            <div class="min-w-0 flex-1">
              <p class="font-medium text-ink-900">{{ j.title }}</p>
              <p class="text-ink-600">
                {{ j.company_name }}
                <span
                  v-for="r in (j.reasons || []).slice(0, 2)"
                  :key="String(r)"
                  class="ml-1 text-ink-400"
                  >· {{ reasonText(r) }}</span
                >
              </p>
            </div>
            <div class="flex items-center gap-1">
              <FnButton size="sm" tone="quiet" @click="triageMatch(j.id, 'shortlist')"
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

      <nav
        class="flex flex-wrap gap-1 rounded-lg bg-paper-2 p-1"
        :aria-label="t('tracks.sections')"
      >
        <span
          class="rounded-md bg-paper-1 px-4 py-2 text-sm font-semibold text-brand-700 shadow-[var(--shadow-card)]"
          >{{ t("tracks.criteria") }}</span
        >
        <NuxtLink
          :to="`/tracks/${trackId}/runs`"
          class="rounded-md px-4 py-2 text-sm font-semibold text-ink-600 hover:text-ink-900"
          >{{ t("tracks.runHistory") }}</NuxtLink
        >
        <NuxtLink
          :to="`/tracks/${trackId}/settings`"
          class="rounded-md px-4 py-2 text-sm font-semibold text-ink-600 hover:text-ink-900"
          >{{ t("tracks.settings") }}</NuxtLink
        >
      </nav>

      <section
        class="flex flex-col gap-4 rounded-xl border border-rule bg-paper-1 p-5 shadow-[var(--shadow-card)]"
      >
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
          <FnButton v-else size="sm" tone="quiet" @click="toggleAgencies">{{
            t("tracks.noAgencies")
          }}</FnButton>
        </div>
        <p class="text-sm text-ink-600">{{ t("tracks.criteriaHint") }}</p>
      </section>

      <section
        v-if="manifest"
        class="flex flex-col gap-5 rounded-xl border border-rule bg-paper-1 p-5 shadow-[var(--shadow-card)]"
      >
        <div class="grid gap-4 lg:grid-cols-2">
          <fieldset v-if="showField('work_modes')" class="flex flex-col gap-2">
            <legend class="text-sm text-ink-600">{{ t("tracks.workModes") }}</legend>
            <div class="flex flex-wrap gap-3">
              <label
                v-for="m in ['remote', 'hybrid', 'on_site']"
                :key="m"
                class="flex min-h-11 items-center gap-2 text-sm"
              >
                <input type="checkbox" :checked="workModes.includes(m)" @change="toggleMode(m)" />
                {{ t(`tracks.mode_${m}`) }}
              </label>
            </div>
          </fieldset>

          <template v-if="showField('locations')">
            <label class="flex flex-col gap-1 text-sm">
              <span class="text-ink-600">{{ labelFor("locations", "tracks.location") }}</span>
              <input
                v-model="place"
                type="text"
                class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
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
                class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              />
            </label>
          </template>

          <template v-if="showField('remote_eligibility')">
            <label class="flex flex-col gap-1 text-sm">
              <span class="text-ink-600">{{ t("tracks.region") }}</span>
              <select
                v-model="regionPreset"
                class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              >
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
              <input
                v-model.number="tzOverlap"
                type="range"
                min="0"
                max="12"
                class="min-h-11 w-full accent-brand-600"
              />
              <span class="text-xs tabular-nums text-ink-600">{{ tzOverlap }}h</span>
            </label>
          </template>

          <label
            v-if="showField('visa_sponsorship')"
            class="flex min-h-11 items-center gap-2 text-sm"
          >
            <input
              v-model="visa"
              type="checkbox"
              class="size-5 rounded border-rule accent-brand-600"
            />
            {{ t("tracks.visa") }}
          </label>
          <label v-if="showField('relocation')" class="flex min-h-11 items-center gap-2 text-sm">
            <input
              v-model="relocation"
              type="checkbox"
              class="size-5 rounded border-rule accent-brand-600"
            />
            {{ t("tracks.relocation") }}
          </label>
        </div>

        <div
          v-if="showField('salary') || showField('salary_includes')"
          class="grid gap-4 border-t border-rule pt-4 lg:grid-cols-2"
        >
          <template v-if="showField('salary')">
            <label class="flex flex-col gap-1 text-sm">
              <span class="text-ink-600">{{ t("tracks.salaryMin") }}</span>
              <input
                v-model.number="salaryMin"
                type="number"
                min="0"
                class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              />
            </label>
            <div class="flex gap-2">
              <label class="flex flex-1 flex-col gap-1 text-sm">
                <span class="text-ink-600">{{ t("tracks.currency") }}</span>
                <input
                  v-model="salaryCurrency"
                  type="text"
                  maxlength="3"
                  class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm uppercase text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
                />
              </label>
              <label class="flex flex-1 flex-col gap-1 text-sm">
                <span class="text-ink-600">{{ t("tracks.period") }}</span>
                <select
                  v-model="salaryPeriod"
                  class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
                >
                  <option value="hour">hour</option>
                  <option value="day">day</option>
                  <option value="month">month</option>
                  <option value="year">year</option>
                </select>
              </label>
            </div>
          </template>
          <fieldset v-if="showField('salary_includes')" class="flex flex-col gap-2">
            <legend class="text-sm text-ink-600">
              {{ labelFor("salary_includes", "tracks.salaryIncludes") }}
            </legend>
            <div class="flex flex-wrap gap-3">
              <label
                v-for="item in ['accommodation', 'meals', 'tips', 'service_charge', 'transport']"
                :key="item"
                class="flex min-h-11 items-center gap-2 text-sm"
              >
                <input
                  type="checkbox"
                  :checked="salaryIncludes.includes(item)"
                  @change="toggleInclude(item)"
                />
                {{ t(`tracks.include_${item}`) }}
              </label>
            </div>
          </fieldset>
        </div>

        <div
          v-if="
            showField('shifts') ||
            showField('employment_types') ||
            showField('posting_max_age_days')
          "
          class="grid gap-4 border-t border-rule pt-4 lg:grid-cols-2"
        >
          <fieldset v-if="showField('shifts')" class="flex flex-col gap-2">
            <legend class="text-sm text-ink-600">{{ t("tracks.shifts") }}</legend>
            <div class="flex flex-wrap gap-3">
              <label
                v-for="item in [
                  'morning',
                  'afternoon',
                  'evening',
                  'night',
                  'weekend',
                  'split',
                  'rotating',
                ]"
                :key="item"
                class="flex min-h-11 items-center gap-2 text-sm"
              >
                <input
                  type="checkbox"
                  :checked="shifts.includes(item)"
                  @change="toggleShift(item)"
                />
                {{ t(`tracks.shift_${item}`) }}
              </label>
            </div>
          </fieldset>
          <fieldset v-if="showField('employment_types')" class="flex flex-col gap-2">
            <legend class="text-sm text-ink-600">{{ t("tracks.employmentTypes") }}</legend>
            <div class="flex flex-wrap gap-3">
              <label
                v-for="item in [
                  'full_time',
                  'part_time',
                  'contract',
                  'freelance',
                  'internship',
                  'temporary',
                  'casual',
                  'seasonal',
                ]"
                :key="item"
                class="flex min-h-11 items-center gap-2 text-sm"
              >
                <input
                  type="checkbox"
                  :checked="employmentTypes.includes(item)"
                  @change="toggleEmployment(item)"
                />
                {{ t(`tracks.type_${item}`) }}
              </label>
            </div>
          </fieldset>
          <label v-if="showField('posting_max_age_days')" class="flex flex-col gap-1 text-sm">
            <span class="text-ink-600">{{ t("tracks.postingAge") }}</span>
            <input
              v-model.number="postingAge"
              type="number"
              min="1"
              max="365"
              class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
            />
          </label>
        </div>

        <div
          v-if="showField('facets') && facets.length"
          class="grid gap-4 border-t border-rule pt-4 lg:grid-cols-2"
        >
          <fieldset v-for="facet in facets" :key="facet.key" class="flex flex-col gap-2">
            <legend class="text-sm text-ink-600">{{ exp.facetLabel(facet) }}</legend>
            <div class="flex flex-wrap gap-2">
              <label
                v-for="option in facet.options"
                :key="option.key"
                class="flex min-h-11 items-center gap-2 rounded-full border border-rule px-3 text-sm"
              >
                <input
                  type="checkbox"
                  :checked="(facetValues[facet.key] ?? []).includes(option.key)"
                  @change="toggleFacet(facet, option.key)"
                />
                {{ exp.optionLabel(option) }}
              </label>
            </div>
          </fieldset>
        </div>

        <div
          v-if="showField('companies')"
          class="grid gap-4 border-t border-rule pt-4 lg:grid-cols-2"
        >
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-ink-600">{{ t("tracks.companiesInclude") }}</span>
            <input
              v-model="companiesInclude"
              type="text"
              class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              maxlength="2000"
            />
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-ink-600">{{ t("tracks.companiesExclude") }}</span>
            <input
              v-model="companiesExclude"
              type="text"
              class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              maxlength="2000"
            />
          </label>
        </div>

        <FnButton tone="primary" class="self-start" :disabled="saving" @click="saveMore">{{
          t("common.save")
        }}</FnButton>
      </section>

      <section class="flex flex-col gap-3 border-t border-rule pt-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <FnButton
            size="sm"
            tone="quiet"
            :aria-expanded="moreOpen"
            @click="moreOpen = !moreOpen"
            >{{ moreOpen ? t("tracks.hideFilters") : t("tracks.moreFilters") }}</FnButton
          >
          <FnButton size="sm" tone="ghost" :aria-pressed="showAll" @click="toggleShowAll">{{
            showAll ? t("tracks.hideAllFilters") : t("tracks.showAllFilters")
          }}</FnButton>
        </div>
        <p v-if="hiddenWithValues.length" class="text-xs text-ink-600">
          <span class="font-semibold">{{ t("tracks.setEarlier") }}:</span>
          {{ hiddenWithValues.join(", ") }}. {{ t("tracks.setEarlierHint") }}
        </p>
        <div v-if="moreOpen" class="grid gap-4 lg:grid-cols-2">
          <template
            v-if="(inMore('remote_eligibility') || showAll) && !showField('remote_eligibility')"
          >
            <label class="flex flex-col gap-1 text-sm">
              <span class="text-ink-600">{{ t("tracks.region") }}</span>
              <select
                v-model="regionPreset"
                class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              >
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
              <input
                v-model.number="tzOverlap"
                type="range"
                min="0"
                max="12"
                class="min-h-11 w-full accent-brand-600"
              />
              <span class="text-xs tabular-nums text-ink-600">{{ tzOverlap }}h</span>
            </label>
          </template>
          <label
            v-if="(inMore('keywords') || showAll) && !showField('keywords')"
            class="flex flex-col gap-1 text-sm md:col-span-2"
          >
            <span class="text-ink-600">{{ t("tracks.keywordsInclude") }}</span>
            <input
              v-model="includeExpr"
              type="text"
              class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm tabular-nums text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              maxlength="2000"
            />
          </label>
          <label
            v-if="(inMore('keywords') || showAll) && !showField('keywords')"
            class="flex flex-col gap-1 text-sm md:col-span-2"
          >
            <span class="text-ink-600">{{ t("tracks.keywordsExclude") }}</span>
            <input
              v-model="excludeExpr"
              type="text"
              class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm tabular-nums text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              maxlength="2000"
            />
          </label>
          <label
            v-if="(inMore('companies') || showAll) && !showField('companies')"
            class="flex flex-col gap-1 text-sm"
          >
            <span class="text-ink-600">{{ t("tracks.companiesInclude") }}</span>
            <input
              v-model="companiesInclude"
              type="text"
              class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              maxlength="2000"
            />
          </label>
          <label
            v-if="(inMore('companies') || showAll) && !showField('companies')"
            class="flex flex-col gap-1 text-sm"
          >
            <span class="text-ink-600">{{ t("tracks.companiesExclude") }}</span>
            <input
              v-model="companiesExclude"
              type="text"
              class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              maxlength="2000"
            />
          </label>
          <label
            v-if="(inMore('languages') || showAll) && !showField('languages')"
            class="flex flex-col gap-1 text-sm"
          >
            <span class="text-ink-600">{{ t("tracks.languages") }}</span>
            <input
              v-model="languagesDraft"
              type="text"
              class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              maxlength="200"
            />
          </label>
          <label
            v-if="(inMore('education') || showAll) && !showField('education')"
            class="flex flex-col gap-1 text-sm"
          >
            <span class="text-ink-600">{{ t("tracks.education") }}</span>
            <input
              v-model="educationDraft"
              type="text"
              class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              maxlength="200"
            />
          </label>
          <label
            v-if="(inMore('clearance') || showAll) && !showField('clearance')"
            class="flex flex-col gap-1 text-sm"
          >
            <span class="text-ink-600">{{ t("tracks.clearance") }}</span>
            <input
              v-model="clearanceDraft"
              type="text"
              class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
              maxlength="120"
            />
          </label>
          <label
            v-if="(inMore('min_match_score') || showAll) && !showField('min_match_score')"
            class="flex flex-col gap-1 text-sm"
          >
            <span class="text-ink-600">{{ t("tracks.minScore") }}</span>
            <input
              v-model.number="minScoreDraft"
              type="number"
              min="0"
              max="100"
              class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
            />
          </label>
          <FnButton tone="primary" class="self-start" :disabled="saving" @click="saveMore">{{
            t("common.save")
          }}</FnButton>
        </div>
      </section>

      <details
        class="rounded-xl border border-rule bg-paper-1 p-4 text-sm shadow-[var(--shadow-card)]"
      >
        <summary
          class="flex min-h-11 cursor-pointer list-none items-center font-semibold text-ink-900"
        >
          {{ t("tracks.whereWeLook") }}
        </summary>
        <div v-if="whereLook.data.value" class="mt-3 flex flex-col gap-4">
          <div>
            <p class="text-xs font-semibold tracking-wide text-ink-400 uppercase">
              {{ t("tracks.searchTerms") }}
            </p>
            <ul
              v-if="whereLook.data.value.queries.length"
              class="mt-1 flex flex-col gap-1 text-ink-600"
            >
              <li v-for="(query, i) in whereLook.data.value.queries" :key="i">
                {{ query.keywords }}
                <template v-if="query.location">in {{ query.location }}</template>
              </li>
            </ul>
            <p v-else class="mt-1 text-ink-600">{{ t("tracks.noSearchTerms") }}</p>
          </div>
          <div>
            <p class="text-xs font-semibold tracking-wide text-ink-400 uppercase">
              {{ t("tracks.sources") }}
            </p>
            <ul class="mt-1 flex flex-col gap-1">
              <li
                v-for="adapter in whereLook.data.value.adapters"
                :key="adapter.key"
                class="flex flex-wrap items-center gap-2 text-ink-600"
              >
                <span class="text-ink-900">{{ adapter.name }}</span>
                <span class="text-xs">{{
                  adapter.configured ? t("tracks.ready") : t("tracks.setupNeeded")
                }}</span>
              </li>
            </ul>
          </div>
        </div>
      </details>
    </template>
  </div>
</template>
