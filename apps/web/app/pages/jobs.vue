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
import { FnButton, FnChip, FnRiskSeal, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const auth = useAuthStore();
const qc = useQueryClient();
const route = useRoute();
const router = useRouter();

const trackFilter = computed(() => (route.query.track as string) || undefined);
const includeIneligible = ref(false);
const sort = ref<"score" | "newest" | "salary">("score");
const selectedId = ref<string | null>(null);
const helpOpen = ref(false);
const skipOpen = ref(false);
const skipReason = ref("too junior");
const riskConfirmOpen = ref(false);

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

function reasonText(r: unknown): string {
  if (typeof r === "string") return r;
  if (r && typeof r === "object") {
    const o = r as { evidence?: string; signal?: string };
    return o.evidence || o.signal || "";
  }
  return "";
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
  rows,
  (list) => {
    if (!list.length) {
      selectedId.value = null;
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

async function exportCsv() {
  try {
    const token = await auth.ensureFresh();
    const qs = new URLSearchParams({
      include_not_eligible: String(includeIneligible.value),
    });
    if (trackFilter.value) qs.set("track_id", trackFilter.value);
    const base = useRuntimeConfig().public.apiBase as string;
    const res = await fetch(`${base}/api/v1/jobs/export.csv?${qs}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(ws.currentId ? { "X-Workspace-Id": ws.currentId } : {}),
      },
    });
    if (!res.ok) {
      throw new Error(`export failed (${res.status})`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "jobs.csv";
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    toast.push({ title: apiError(err), tone: "danger" });
  }
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

function salaryLabel(s: Record<string, unknown> | undefined): string {
  if (!s) return "";
  if (s.min != null) return String(s.min);
  return "";
}

function chipTone(v?: string | null): "neutral" | "accent" | "pencil" {
  if (v === "met") return "accent";
  if (v === "partial") return "pencil";
  return "neutral";
}
</script>

<template>
  <div class="flex h-[calc(100dvh-4rem)] flex-col gap-3 p-4 md:p-6">
    <header class="flex flex-wrap items-center gap-2">
      <h1 class="font-display text-xl text-ink-900">{{ t("nav.jobs") }}</h1>
      <div class="ml-auto flex flex-wrap items-center gap-2">
        <label class="flex items-center gap-1 text-sm text-ink-600">
          <input v-model="includeIneligible" type="checkbox" class="accent-persimmon-600" />
          Ineligible
        </label>
        <select
          v-model="sort"
          class="rounded border border-ink-200 bg-paper-50 px-2 py-1 text-sm"
          aria-label="Sort"
        >
          <option value="score">Match</option>
          <option value="newest">Newest</option>
          <option value="salary">Salary</option>
        </select>
        <FnButton size="sm" tone="ghost" @click="exportCsv">CSV</FnButton>
        <FnButton size="sm" tone="ghost" aria-label="Shortcuts" @click="helpOpen = !helpOpen"
          >?</FnButton
        >
      </div>
    </header>

    <div
      v-if="helpOpen"
      class="rounded border border-ink-200 bg-paper-100 px-3 py-2 text-sm text-ink-700"
    >
      j/k move · s shortlist · x skip · t tailor · o open · ?
    </div>

    <div v-if="loading" class="grid gap-2">
      <FnSkeleton class="h-10" />
      <FnSkeleton class="h-10" />
      <FnSkeleton class="h-10" />
    </div>

    <div v-else-if="!rows.length" class="flex flex-1 flex-col items-start gap-3 text-ink-600">
      <p>No jobs</p>
      <ul v-if="relax.data.value?.length" class="space-y-1 text-sm">
        <li v-for="s in relax.data.value" :key="s.label">{{ s.label }}: +{{ s.gained }}</li>
      </ul>
      <FnButton size="sm" @click="router.push('/tracks')">Tracks</FnButton>
    </div>

    <div
      v-else
      class="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)_minmax(0,18rem)]"
    >
      <ul class="min-h-0 overflow-y-auto border-r border-ink-100 pr-2" role="listbox">
        <li
          v-for="row in rows"
          :key="row.id"
          role="option"
          :aria-selected="row.id === selectedId"
          class="cursor-pointer border-b border-ink-100 px-2 py-2 text-sm hover:bg-paper-100"
          :class="row.id === selectedId ? 'bg-paper-100' : ''"
          @click="selectedId = row.id"
        >
          <div class="flex items-baseline gap-2">
            <span class="font-mono text-xs tabular-nums text-persimmon-700">{{
              row.score != null ? Math.round(row.score) : "-"
            }}</span>
            <span class="truncate font-medium text-ink-900">{{ row.title }}</span>
          </div>
          <div class="mt-0.5 flex flex-wrap gap-1 text-xs text-ink-500">
            <span>{{ row.company_name }}</span>
            <FnRiskSeal
              v-if="row.risk_level"
              :level="sealLevel(row.risk_level)"
              :label="sealLabel(row.risk_level)"
            />
            <FnChip v-if="row.eligibility === 'not_eligible'">Ineligible</FnChip>
            <FnChip v-for="r in (row.reasons || []).slice(0, 2)" :key="String(r)">{{ r }}</FnChip>
          </div>
        </li>
      </ul>

      <section v-if="selected" class="min-h-0 overflow-y-auto">
        <h2 class="font-display text-2xl text-ink-900">{{ selected.title }}</h2>
        <p class="mt-1 text-sm text-ink-600">
          {{ selected.company_name }}
          <span v-if="selected.work_mode"> · {{ selected.work_mode }}</span>
          <span v-if="salaryLabel(selected.salary)"> · {{ salaryLabel(selected.salary) }}</span>
        </p>
        <p
          v-if="selected.eligibility_quote"
          class="mt-2 border-l-2 border-persimmon-700 pl-3 text-sm italic text-ink-700"
        >
          {{ selected.eligibility_quote }}
        </p>
        <p v-if="selected.few_stated_requirements" class="mt-2 text-xs text-ink-500">
          Few stated requirements
        </p>
        <div class="mt-4 whitespace-pre-wrap text-sm text-ink-800">
          {{ selected.description_text }}
        </div>
      </section>
      <FnSkeleton v-else class="h-40" />

      <aside v-if="selected" class="min-h-0 overflow-y-auto border-l border-ink-100 pl-3">
        <div class="mb-3">
          <div class="font-mono text-3xl tabular-nums text-persimmon-700">
            {{ selected.score != null ? Math.round(selected.score) : "-" }}
          </div>
          <div class="mt-1 flex flex-wrap gap-1">
            <FnRiskSeal
              v-if="selected.risk_level"
              :level="sealLevel(selected.risk_level)"
              :label="sealLabel(selected.risk_level)"
            />
            <FnChip v-for="r in selected.reasons || []" :key="String(r)">{{ r }}</FnChip>
            <FnChip v-if="selected.ai_review_paused" tone="pencil">AI review paused</FnChip>
          </div>
          <ul
            v-if="selected.risk_reasons?.length"
            class="mt-2 space-y-1 border-l-2 border-oxblood-600 pl-2 text-xs text-ink-700"
          >
            <li v-for="(r, i) in selected.risk_reasons.slice(0, 5)" :key="i">
              {{ reasonText(r) }}
            </li>
          </ul>
        </div>
        <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">Fit</h3>
        <ul class="mb-4 space-y-2 text-sm">
          <li
            v-for="q in selected.qualifications || []"
            :key="String(q.id)"
            class="border-b border-ink-50 pb-2"
          >
            <div class="flex items-start gap-2">
              <FnChip :tone="chipTone(String(q.verdict || ''))">{{ q.kind }}</FnChip>
              <span class="text-ink-800">{{ q.text }}</span>
            </div>
            <p v-if="q.verdict" class="mt-1 text-xs text-ink-500">
              {{ q.verdict }}<span v-if="q.evidence_quote"> · {{ q.evidence_quote }}</span>
            </p>
          </li>
        </ul>
        <div class="flex flex-wrap gap-2">
          <FnButton size="sm" @click="triage('shortlist')">Shortlist</FnButton>
          <FnButton size="sm" :disabled="!selectedId" @click="router.push(`/tailor/${selectedId}`)">
            Tailor
          </FnButton>
          <FnButton size="sm" tone="ghost" @click="skipOpen = true">Skip</FnButton>
          <FnButton size="sm" tone="ghost" :disabled="!selected.apply_url" @click="openOriginal">
            Open
          </FnButton>
          <FnButton size="sm" tone="ghost" @click="markApplied">{{
            t("applications.markApplied")
          }}</FnButton>
          <FnButton
            v-if="selected.risk_level === 'red' || selected.risk_level === 'yellow'"
            size="sm"
            tone="ghost"
            @click="riskConfirmOpen = true"
            >Continue</FnButton
          >
        </div>
        <div
          v-if="riskConfirmOpen && selected"
          class="mt-3 space-y-2 rounded border border-oxblood-600 p-2 text-sm"
        >
          <p>
            This job is marked
            {{ selected.risk_level === "red" ? "high risk" : "caution" }}. Continue anyway?
          </p>
          <div class="flex gap-2">
            <FnButton size="sm" @click="continueDespiteRisk">Confirm</FnButton>
            <FnButton size="sm" tone="ghost" @click="riskConfirmOpen = false">Cancel</FnButton>
          </div>
        </div>
        <div v-if="skipOpen" class="mt-3 space-y-2 rounded border border-ink-200 p-2">
          <select
            v-model="skipReason"
            class="w-full rounded border border-ink-200 px-2 py-1 text-sm"
          >
            <option>too junior</option>
            <option>too senior</option>
            <option>salary</option>
            <option>location</option>
            <option>missing skills</option>
            <option>wrong title</option>
            <option>other</option>
          </select>
          <FnButton size="sm" @click="triage('skip', skipReason)">Confirm</FnButton>
        </div>
        <div v-if="selected.other_roles?.length" class="mt-6">
          <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
            Other roles
          </h3>
          <ul class="space-y-1 text-sm">
            <li v-for="r in selected.other_roles" :key="r.id">
              <a
                :href="r.apply_url"
                class="text-persimmon-700 underline"
                target="_blank"
                rel="noopener"
                >{{ r.title }}</a
              >
            </li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>
