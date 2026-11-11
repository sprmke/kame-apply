<script setup lang="ts">
import {
  createManualApiV1ApplicationsManualPost,
  createViewApiV1ApplicationViewsPost,
  listApplicationsApiV1ApplicationsGet,
  listTracksApiV1TracksGet,
  listViewsApiV1ApplicationViewsGet,
  metricsApiV1MetricsGet,
  patchStatusApiV1ApplicationsAppIdStatusPatch,
  type ApplicationRead,
  type ApplicationStatusBody,
  type TrackRead,
} from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

const STATUSES = [
  "ready",
  "in_progress",
  "needs_you",
  "submitted",
  "responded",
  "interview",
  "offer",
  "rejected",
  "ghosted",
  "withdrawn",
] as const;

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const auth = useAuthStore();
const qc = useQueryClient();
const route = useRoute();
const router = useRouter();
const fmt = useFormat();
const config = useRuntimeConfig();

const view = ref<"table" | "board">((route.query.view as "table" | "board") || "table");
const trackId = ref((route.query.track as string) || "");
const status = ref((route.query.status as string) || "");
const method = ref((route.query.method as string) || "");
const q = ref((route.query.q as string) || "");
const period = ref<"today" | "week" | "total">("week");

const manualOpen = ref(false);
const manualTrack = ref("");
const manualCompany = ref("");
const manualTitle = ref("");
const manualUrl = ref("");
const savingView = ref(false);
const dragId = ref<string | null>(null);
const noteOpen = ref(false);
const noteText = ref("");
const pendingMove = ref<{ id: string; status: string } | null>(null);

const tracks = useQuery({
  queryKey: computed(() => ["tracks", ws.currentId]),
  queryFn: async () => {
    const { data } = await listTracksApiV1TracksGet({ throwOnError: true });
    return (data ?? []) as TrackRead[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const list = useQuery({
  queryKey: computed(() => [
    "applications",
    ws.currentId,
    trackId.value,
    status.value,
    method.value,
    q.value,
  ]),
  queryFn: async () => {
    const { data } = await listApplicationsApiV1ApplicationsGet({
      query: {
        track_id: trackId.value || undefined,
        status: status.value || undefined,
        method: method.value || undefined,
        q: q.value || undefined,
        limit: 200,
        offset: 0,
      },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

type SavedView = { id: string; name: string; filters?: Record<string, unknown> };
type MetricsPayload = {
  funnel?: Record<string, number>;
  outcomes?: { by_method?: Record<string, Record<string, number>> };
};

const views = useQuery({
  queryKey: computed(() => ["application-views", ws.currentId]),
  queryFn: async () => {
    const { data } = await listViewsApiV1ApplicationViewsGet({ throwOnError: true });
    return (data ?? []) as SavedView[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const metrics = useQuery({
  queryKey: computed(() => ["metrics", ws.currentId, period.value, trackId.value]),
  queryFn: async () => {
    const { data } = await metricsApiV1MetricsGet({
      query: {
        period: period.value,
        track_id: trackId.value || undefined,
      },
      throwOnError: true,
    });
    return data as MetricsPayload;
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const items = computed(() => (list.data.value?.items ?? []) as ApplicationRead[]);
const loading = computed(
  () => !ws.loaded || list.isPending.value || (list.isFetching.value && !list.data.value),
);

const byStatus = computed(() => {
  const map: Record<string, ApplicationRead[]> = {};
  for (const s of STATUSES) map[s] = [];
  for (const a of items.value) {
    const st = a.status === "applied" ? "submitted" : a.status;
    (map[st] ??= []).push(a);
  }
  return map;
});

watch([view, trackId, status, method, q], () => {
  router.replace({
    query: {
      view: view.value === "table" ? undefined : view.value,
      track: trackId.value || undefined,
      status: status.value || undefined,
      method: method.value || undefined,
      q: q.value || undefined,
    },
  });
});

function applyView(filters: Record<string, unknown>) {
  trackId.value = String(filters.track_id || "");
  status.value = String(filters.status || "");
  method.value = String(filters.method || "");
  q.value = String(filters.q || "");
}

async function saveCurrentView() {
  const name = window.prompt(t("applications.viewName"));
  if (!name?.trim()) return;
  savingView.value = true;
  try {
    await createViewApiV1ApplicationViewsPost({
      body: {
        name: name.trim(),
        filters: {
          track_id: trackId.value || null,
          status: status.value || null,
          method: method.value || null,
          q: q.value || null,
        },
      },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["application-views", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    savingView.value = false;
  }
}

async function moveStatus(id: string, next: string, note = "") {
  try {
    await patchStatusApiV1ApplicationsAppIdStatusPatch({
      path: { app_id: id },
      body: { status: next as ApplicationStatusBody["status"], note },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["applications", ws.currentId] });
    await qc.invalidateQueries({ queryKey: ["metrics", ws.currentId] });
    await qc.invalidateQueries({ queryKey: ["home", ws.currentId] });
  } catch (e) {
    const msg = apiError(e);
    if (msg.toLowerCase().includes("note")) {
      pendingMove.value = { id, status: next };
      noteText.value = "";
      noteOpen.value = true;
      return;
    }
    toast.push({ title: msg, tone: "danger" });
  }
}

async function confirmNoteMove() {
  if (!pendingMove.value) return;
  await moveStatus(pendingMove.value.id, pendingMove.value.status, noteText.value.trim());
  noteOpen.value = false;
  pendingMove.value = null;
}

function onDragStart(id: string) {
  dragId.value = id;
}

function onDrop(col: string) {
  if (!dragId.value) return;
  void moveStatus(dragId.value, col);
  dragId.value = null;
}

async function createManual() {
  if (!manualTrack.value || !manualCompany.value.trim() || !manualTitle.value.trim()) {
    toast.push({ title: t("applications.manualRequired"), tone: "danger" });
    return;
  }
  try {
    const { data } = await createManualApiV1ApplicationsManualPost({
      body: {
        track_id: manualTrack.value,
        company: manualCompany.value.trim(),
        title: manualTitle.value.trim(),
        url: manualUrl.value.trim(),
        method: "manual",
      },
      throwOnError: true,
    });
    manualOpen.value = false;
    manualCompany.value = "";
    manualTitle.value = "";
    manualUrl.value = "";
    await qc.invalidateQueries({ queryKey: ["applications", ws.currentId] });
    if (data?.id) await navigateTo(`/applications/${data.id}`);
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function exportCsv() {
  try {
    const base = String(config.public.apiBase || "").replace(/\/$/, "");
    const token = await auth.ensureFresh();
    const res = await fetch(`${base}/api/v1/applications/export?fmt=csv`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(ws.currentId ? { "X-Workspace-Id": ws.currentId } : {}),
      },
    });
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "applications.csv";
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

watch(
  () => tracks.data.value,
  (list) => {
    if (!manualTrack.value && list?.length) manualTrack.value = list[0]!.id;
  },
  { immediate: true },
);

const funnel = computed(() => {
  const f = metrics.data.value?.funnel;
  if (!f) return [];
  return [
    ["discovered", f.discovered ?? 0],
    ["matched", f.matched ?? 0],
    ["shortlisted", f.shortlisted ?? 0],
    ["submitted", f.submitted ?? 0],
    ["responded", f.responded ?? 0],
    ["interview", f.interview ?? 0],
  ] as [string, number][];
});

const outcomes = computed(() => Object.entries(metrics.data.value?.outcomes?.by_method ?? {}));
</script>

<template>
  <div class="mx-auto flex w-full max-w-[1200px] flex-col gap-8">
    <PageHeader :title="t('nav.applications')">
      <template #actions>
        <FnButton tone="quiet" size="sm" @click="exportCsv">{{
          t("applications.export")
        }}</FnButton>
        <FnButton size="sm" :tone="items.length ? 'primary' : 'quiet'" @click="manualOpen = true">{{
          t("applications.log")
        }}</FnButton>
      </template>
    </PageHeader>

    <section
      class="flex flex-wrap items-end gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    >
      <label class="flex flex-col gap-2 text-sm font-semibold text-ink-900">
        {{ t("applications.track") }}
        <select
          v-model="trackId"
          class="min-h-12 min-w-[10rem] rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
        >
          <option value="">{{ t("applications.allTracks") }}</option>
          <option v-for="tr in tracks.data.value ?? []" :key="tr.id" :value="tr.id">
            {{ tr.name }}
          </option>
        </select>
      </label>
      <label class="flex flex-col gap-2 text-sm font-semibold text-ink-900">
        {{ t("applications.status") }}
        <select
          v-model="status"
          class="min-h-12 min-w-[8rem] rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
        >
          <option value="">{{ t("applications.any") }}</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-2 text-sm font-semibold text-ink-900">
        {{ t("applications.method") }}
        <select
          v-model="method"
          class="min-h-12 min-w-[8rem] rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
        >
          <option value="">{{ t("applications.any") }}</option>
          <option value="manual">manual</option>
          <option value="extension">extension</option>
          <option value="runner">runner</option>
          <option value="answer_desk">answer_desk</option>
        </select>
      </label>
      <label class="flex flex-col gap-2 text-sm font-semibold text-ink-900">
        {{ t("applications.find") }}
        <input
          v-model="q"
          type="search"
          class="min-h-12 min-w-[10rem] rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 placeholder:text-ink-400 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
          :placeholder="t('applications.findPlaceholder')"
        />
      </label>
      <div class="flex gap-1 rounded-lg bg-paper-2 p-1">
        <button
          type="button"
          class="min-h-11 rounded-md px-4 text-sm font-semibold transition-colors"
          :class="
            view === 'table'
              ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
              : 'text-ink-600 hover:text-ink-900'
          "
          @click="view = 'table'"
        >
          {{ t("applications.table") }}
        </button>
        <button
          type="button"
          class="min-h-11 rounded-md px-4 text-sm font-semibold transition-colors"
          :class="
            view === 'board'
              ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
              : 'text-ink-600 hover:text-ink-900'
          "
          @click="view = 'board'"
        >
          {{ t("applications.board") }}
        </button>
      </div>
      <FnButton tone="quiet" size="sm" :disabled="savingView" @click="saveCurrentView">{{
        t("applications.saveView")
      }}</FnButton>
    </section>

    <div v-if="(views.data.value ?? []).length" class="flex flex-wrap gap-2">
      <FnChip
        v-for="v in views.data.value ?? []"
        :key="v.id"
        class="cursor-pointer"
        @click="applyView(v.filters || {})"
        >{{ v.name }}</FnChip
      >
    </div>

    <section
      class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    >
      <div class="flex flex-wrap items-center gap-2">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("applications.funnel") }}
        </h2>
        <select
          v-model="period"
          class="min-h-11 rounded-md border border-rule bg-paper-0 px-3 text-sm font-medium text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
          :aria-label="t('today.period')"
        >
          <option value="today">{{ t("today.periodToday") }}</option>
          <option value="week">{{ t("today.periodWeek") }}</option>
          <option value="total">{{ t("today.periodTotal") }}</option>
        </select>
      </div>
      <p class="text-sm tabular-nums text-ink-900">
        <span v-for="([label, n], i) in funnel" :key="label">
          <span v-if="i"> → </span>{{ n }} {{ label }}
        </span>
      </p>
      <ul v-if="outcomes.length" class="flex flex-wrap gap-3 text-xs tabular-nums text-ink-600">
        <li v-for="[m, stats] in outcomes" :key="m">
          {{ m }}: {{ stats.submitted ?? 0 }} / {{ stats.responded ?? 0 }} /
          {{ stats.interview ?? 0 }}
        </li>
      </ul>
    </section>

    <div v-if="loading"><FnSkeleton class="h-40 w-full" /></div>

    <template v-else-if="view === 'table'">
      <div
        v-if="!items.length"
        class="flex flex-col items-start gap-3 rounded-xl border border-dashed border-rule bg-paper-1 p-6"
      >
        <p class="text-sm text-ink-600">{{ t("applications.empty") }}</p>
        <FnButton as-child tone="primary">
          <NuxtLink to="/jobs">{{ t("applications.browseJobs") }}</NuxtLink>
        </FnButton>
      </div>
      <div
        v-else
        class="overflow-x-auto rounded-xl border border-rule bg-paper-1 shadow-[var(--shadow-card)]"
      >
        <table class="w-full min-w-[640px] text-left text-sm">
          <thead class="bg-paper-2 text-xs font-semibold tracking-wide text-ink-600 uppercase">
            <tr>
              <th class="px-4 py-3 font-semibold">{{ t("applications.role") }}</th>
              <th class="px-4 py-3 font-semibold">{{ t("applications.status") }}</th>
              <th class="px-4 py-3 font-semibold">{{ t("applications.method") }}</th>
              <th class="px-4 py-3 font-semibold">{{ t("applications.submitted") }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-rule">
            <tr
              v-for="a in items"
              :key="a.id"
              class="cursor-pointer transition-colors hover:bg-paper-2/60"
              @click="navigateTo(`/applications/${a.id}`)"
            >
              <td class="px-4 py-4">
                <div class="font-medium text-ink-900">{{ a.job_title || "—" }}</div>
                <div class="text-ink-600">{{ a.company_name }}</div>
              </td>
              <td class="px-4 py-4">
                <select
                  class="min-h-11 border border-rule bg-paper-0 px-2"
                  :value="a.status"
                  @click.stop
                  @change="moveStatus(a.id, ($event.target as HTMLSelectElement).value)"
                >
                  <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
                </select>
              </td>
              <td class="py-3 pr-3 font-mono text-[0.6875rem]">{{ a.method }}</td>
              <td class="py-3 pr-3 font-mono text-[0.6875rem]">
                {{ a.submitted_at ? fmt.dateTime(a.submitted_at) : "" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div v-else class="flex gap-3 overflow-x-auto pb-4">
      <section
        v-for="col in STATUSES"
        :key="col"
        class="flex w-56 shrink-0 flex-col gap-2 border border-rule bg-paper-0 p-2"
        @dragover.prevent
        @drop.prevent="onDrop(col)"
      >
        <h3 class="text-xs font-medium tracking-wide text-ink-600 uppercase">
          {{ col }}
          <span class="font-mono">({{ byStatus[col]?.length ?? 0 }})</span>
        </h3>
        <article
          v-for="a in byStatus[col] ?? []"
          :key="a.id"
          draggable="true"
          class="cursor-grab border border-rule bg-paper-1 p-2 text-sm active:cursor-grabbing"
          @dragstart="onDragStart(a.id)"
          @click="navigateTo(`/applications/${a.id}`)"
        >
          <p class="font-medium text-ink-900">{{ a.job_title }}</p>
          <p class="text-ink-600">{{ a.company_name }}</p>
        </article>
      </section>
    </div>

    <div
      v-if="manualOpen"
      class="fixed inset-0 z-40 flex items-end justify-center bg-ink-900/40 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      @click.self="manualOpen = false"
    >
      <div class="w-full max-w-md space-y-3 border border-rule bg-paper-0 p-4">
        <h2 class="font-medium">{{ t("applications.log") }}</h2>
        <label class="flex flex-col gap-2 text-sm font-semibold text-ink-900">
          {{ t("applications.track") }}
          <select
            v-model="manualTrack"
            class="min-h-11 border border-rule bg-paper-0 px-2 text-sm text-ink-900"
          >
            <option v-for="tr in tracks.data.value ?? []" :key="tr.id" :value="tr.id">
              {{ tr.name }}
            </option>
          </select>
        </label>
        <label class="flex flex-col gap-2 text-sm font-semibold text-ink-900">
          {{ t("applications.company") }}
          <input
            v-model="manualCompany"
            class="min-h-11 border border-rule bg-paper-0 px-2 text-sm text-ink-900"
          />
        </label>
        <label class="flex flex-col gap-2 text-sm font-semibold text-ink-900">
          {{ t("applications.title") }}
          <input
            v-model="manualTitle"
            class="min-h-11 border border-rule bg-paper-0 px-2 text-sm text-ink-900"
          />
        </label>
        <label class="flex flex-col gap-2 text-sm font-semibold text-ink-900">
          {{ t("applications.url") }}
          <input
            v-model="manualUrl"
            class="min-h-11 border border-rule bg-paper-0 px-2 text-sm text-ink-900"
          />
        </label>
        <div class="flex justify-end gap-2">
          <FnButton tone="quiet" size="sm" @click="manualOpen = false">{{
            t("common.cancel")
          }}</FnButton>
          <FnButton size="sm" @click="createManual">{{ t("common.save") }}</FnButton>
        </div>
      </div>
    </div>

    <div
      v-if="noteOpen"
      class="fixed inset-0 z-40 flex items-end justify-center bg-ink-900/40 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      @click.self="noteOpen = false"
    >
      <div class="w-full max-w-md space-y-3 border border-rule bg-paper-0 p-4">
        <h2 class="font-medium">{{ t("applications.noteRequired") }}</h2>
        <textarea
          v-model="noteText"
          rows="3"
          class="w-full border border-rule bg-paper-0 p-2 text-sm"
        />
        <div class="flex justify-end gap-2">
          <FnButton tone="quiet" size="sm" @click="noteOpen = false">{{
            t("common.cancel")
          }}</FnButton>
          <FnButton size="sm" :disabled="!noteText.trim()" @click="confirmNoteMove">{{
            t("common.save")
          }}</FnButton>
        </div>
      </div>
    </div>
  </div>
</template>
