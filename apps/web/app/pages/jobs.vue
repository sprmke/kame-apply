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
import { FnButton, FnChip, FnRiskSeal, FnSelect, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const route = useRoute();
const router = useRouter();

const trackFilter = computed(() => (route.query.track as string) || undefined);
const includeIneligible = ref(false);
const sort = ref<"score" | "newest" | "salary">("score");
const sortOptions = [
  { value: "score", label: "Match" },
  { value: "newest", label: "Newest" },
  { value: "salary", label: "Salary" },
];
const sortValue = computed({
  get: () => sort.value,
  set: (value: string) => {
    sort.value = value as typeof sort.value;
  },
});
const selectedId = ref<string | null>(null);
const helpOpen = ref(false);
const skipOpen = ref(false);
const skipReason = ref("too junior");
const skipOptions = [
  { value: "too junior", label: "Too junior" },
  { value: "too senior", label: "Too senior" },
  { value: "salary", label: "Salary" },
  { value: "location", label: "Location" },
  { value: "missing skills", label: "Missing skills" },
  { value: "wrong title", label: "Wrong title" },
  { value: "other", label: "Other" },
];
const riskConfirmOpen = ref(false);
const showAllFit = ref(false);
const mobileDetail = ref(false);

function sealLevel(level: string | null | undefined): "clear" | "caution" | "danger" {
  if (level === "red") return "danger";
  if (level === "yellow") return "caution";
  return "clear";
}

function sealLabel(level: string | null | undefined): string {
  if (level === "red") return "High risk";
  if (level === "yellow") return "Caution";
  return "Clear";
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
  ]),
  queryFn: async () => {
    const { data } = await listJobsApiV1JobsGet({
      query: {
        track_id: trackFilter.value,
        include_not_eligible: includeIneligible.value,
        sort: sort.value,
        limit: 100,
      },
      throwOnError: true,
    });
    return (data ?? []) as BoardJobRead[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const rows = computed(() => board.data.value ?? []);
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
const allUnproven = computed(() => {
  const rows = selected.value?.qualifications ?? [];
  return rows.length > 0 && rows.every((q) => String(q.verdict || "").includes("not"));
});

function kindLabel(kind?: string | null): string {
  if (kind === "must") return t("jobs.required");
  if (kind === "nice") return t("jobs.preferred");
  return kind || "";
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
    class="mx-auto flex min-h-[calc(100dvh-4rem)] w-full max-w-[1600px] flex-col gap-4 p-4 pb-24 md:p-6 lg:h-[calc(100dvh-4rem)] lg:pb-6"
  >
    <header
      class="flex flex-wrap items-end justify-between gap-4"
      :class="mobileDetail ? 'max-lg:hidden' : ''"
    >
      <div class="min-w-0">
        <h1 class="text-3xl font-bold tracking-[-0.03em] text-ink-900">{{ t("nav.jobs") }}</h1>
        <p class="mt-1 max-w-2xl text-sm leading-6 text-ink-600">
          Ranked matches from your searches. Pick a job to see the posting and why it fits.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <label
          class="flex min-h-12 items-center gap-2 rounded-md border border-rule bg-paper-1 px-3 text-sm font-medium text-ink-600 shadow-[var(--shadow-card)]"
          title="Include jobs where you may not meet every requirement"
        >
          <input
            v-model="includeIneligible"
            type="checkbox"
            class="size-5 rounded border-rule accent-brand-600"
            :aria-label="t('jobs.includeIneligible')"
          />
          {{ t("jobs.includeIneligible") }}
        </label>
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-ink-600">Sort</span>
          <div class="w-36">
            <FnSelect v-model="sortValue" :options="sortOptions" ariaLabel="Sort jobs" />
          </div>
        </div>
      </div>
    </header>

    <div
      v-if="helpOpen"
      class="rounded border border-rule bg-paper-2 px-3 py-2 text-sm text-ink-600"
    >
      j/k move · s shortlist · x skip · t tailor · o open · ?
    </div>

    <div v-if="loading" class="grid gap-2">
      <FnSkeleton class="h-10" />
      <FnSkeleton class="h-10" />
      <FnSkeleton class="h-10" />
    </div>

    <div
      v-else-if="!rows.length"
      class="flex w-full flex-col items-start gap-4 rounded-xl border border-dashed border-rule bg-paper-1 p-6 text-ink-600"
    >
      <div class="flex flex-col gap-1">
        <p class="text-lg font-semibold text-ink-900">No jobs</p>
        <p class="text-sm text-ink-600">Run a search to start.</p>
      </div>
      <ul v-if="relax.data.value?.length" class="space-y-1 text-sm">
        <li v-for="s in relax.data.value" :key="s.label">{{ s.label }}: +{{ s.gained }}</li>
      </ul>
      <FnButton tone="primary" size="sm" @click="router.push('/tracks')">{{
        t("nav.tracks")
      }}</FnButton>
    </div>

    <div
      v-else
      class="grid min-h-0 flex-1 gap-4 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)] lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)_minmax(0,18rem)]"
    >
      <ul
        :class="mobileDetail ? 'hidden lg:block' : 'block'"
        class="border-r border-rule pr-2 lg:min-h-0 lg:overflow-y-auto"
        role="listbox"
      >
        <li
          v-for="row in rows"
          :key="row.id"
          role="option"
          :aria-selected="row.id === selectedId"
          class="cursor-pointer rounded-lg border-b border-rule px-3 py-3 text-sm transition-colors hover:bg-paper-2"
          :class="row.id === selectedId ? 'bg-brand-50' : ''"
          @click="selectJob(row.id)"
        >
          <div class="flex items-baseline gap-2">
            <span class="font-mono text-xs tabular-nums text-brand-700">{{
              row.score != null ? Math.round(row.score) : "-"
            }}</span>
            <span class="line-clamp-2 font-medium text-ink-900">{{ row.title }}</span>
          </div>
          <div class="mt-0.5 flex flex-wrap gap-1 text-xs text-ink-400">
            <span>{{ row.company_name }}</span>
            <FnRiskSeal
              v-if="row.risk_level === 'yellow' || row.risk_level === 'red'"
              :level="sealLevel(row.risk_level)"
              :label="sealLabel(row.risk_level)"
            />
            <FnChip v-if="row.eligibility === 'not_eligible'">Ineligible</FnChip>
            <FnChip v-for="r in visibleReasons(row.reasons).slice(0, 1)" :key="String(r)">{{
              reasonText(r)
            }}</FnChip>
          </div>
        </li>
      </ul>

      <section
        v-if="selected"
        :class="mobileDetail ? 'block' : 'hidden lg:block'"
        class="min-h-0 lg:overflow-y-auto"
      >
        <button
          type="button"
          class="mb-3 flex min-h-11 items-center gap-2 rounded-md px-2 text-sm font-semibold text-ink-600 hover:bg-paper-2 lg:hidden"
          @click="mobileDetail = false"
        >
          <NavIcon name="ph:arrow-left" :size="16" /> Back to jobs
        </button>
        <h2 class="text-3xl font-bold tracking-[-0.03em] text-ink-900">{{ selected.title }}</h2>
        <p class="mt-1 text-sm text-ink-600">
          {{ selected.company_name }}
          <span v-if="selected.work_mode"> · {{ workModeLabel(selected.work_mode) }}</span>
          <span v-if="salaryLabel(selected.salary)"> · {{ salaryLabel(selected.salary) }}</span>
        </p>
        <p
          v-if="selected.eligibility_quote"
          class="mt-2 border-l-2 border-brand-700 pl-3 text-sm italic text-ink-600"
        >
          {{ selected.eligibility_quote }}
        </p>
        <p v-if="selected.few_stated_requirements" class="mt-2 text-xs text-ink-400">
          Few stated requirements
        </p>
        <div class="mt-5 border-t border-rule pt-5">
          <h3 class="mb-3 text-sm font-semibold tracking-wide text-ink-400 uppercase">
            Job description
          </h3>
          <JobDescription :text="selected.description_text" />
        </div>
      </section>
      <FnSkeleton v-else class="h-40" />

      <aside
        v-if="selected"
        :class="mobileDetail ? 'block' : 'hidden lg:block'"
        class="flex flex-col gap-5 rounded-lg border-t border-rule bg-paper-0 p-4 lg:min-h-0 lg:overflow-y-auto lg:border-t-0 lg:border-l lg:pl-4"
      >
        <section class="flex flex-col gap-3">
          <div class="flex items-end gap-3">
            <div>
              <div class="text-3xl font-bold tabular-nums text-brand-700">
                {{ selected.score != null ? Math.round(selected.score) : "-" }}
              </div>
              <p class="text-xs text-ink-400">{{ t("jobs.matchScore") }}</p>
            </div>
            <FnRiskSeal
              v-if="selected.risk_level"
              class="mb-1"
              :level="sealLevel(selected.risk_level)"
              :label="sealLabel(selected.risk_level)"
            />
          </div>
          <div v-if="visibleReasons(selected.reasons).length" class="flex flex-wrap gap-1">
            <FnChip v-for="r in visibleReasons(selected.reasons).slice(0, 5)" :key="String(r)">{{
              reasonText(r)
            }}</FnChip>
          </div>
          <ul
            v-if="visibleRiskReasons.length"
            class="space-y-1 border-l-2 border-oxblood-600 pl-3 text-sm leading-6 text-ink-600"
          >
            <li v-for="(r, i) in visibleRiskReasons" :key="i">{{ reasonText(r) }}</li>
          </ul>
        </section>

        <section class="flex flex-col gap-2 border-t border-rule pt-4">
          <h3 class="text-sm font-semibold tracking-wide text-ink-400 uppercase">Next</h3>
          <div class="grid grid-cols-2 gap-2">
            <FnButton size="sm" tone="primary" @click="router.push(`/tailor/${selectedId}`)">
              Tailor
            </FnButton>
            <FnButton size="sm" tone="quiet" @click="triage('shortlist')"> Shortlist </FnButton>
            <FnButton
              size="sm"
              tone="quiet"
              :disabled="!selected.apply_url"
              title="Open the original posting"
              @click="openOriginal"
            >
              Open
            </FnButton>
            <FnButton size="sm" tone="ghost" @click="skipOpen = true">Skip</FnButton>
          </div>
          <FnButton size="sm" tone="ghost" class="self-start" @click="markApplied">{{
            t("applications.markApplied")
          }}</FnButton>
        </section>

        <section class="flex flex-col gap-3 border-t border-rule pt-4">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold tracking-wide text-ink-400 uppercase">
              {{ t("jobs.fit") }}
            </h3>
            <span v-if="selected.qualifications?.length" class="text-xs text-ink-400">
              {{ selected.qualifications.length }} checks
            </span>
          </div>
          <p class="text-sm leading-6 text-ink-600">How your profile lines up with this posting.</p>
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
              <p
                class="mt-2 line-clamp-3 text-sm leading-6 text-ink-900"
                :title="String(q.text || '')"
              >
                {{ q.text }}
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
            This posting is marked
            {{ selected.risk_level === "red" ? "high risk" : "caution" }}. Review the reasons before
            continuing.
          </p>
          <FnButton size="sm" tone="danger" class="self-start" @click="riskConfirmOpen = true">
            Continue anyway
          </FnButton>
        </section>

        <div
          v-if="riskConfirmOpen && selected"
          class="space-y-2 rounded-lg border border-oxblood-600 bg-paper-1 p-3 text-sm"
        >
          <p class="leading-6">
            This job is marked
            {{ selected.risk_level === "red" ? "high risk" : "caution" }}. Continue anyway?
          </p>
          <div class="flex gap-2">
            <FnButton size="sm" tone="danger" @click="continueDespiteRisk">Confirm</FnButton>
            <FnButton size="sm" tone="ghost" @click="riskConfirmOpen = false">Cancel</FnButton>
          </div>
        </div>

        <div v-if="skipOpen" class="space-y-2 rounded-lg border border-rule bg-paper-1 p-3">
          <p class="text-sm font-medium text-ink-900">Why skip this job?</p>
          <FnSelect v-model="skipReason" :options="skipOptions" ariaLabel="Skip reason" />
          <FnButton size="sm" @click="triage('skip', skipReason)">Confirm skip</FnButton>
        </div>

        <div v-if="selected.other_roles?.length" class="border-t border-rule pt-4">
          <h3 class="mb-2 text-sm font-semibold tracking-wide text-ink-400 uppercase">
            Other roles
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
      class="fixed inset-x-0 bottom-16 z-20 flex gap-2 border-t border-rule bg-paper-1 p-3 shadow-[0_-8px_24px_-20px_rgba(16,24,40,0.35)] lg:hidden"
    >
      <FnButton size="sm" tone="quiet" @click="triage('shortlist')">Shortlist</FnButton>
      <FnButton
        size="sm"
        tone="primary"
        :disabled="!selectedId"
        @click="router.push(`/tailor/${selectedId}`)"
      >
        Tailor
      </FnButton>
      <FnButton size="sm" tone="ghost" :disabled="!selected.apply_url" @click="openOriginal">
        Open
      </FnButton>
      <FnButton size="sm" tone="ghost" @click="skipOpen = true">Skip</FnButton>
    </div>
  </div>
</template>
