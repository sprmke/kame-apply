<script setup lang="ts">
import {
  listJobsApiV1JobsGet,
  markAppliedApiV1ApplicationsMarkAppliedPost,
  relaxationsApiV1TracksTrackIdRelaxationsGet,
  riskDecisionApiV1JobsJobIdRiskDecisionPost,
  trackJobDetailApiV1TrackJobsTrackJobIdGet,
  triageJobApiV1TrackJobsTrackJobIdTriagePost,
  type BoardJobRead,
  type JobDetailRead,
} from "@kame/api-client";
import {
  FnButton,
  FnChip,
  FnEmptyState,
  FnRiskSeal,
  FnSelect,
  FnSkeleton,
  FnSkeletonGroup,
  useToast,
} from "@kame/ui";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const { t, te } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const route = useRoute();
const router = useRouter();

const trackFilter = computed(() => (route.query.track as string) || undefined);
const includeIneligible = ref(false);
const sort = ref<"score" | "newest" | "salary">("score");
const sortOptions = computed(() => [
  { value: "score", label: t("jobs.sortMatch") },
  { value: "newest", label: t("jobs.sortNewest") },
  { value: "salary", label: t("jobs.sortSalary") },
]);
const sortValue = computed({
  get: () => sort.value,
  set: (value: string) => {
    sort.value = value as typeof sort.value;
  },
});
const statusFilter = ref("");
const salaryOnly = ref(false);
const remoteOnly = ref(false);
const moreOpen = ref(false);
const statusChips = computed(() => [
  { value: "", label: t("jobs.filtersAll") },
  { value: "new", label: t("jobs.filtersNew") },
  { value: "shortlisted", label: t("jobs.filtersShortlisted") },
  { value: "applied", label: t("jobs.filtersApplied") },
]);
const selectedId = ref<string | null>(null);
const helpOpen = ref(false);
const skipOpen = ref(false);
const skipReason = ref("too junior");
const skipOptions = computed(() => [
  { value: "too junior", label: t("jobs.skipTooJunior") },
  { value: "too senior", label: t("jobs.skipTooSenior") },
  { value: "salary", label: t("jobs.skipSalary") },
  { value: "location", label: t("jobs.skipLocation") },
  { value: "missing skills", label: t("jobs.skipSkills") },
  { value: "wrong title", label: t("jobs.skipWrongTitle") },
  { value: "other", label: t("jobs.skipOther") },
]);
const riskConfirmOpen = ref(false);
const showAllFit = ref(false);
const mobileDetail = ref(false);

const HIGHLIGHT_KEY = "kame.jobs.highlight";
function highlightPreference(): boolean {
  try {
    return localStorage.getItem(HIGHLIGHT_KEY) !== "off";
  } catch {
    return true;
  }
}
const highlightMatches = ref(highlightPreference());
watch(highlightMatches, (value) => {
  try {
    localStorage.setItem(HIGHLIGHT_KEY, value ? "on" : "off");
  } catch {
    // A blocked storage write should not break reading.
  }
});

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

function reasonText(r: unknown): string {
  const text =
    typeof r === "string"
      ? r
      : r && typeof r === "object"
        ? String(
            (r as { evidence?: string; signal?: string }).evidence ||
              (r as { signal?: string }).signal ||
              "",
          )
        : "";
  const clean = text.trim();
  return STOP_REASONS.has(clean.toLowerCase()) ? "" : (REASON_COPY[clean] ?? clean);
}

const board = useQuery({
  queryKey: computed(() => [
    "jobs-board",
    ws.currentId,
    trackFilter.value,
    includeIneligible.value,
    sort.value,
    statusFilter.value,
  ]),
  queryFn: async () => {
    const { data } = await listJobsApiV1JobsGet({
      query: {
        track_id: trackFilter.value,
        status: statusFilter.value || undefined,
        include_not_eligible: includeIneligible.value,
        sort: sort.value,
        limit: 100,
      },
      throwOnError: true,
    });
    return (data ?? []) as BoardJobRead[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
  placeholderData: keepPreviousData,
});

const rows = computed(() =>
  (board.data.value ?? []).filter((row) => {
    if (salaryOnly.value && !salaryLabel(row.salary)) return false;
    if (remoteOnly.value && row.work_mode !== "remote") return false;
    return true;
  }),
);
const initialJob = computed(() => (route.query.job as string) || null);
const loading = computed(
  () => !ws.loaded || board.isPending.value || (board.isFetching.value && !board.data.value),
);

const detailQ = useQuery({
  queryKey: computed(() => ["track-job", ws.currentId, selectedId.value]),
  queryFn: async () => {
    const { data } = await trackJobDetailApiV1TrackJobsTrackJobIdGet({
      path: { track_job_id: selectedId.value! },
      throwOnError: true,
    });
    return data as JobDetailRead;
  },
  enabled: computed(() => Boolean(ws.currentId && selectedId.value)),
});

const selected = computed(() => detailQ.data.value ?? null);
const selectedIndex = computed(() => rows.value.findIndex((r) => r.id === selectedId.value));

const relax = useQuery({
  queryKey: computed(() => ["relax", ws.currentId, trackFilter.value]),
  queryFn: async () => {
    if (!trackFilter.value) return [];
    const { data } = await relaxationsApiV1TracksTrackIdRelaxationsGet({
      path: { track_id: trackFilter.value },
      throwOnError: true,
    });
    return data ?? [];
  },
  enabled: computed(() => Boolean(ws.currentId && trackFilter.value && rows.value.length === 0)),
});

watch(
  [rows, initialJob],
  ([list, wanted]) => {
    if (!list.length) {
      selectedId.value = null;
      return;
    }
    if (wanted && list.some((r) => r.id === wanted)) {
      selectedId.value = wanted;
      mobileDetail.value = true;
      return;
    }
    if (!selectedId.value || !list.some((r) => r.id === selectedId.value)) {
      selectedId.value = list[0]!.id;
    }
  },
  { immediate: true },
);

async function triage(
  action: "shortlist" | "skip" | "hide" | "applied" | "restore",
  reason?: string,
) {
  if (!selectedId.value) return;
  try {
    await triageJobApiV1TrackJobsTrackJobIdTriagePost({
      path: { track_job_id: selectedId.value },
      body: { action, skip_reason: reason },
      throwOnError: true,
    });
    skipOpen.value = false;
    await qc.invalidateQueries({ queryKey: ["jobs-board", ws.currentId] });
    const idx = selectedIndex.value;
    const next = rows.value[idx + 1] ?? rows.value[idx - 1];
    selectedId.value = next?.id ?? null;
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function markApplied() {
  if (!selectedId.value) return;
  try {
    const { data } = await markAppliedApiV1ApplicationsMarkAppliedPost({
      body: { track_job_id: selectedId.value, method: "manual" },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["jobs-board", ws.currentId] });
    await qc.invalidateQueries({ queryKey: ["applications", ws.currentId] });
    await qc.invalidateQueries({ queryKey: ["home", ws.currentId] });
    if (data?.duplicate_warning) {
      toast.push({ title: t("applications.duplicate") });
    }
    if (data?.id) await navigateTo(`/applications/${data.id}`);
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function continueDespiteRisk() {
  if (!selected.value?.job_id) return;
  try {
    await riskDecisionApiV1JobsJobIdRiskDecisionPost({
      path: { job_id: selected.value.job_id },
      body: { decision: "continue", confirm_risk: true },
      throwOnError: true,
    });
    riskConfirmOpen.value = false;
    await qc.invalidateQueries({ queryKey: ["track-job", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

function selectJob(id: string) {
  selectedId.value = id;
  mobileDetail.value = true;
}

function move(delta: number) {
  if (!rows.value.length) return;
  const idx = Math.max(0, selectedIndex.value);
  const next = rows.value[Math.min(rows.value.length - 1, Math.max(0, idx + delta))];
  if (next) selectedId.value = next.id;
}

function openOriginal() {
  const url = selected.value?.apply_url;
  if (url) window.open(url, "_blank", "noopener");
}

function onKey(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement | null)?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
  if (e.key === "j" || e.key === "ArrowDown") {
    e.preventDefault();
    move(1);
  } else if (e.key === "k" || e.key === "ArrowUp") {
    e.preventDefault();
    move(-1);
  } else if (e.key === "s") {
    e.preventDefault();
    void triage("shortlist");
  } else if (e.key === "x") {
    e.preventDefault();
    skipOpen.value = true;
  } else if (e.key === "t") {
    e.preventDefault();
    if (selectedId.value) void router.push(`/tailor/${selectedId.value}`);
  } else if (e.key === "o") {
    e.preventDefault();
    openOriginal();
  } else if (e.key === "?") {
    e.preventDefault();
    helpOpen.value = !helpOpen.value;
  }
}

onMounted(() => window.addEventListener("keydown", onKey));
onUnmounted(() => window.removeEventListener("keydown", onKey));

function workModeLabel(mode: string | null | undefined): string {
  if (!mode) return "";
  return t(`tracks.mode_${mode}`);
}

function salaryLabel(s: Record<string, unknown> | undefined): string {
  if (!s || s.min == null) return "";
  const format = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
  const min = Number(s.min);
  const max = s.max != null ? Number(s.max) : null;
  const range = max != null ? `${format.format(min)}–${format.format(max)}` : format.format(min);
  return [s.currency, range, s.period ? `/ ${s.period}` : ""].filter(Boolean).join(" ");
}

function payLabel(s: Record<string, unknown> | undefined): string {
  if (!s || !s.currency || !s.period || s.min == null) return "";
  return salaryLabel(s);
}

function visibleReasons(reasons: unknown[] | undefined): unknown[] {
  return (reasons || []).filter((r) => {
    const text = reasonText(r).toLowerCase();
    if (!text) return false;
    const parts = text
      .split(/[,·|]/)
      .map((part) => part.trim())
      .filter(Boolean);
    return parts.length > 0 && !parts.every((part) => STOP_REASONS.has(part));
  });
}

const visibleQualifications = computed(() => {
  const rows = selected.value?.qualifications ?? [];
  return showAllFit.value ? rows : rows.slice(0, 3);
});
const visibleRiskReasons = computed(() =>
  visibleReasons(selected.value?.risk_reasons ?? []).slice(0, 5),
);
const fitMet = computed(
  () => (selected.value?.qualifications ?? []).filter((q) => q.verdict === "met").length,
);
const allUnproven = computed(() => {
  const rows = selected.value?.qualifications ?? [];
  return rows.length > 0 && rows.every((q) => String(q.verdict || "").includes("not"));
});

function kindLabel(kind?: string | null): string {
  if (kind === "must") return t("jobs.required");
  if (kind === "nice") return t("jobs.preferred");
  if (kind === "credential") return t("jobs.certificate");
  if (kind === "shift") return t("jobs.shift");
  if (kind === "benefit") return t("jobs.payIncludes");
  return kind || "";
}

function qualText(row: { kind?: string; text?: string }): string {
  const raw = String(row.text || "");
  if (row.kind === "credential") {
    const key = `credential.${raw}`;
    return te(key) ? t(key) : raw;
  }
  if (row.kind === "shift" || row.kind === "benefit") {
    const prefix = row.kind === "shift" ? "tracks.shift_" : "tracks.include_";
    return raw
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => (te(prefix + part) ? t(prefix + part) : part))
      .join(", ");
  }
  return raw;
}

function verdictLabel(verdict?: string | null): string {
  if (!verdict) return "";
  if (verdict.includes("not")) return t("jobs.noEvidence");
  if (verdict === "met") return "Met";
  if (verdict === "partial") return "Partial";
  return verdict;
}

function chipTone(v?: string | null): "neutral" | "accent" | "pencil" {
  if (v === "met") return "accent";
  if (v === "partial") return "pencil";
  return "neutral";
}
</script>

<template>
  <div
    class="mx-auto flex w-full max-w-[1600px] flex-col gap-4"
    :class="
      mobileDetail
        ? 'min-h-[calc(100dvh-8rem)]'
        : 'min-h-[calc(100dvh-8rem)] lg:h-[calc(100dvh-4rem)]'
    "
  >
    <header class="flex flex-col gap-3" :class="mobileDetail ? 'max-lg:hidden' : ''">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div class="min-w-0">
          <h1 class="text-2xl font-bold tracking-[-0.03em] text-ink-900 sm:text-3xl">
            {{ t("nav.jobs") }}
          </h1>
          <p class="mt-1 max-w-2xl text-sm leading-6 text-ink-600">{{ t("jobs.intro") }}</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm text-ink-600">{{ t("jobs.sort") }}</span>
          <div class="w-36">
            <FnSelect v-model="sortValue" :options="sortOptions" :aria-label="t('jobs.sort')" />
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <div class="flex gap-1 overflow-x-auto rounded-lg bg-paper-2 p-1" role="tablist">
          <button
            v-for="chip in statusChips"
            :key="chip.value"
            type="button"
            role="tab"
            class="min-h-11 shrink-0 rounded-md px-3 text-sm font-semibold whitespace-nowrap"
            :class="
              statusFilter === chip.value
                ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
                : 'text-ink-600 hover:text-ink-900'
            "
            :aria-selected="statusFilter === chip.value"
            @click="statusFilter = chip.value"
          >
            {{ chip.label }}
          </button>
        </div>
        <button
          type="button"
          class="min-h-11 rounded-md px-3 text-sm font-semibold text-ink-600 hover:bg-paper-2 hover:text-ink-900"
          :aria-expanded="moreOpen"
          @click="moreOpen = !moreOpen"
        >
          {{ t("jobs.moreFilters") }}
        </button>
      </div>

      <div
        v-if="moreOpen"
        class="flex flex-wrap items-center gap-3 rounded-xl border border-rule bg-paper-1 p-3"
      >
        <label class="flex min-h-11 items-center gap-2 text-sm text-ink-900">
          <input
            v-model="salaryOnly"
            type="checkbox"
            class="size-5 rounded border-rule accent-brand-600"
          />
          {{ t("jobs.filtersSalary") }}
        </label>
        <label class="flex min-h-11 items-center gap-2 text-sm text-ink-900">
          <input
            v-model="remoteOnly"
            type="checkbox"
            class="size-5 rounded border-rule accent-brand-600"
          />
          {{ t("jobs.filtersRemote") }}
        </label>
        <label class="flex min-h-11 items-center gap-2 text-sm text-ink-900">
          <input
            v-model="includeIneligible"
            type="checkbox"
            class="size-5 rounded border-rule accent-brand-600"
          />
          {{ t("jobs.includeIneligible") }}
        </label>
      </div>

      <p
        v-if="helpOpen"
        class="rounded-lg border border-rule bg-paper-2 px-3 py-2 text-sm text-ink-600"
      >
        {{ t("jobs.shortcutsLine") }}
      </p>
    </header>

    <FnSkeletonGroup
      v-if="loading"
      :label="t('common.loading')"
      class="grid min-h-0 flex-1 gap-0 rounded-xl border border-rule bg-paper-1 p-0 shadow-[var(--shadow-card)] lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)] xl:grid-cols-[minmax(0,22rem)_minmax(0,1fr)_minmax(0,19rem)]"
    >
      <div class="flex min-h-0 min-w-0 flex-col lg:border-r lg:border-rule">
        <div
          class="flex items-center gap-3 border-b border-rule px-4 py-2 text-[0.6875rem] font-semibold tracking-[0.12em] uppercase max-sm:hidden"
          aria-hidden="true"
        >
          <span class="w-9 shrink-0"><FnSkeleton class="ml-auto h-3 w-7" /></span>
          <span class="flex-1"><FnSkeleton class="h-3 w-12" /></span>
        </div>
        <ul class="min-h-0 flex-1 pb-20 lg:overflow-hidden lg:pb-0">
          <li v-for="n in 7" :key="n" class="border-b border-rule last:border-b-0">
            <div class="flex items-start gap-3 px-3 py-3">
              <FnSkeleton class="mt-0.5 h-4 w-9 shrink-0" />
              <div class="flex min-h-14 min-w-0 flex-1 flex-col gap-2">
                <FnSkeleton class="h-4 w-4/5" />
                <FnSkeleton class="h-3 w-3/5" />
                <FnSkeleton class="h-3 w-2/5" />
              </div>
            </div>
          </li>
        </ul>
      </div>

      <section class="hidden min-h-0 px-4 py-4 sm:px-6 xl:block">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="flex min-w-0 flex-1 flex-col gap-2">
            <FnSkeleton class="h-8 w-4/5 sm:h-9" />
            <FnSkeleton class="h-4 w-2/3" />
          </div>
          <FnSkeleton class="h-7 w-24 shrink-0 rounded-full" />
        </div>
        <div class="mt-5 flex flex-wrap gap-2 border-y border-rule py-3">
          <FnSkeleton class="h-11 w-32 rounded-md" />
          <FnSkeleton class="h-11 w-24 rounded-md" />
          <FnSkeleton class="h-11 w-28 rounded-md" />
          <FnSkeleton class="h-11 w-24 rounded-md" />
        </div>
        <div class="mt-5 flex flex-col gap-2">
          <FnSkeleton class="h-4 w-32" />
          <FnSkeleton class="h-4 w-full" />
          <FnSkeleton class="h-4 w-11/12" />
          <FnSkeleton class="h-4 w-3/4" />
        </div>
        <div class="mt-6 flex flex-col gap-2">
          <FnSkeleton class="h-4 w-40" />
          <FnSkeleton class="h-4 w-full" />
          <FnSkeleton class="h-4 w-10/12" />
          <FnSkeleton class="h-4 w-9/12" />
          <FnSkeleton class="h-4 w-full" />
          <FnSkeleton class="h-4 w-7/12" />
        </div>
      </section>

      <section
        class="hidden min-h-0 flex-col gap-5 border-t border-rule bg-paper-0 px-4 py-5 xl:flex xl:overflow-y-auto xl:border-t-0 xl:border-l"
      >
        <section class="flex flex-col gap-3">
          <div class="flex flex-col gap-1">
            <FnSkeleton class="h-9 w-12" />
            <FnSkeleton class="h-3 w-20" />
          </div>
          <FnSkeleton class="h-4 w-28" />
          <div class="flex flex-col gap-2">
            <FnSkeleton class="h-4 w-full" />
            <FnSkeleton class="h-4 w-5/6" />
            <FnSkeleton class="h-4 w-2/3" />
          </div>
          <FnSkeleton class="h-24 w-full rounded-lg" />
        </section>
        <section class="flex flex-col gap-2 border-t border-rule pt-4">
          <div class="flex items-center justify-between gap-2">
            <FnSkeleton class="h-4 w-16" />
            <FnSkeleton class="h-3 w-16" />
          </div>
          <FnSkeleton class="h-3.5 w-full" />
          <div class="flex flex-col gap-2">
            <FnSkeleton class="h-16 w-full rounded-lg" />
            <FnSkeleton class="h-16 w-full rounded-lg" />
            <FnSkeleton class="h-16 w-full rounded-lg" />
          </div>
        </section>
      </section>
    </FnSkeletonGroup>

    <FnEmptyState
      v-else-if="!rows.length"
      :title="t('jobs.emptyTitle')"
      :body="t('jobs.emptyBody')"
    >
      <FnButton tone="primary" size="sm" @click="router.push('/tracks')">{{
        t("nav.tracks")
      }}</FnButton>
      <ul v-if="relax.data.value?.length" class="flex flex-wrap gap-2 text-sm text-ink-600">
        <li v-for="s in relax.data.value" :key="s.label" class="rounded-full bg-paper-2 px-3 py-1">
          {{ s.label }}: +{{ s.gained }}
        </li>
      </ul>
    </FnEmptyState>

    <div
      v-else
      class="grid min-h-0 flex-1 gap-0 rounded-xl border border-rule bg-paper-1 p-0 shadow-[var(--shadow-card)] lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)] xl:grid-cols-[minmax(0,22rem)_minmax(0,1fr)_minmax(0,19rem)]"
    >
      <div
        :class="mobileDetail ? 'hidden lg:flex' : 'flex'"
        class="min-h-0 min-w-0 flex-col lg:border-r lg:border-rule"
      >
        <div
          class="flex items-center gap-3 border-b border-rule px-4 py-2 text-[0.6875rem] font-semibold tracking-[0.12em] text-ink-400 uppercase max-sm:hidden"
        >
          <span class="w-9 shrink-0 text-right">{{ t("jobs.colMatch") }}</span>
          <span class="flex-1">{{ t("jobs.colJob") }}</span>
        </div>
        <ul
          :aria-label="t('jobs.list')"
          class="min-h-0 flex-1 pb-20 lg:overflow-y-auto lg:pb-0"
          role="listbox"
        >
          <li
            v-for="row in rows"
            :key="row.id"
            role="option"
            :aria-selected="row.id === selectedId"
            class="cursor-pointer border-b border-rule transition-colors last:border-b-0"
            :class="
              row.id === selectedId
                ? 'bg-brand-50 shadow-[inset_2px_0_0_0_var(--brand-500)]'
                : 'hover:bg-paper-2'
            "
            @click="selectJob(row.id)"
          >
            <div class="flex items-start gap-3 px-3 py-3">
              <span
                class="w-9 shrink-0 pt-0.5 text-right text-sm font-semibold tabular-nums"
                :class="row.id === selectedId ? 'text-brand-700' : 'text-ink-600'"
                >{{ row.score != null ? Math.round(row.score) : "-" }}</span
              >
              <div class="min-h-14 min-w-0 flex-1">
                <p
                  class="truncate text-sm font-semibold text-ink-900"
                  :title="row.title ?? undefined"
                >
                  {{ row.title }}
                </p>
                <p class="mt-0.5 flex items-center gap-x-1.5 text-xs">
                  <span class="min-w-0 truncate text-ink-600">{{ row.company_name }}</span>
                  <span v-if="row.work_mode" class="shrink-0 text-ink-400"
                    >· {{ workModeLabel(row.work_mode) }}</span
                  >
                  <span
                    v-if="row.risk_level === 'red'"
                    class="inline-flex shrink-0 items-center gap-1 font-semibold text-oxblood-600"
                    ><span aria-hidden="true">✕</span>{{ t("jobs.highRisk") }}</span
                  >
                  <span
                    v-else-if="row.risk_level === 'yellow'"
                    class="inline-flex shrink-0 items-center gap-1 font-semibold text-saffron-600"
                    ><span aria-hidden="true">!</span>{{ t("jobs.caution") }}</span
                  >
                  <span
                    v-if="row.eligibility === 'not_eligible'"
                    class="shrink-0 text-ink-400"
                    :title="t('jobs.notEligibleReason')"
                    >· {{ t("jobs.ineligible") }}</span
                  >
                </p>
                <p v-if="payLabel(row.salary)" class="mt-0.5 text-xs tabular-nums text-ink-600">
                  {{ payLabel(row.salary) }}
                </p>
              </div>
            </div>
          </li>
        </ul>
      </div>

      <section
        v-if="!selected && selectedId"
        :class="mobileDetail ? 'block' : 'hidden xl:block'"
        class="min-h-0 px-4 py-4 sm:px-6 lg:overflow-y-auto"
      >
        <button
          type="button"
          class="mb-3 flex min-h-11 items-center gap-2 rounded-md px-2 text-sm font-semibold text-ink-600 hover:bg-paper-2 lg:hidden"
          @click="mobileDetail = false"
        >
          <NavIcon name="ph:arrow-left" :size="16" /> {{ t("jobs.backToList") }}
        </button>
        <FnSkeletonGroup :label="t('common.loading')" class="flex flex-col gap-5">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="flex min-w-0 flex-1 flex-col gap-2">
              <FnSkeleton class="h-8 w-4/5 sm:h-9" />
              <FnSkeleton class="h-4 w-2/3" />
            </div>
            <FnSkeleton class="h-7 w-24 shrink-0 rounded-full" />
          </div>
          <div class="flex flex-wrap gap-2 border-y border-rule py-3">
            <FnSkeleton class="h-11 w-32 rounded-md" />
            <FnSkeleton class="h-11 w-24 rounded-md" />
            <FnSkeleton class="h-11 w-28 rounded-md" />
            <FnSkeleton class="h-11 w-24 rounded-md" />
          </div>
          <div class="flex flex-col gap-2">
            <FnSkeleton class="h-4 w-32" />
            <FnSkeleton class="h-4 w-full" />
            <FnSkeleton class="h-4 w-11/12" />
            <FnSkeleton class="h-4 w-3/4" />
          </div>
          <div class="flex flex-col gap-2">
            <FnSkeleton class="h-4 w-40" />
            <FnSkeleton class="h-4 w-full" />
            <FnSkeleton class="h-4 w-10/12" />
            <FnSkeleton class="h-4 w-9/12" />
            <FnSkeleton class="h-4 w-full" />
            <FnSkeleton class="h-4 w-7/12" />
          </div>
        </FnSkeletonGroup>
      </section>

      <section
        v-else-if="selected"
        :class="mobileDetail ? 'block' : 'hidden xl:block'"
        class="min-h-0 px-4 py-4 sm:px-6 lg:overflow-y-auto"
      >
        <button
          type="button"
          class="mb-3 flex min-h-11 items-center gap-2 rounded-md px-2 text-sm font-semibold text-ink-600 hover:bg-paper-2 lg:hidden"
          @click="mobileDetail = false"
        >
          <NavIcon name="ph:arrow-left" :size="16" /> {{ t("jobs.backToList") }}
        </button>

        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <h2 class="text-2xl font-bold tracking-[-0.03em] text-ink-900 sm:text-3xl">
              {{ selected.title }}
            </h2>
            <p class="mt-1 text-sm text-ink-600">
              {{ selected.company_name }}
              <span v-if="selected.work_mode"> · {{ workModeLabel(selected.work_mode) }}</span>
              <span v-if="salaryLabel(selected.salary)"> · {{ salaryLabel(selected.salary) }}</span>
            </p>
          </div>
          <FnRiskSeal
            v-if="selected.risk_level"
            class="shrink-0"
            :level="sealLevel(selected.risk_level)"
            :label="sealLabel(selected.risk_level)"
          />
        </div>

        <p
          v-if="selected.eligibility_quote"
          class="mt-3 border-l-2 border-brand-700 pl-3 text-sm leading-6 text-ink-600 italic"
        >
          {{ selected.eligibility_quote }}
        </p>
        <p v-if="selected.few_stated_requirements" class="mt-2 text-xs text-ink-400">
          {{ t("jobs.fewRequirements") }}
        </p>

        <div class="mt-5 flex flex-wrap gap-2 border-y border-rule py-3">
          <FnButton size="sm" tone="primary" @click="router.push(`/tailor/${selectedId}`)">
            {{ t("jobs.tailorResume") }}
          </FnButton>
          <FnButton size="sm" tone="quiet" @click="triage('shortlist')">
            {{ t("jobs.shortlist") }}
          </FnButton>
          <FnButton size="sm" tone="quiet" :disabled="!selected.apply_url" @click="openOriginal">
            {{ t("jobs.openOriginal") }}
          </FnButton>
          <FnButton size="sm" tone="ghost" @click="markApplied">{{
            t("applications.markApplied")
          }}</FnButton>
          <FnButton size="sm" tone="ghost" @click="skipOpen = true">{{ t("jobs.skip") }}</FnButton>
        </div>

        <section
          v-if="visibleReasons(selected.reasons).length"
          class="mt-4 flex flex-col gap-1 xl:hidden"
        >
          <h3 class="text-sm font-semibold tracking-wide text-ink-400 uppercase">
            {{ t("jobs.whyMatch") }}
          </h3>
          <ul class="flex flex-col gap-1">
            <li
              v-for="r in visibleReasons(selected.reasons).slice(0, 3)"
              :key="String(r)"
              class="flex items-start gap-2 text-sm leading-6 text-ink-600"
            >
              <span class="mt-2 size-1.5 shrink-0 rounded-full bg-fern-600" aria-hidden="true" />
              {{ reasonText(r) }}
            </li>
          </ul>
        </section>

        <section v-if="selected.qualifications?.length" class="mt-4 flex flex-col gap-1 xl:hidden">
          <h3 class="text-sm font-semibold tracking-wide text-ink-400 uppercase">
            {{ t("jobs.fit") }}
          </h3>
          <p class="text-sm leading-6 text-ink-600">
            {{ t("jobs.fitCompact", { met: fitMet, total: selected.qualifications.length }) }}
          </p>
          <NuxtLink
            v-if="allUnproven"
            to="/profile/onboarding"
            class="text-sm font-semibold text-brand-700 underline"
            >{{ t("jobs.addResume") }}</NuxtLink
          >
        </section>

        <div class="mt-5 border-t border-rule pt-5">
          <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h3 class="text-sm font-semibold tracking-wide text-ink-400 uppercase">
              {{ t("jobs.description") }}
            </h3>
            <label
              v-if="selected.match_terms?.length"
              class="flex min-h-11 cursor-pointer items-center gap-2 text-sm font-medium text-ink-600"
            >
              <input
                v-model="highlightMatches"
                type="checkbox"
                class="size-5 rounded border-rule accent-brand-600"
              />
              {{ t("jobs.highlightMatches") }}
            </label>
          </div>
          <JobDescription
            :text="selected.description_text"
            :terms="selected.match_terms ?? []"
            :highlight="highlightMatches"
          />
        </div>
      </section>
      <FnSkeleton v-else class="h-40" />

      <aside
        v-if="selected"
        :class="mobileDetail ? 'block' : 'hidden xl:block'"
        class="flex min-h-0 flex-col gap-5 border-t border-rule bg-paper-0 px-4 py-5 xl:overflow-y-auto xl:border-t-0 xl:border-l"
      >
        <section class="flex flex-col gap-3">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="text-3xl font-bold tabular-nums text-brand-700">
                {{ selected.score != null ? Math.round(selected.score) : "-" }}
              </div>
              <p class="text-xs text-ink-400">{{ t("jobs.matchScore") }}</p>
            </div>
          </div>
          <h3 class="text-sm font-semibold tracking-wide text-ink-400 uppercase">
            {{ t("jobs.whyMatch") }}
          </h3>
          <ul v-if="visibleReasons(selected.reasons).length" class="flex flex-col gap-1">
            <li
              v-for="r in visibleReasons(selected.reasons).slice(0, 5)"
              :key="String(r)"
              class="flex items-start gap-2 text-sm leading-6 text-ink-600"
            >
              <span class="mt-2 size-1.5 shrink-0 rounded-full bg-fern-600" aria-hidden="true" />
              {{ reasonText(r) }}
            </li>
          </ul>
          <ul
            v-if="
              visibleRiskReasons.length &&
              (selected.risk_level === 'yellow' || selected.risk_level === 'red')
            "
            class="space-y-1 border-l-2 border-oxblood-600 pl-3 text-sm leading-6 text-ink-600"
          >
            <li v-for="(r, i) in visibleRiskReasons" :key="i">{{ reasonText(r) }}</li>
          </ul>
          <ScoreBreakdown :components="selected.score_components" />
        </section>

        <section class="flex flex-col gap-2 border-t border-rule pt-4">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold tracking-wide text-ink-400 uppercase">
              {{ t("jobs.fit") }}
            </h3>
            <span v-if="selected.qualifications?.length" class="text-xs text-ink-400">
              {{ t("jobs.checks", { n: selected.qualifications.length }) }}
            </span>
          </div>
          <p class="text-sm leading-6 text-ink-600">{{ t("jobs.fitHint") }}</p>
          <p
            v-if="allUnproven"
            class="rounded-lg border border-brand-200 bg-brand-50 p-3 text-sm leading-6 text-ink-900"
          >
            {{ t("jobs.addResumeFacts") }}
            <NuxtLink
              to="/profile/onboarding"
              class="font-semibold whitespace-nowrap text-brand-700 underline"
              >{{ t("jobs.addResume") }}</NuxtLink
            >
          </p>
          <ul class="space-y-2">
            <li
              v-for="q in visibleQualifications"
              :key="String(q.id)"
              class="rounded-lg border border-rule bg-paper-1 p-3"
            >
              <div class="flex flex-wrap items-center gap-2">
                <FnChip :tone="chipTone(String(q.verdict || ''))">{{
                  verdictLabel(String(q.verdict || ""))
                }}</FnChip>
                <span class="text-xs font-semibold tracking-wide text-ink-400 uppercase">{{
                  kindLabel(String(q.kind || ""))
                }}</span>
              </div>
              <p class="mt-2 line-clamp-3 text-sm leading-6 text-ink-900" :title="qualText(q)">
                {{ qualText(q) }}
              </p>
              <p
                v-if="q.evidence_quote && q.evidence_quote !== q.text"
                class="mt-1 line-clamp-2 text-xs leading-5 text-ink-400"
              >
                {{ q.evidence_quote }}
              </p>
            </li>
          </ul>
          <FnButton
            v-if="(selected.qualifications?.length ?? 0) > 3"
            size="sm"
            tone="ghost"
            class="self-start"
            @click="showAllFit = !showAllFit"
            >{{ showAllFit ? t("jobs.showFewerChecks") : t("jobs.showAllChecks") }}</FnButton
          >
        </section>

        <section
          v-if="selected.risk_level === 'red' || selected.risk_level === 'yellow'"
          class="flex flex-col gap-2 border-t border-rule pt-4"
        >
          <p class="text-sm leading-6 text-ink-600">
            {{ selected.risk_level === "red" ? t("jobs.riskHighBody") : t("jobs.riskCautionBody") }}
          </p>
          <FnButton size="sm" tone="danger" class="self-start" @click="riskConfirmOpen = true">
            {{ t("jobs.continueAnyway") }}
          </FnButton>
        </section>

        <div
          v-if="riskConfirmOpen && selected"
          class="space-y-2 rounded-lg border border-oxblood-600 bg-paper-1 p-3 text-sm"
        >
          <p class="leading-6">{{ t("jobs.riskConfirm") }}</p>
          <div class="flex gap-2">
            <FnButton size="sm" tone="danger" @click="continueDespiteRisk">{{
              t("common.confirm")
            }}</FnButton>
            <FnButton size="sm" tone="ghost" @click="riskConfirmOpen = false">{{
              t("common.cancel")
            }}</FnButton>
          </div>
        </div>

        <div v-if="skipOpen" class="space-y-2 rounded-lg border border-rule bg-paper-1 p-3">
          <p class="text-sm font-medium text-ink-900">{{ t("jobs.skipPrompt") }}</p>
          <FnSelect
            v-model="skipReason"
            :options="skipOptions"
            :aria-label="t('jobs.skipPrompt')"
          />
          <FnButton size="sm" @click="triage('skip', skipReason)">{{
            t("jobs.confirmSkip")
          }}</FnButton>
        </div>

        <div v-if="selected.other_roles?.length" class="border-t border-rule pt-4">
          <h3 class="mb-2 text-sm font-semibold tracking-wide text-ink-400 uppercase">
            {{ t("jobs.otherRoles") }}
          </h3>
          <ul class="space-y-1 text-sm">
            <li v-for="r in selected.other_roles" :key="r.id">
              <a
                :href="r.apply_url"
                class="text-brand-700 underline"
                target="_blank"
                rel="noopener"
                >{{ r.title }}</a
              >
            </li>
          </ul>
        </div>
      </aside>
    </div>

    <div
      v-if="mobileDetail && selected"
      class="fixed inset-x-0 bottom-16 z-20 flex gap-2 md:bottom-0 border-t border-rule bg-paper-1 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] shadow-[0_-8px_24px_-20px_rgba(16,24,40,0.35)] lg:hidden"
    >
      <FnButton size="sm" tone="quiet" class="shrink-0" @click="triage('shortlist')">{{
        t("jobs.shortlist")
      }}</FnButton>
      <FnButton
        size="sm"
        tone="primary"
        class="flex-1"
        :disabled="!selectedId"
        @click="router.push(`/tailor/${selectedId}`)"
      >
        {{ t("jobs.tailorResume") }}
      </FnButton>
      <FnButton size="sm" tone="ghost" class="shrink-0" @click="skipOpen = true">{{
        t("jobs.skip")
      }}</FnButton>
    </div>
  </div>
</template>
