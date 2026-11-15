<script setup lang="ts">
import {
  openSetupApiV1OnboardingSetupsGet,
  getProvenanceApiV1OnboardingSetupsProvenanceGet,
  homeApiV1HomeGet,
  listJobsApiV1JobsGet,
  revertSetupApiV1OnboardingSetupsDraftIdRevertPost,
  type BoardJobRead,
} from "@kame/api-client";
import { FnButton, FnEmptyState, FnFolderTab, FnRiskSeal, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

type HomeBrief = {
  headline?: string;
  empty?: boolean;
  needs_you?: { count?: number; items: { href: string; title: string; detail: string }[] };
  kpis?: {
    kpis?: {
      submitted?: number;
      response_rate?: number;
      interviews?: number;
      matched?: number;
    };
  };
  tracks?: {
    id: string;
    name: string;
    color_hue?: number;
    autonomy?: string;
    pipeline?: Record<string, number>;
  }[];
};

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const auth = useAuthStore();
const ws = useWorkspaceStore();
const toast = useToast();
const apiError = useApiError();
const qc = useQueryClient();
const { profileId } = useActiveProfile();

const openSetup = useQuery({
  queryKey: computed(() => ["setup-open", ws.currentId, profileId.value]),
  queryFn: async () => {
    const { data } = await openSetupApiV1OnboardingSetupsGet({
      query: { profile_id: profileId.value ?? undefined },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});

const provenance = useQuery({
  queryKey: computed(() => ["setup-provenance", ws.currentId, profileId.value]),
  queryFn: async () => {
    const { data } = await getProvenanceApiV1OnboardingSetupsProvenanceGet({
      query: { profile_id: profileId.value! },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});

const doneDismissed = ref(false);
const doneKey = computed(() => `kame.setupDoneCard.${provenance.data.value?.draft_id ?? "none"}`);

watch(
  () => provenance.data.value?.draft_id,
  () => {
    doneDismissed.value = false;
    if (typeof window !== "undefined") {
      doneDismissed.value = window.localStorage.getItem(doneKey.value) === "1";
    }
  },
  { immediate: true },
);

const recentDone = computed(() => {
  const row = provenance.data.value;
  if (!row || doneDismissed.value) return null;
  const applied = new Date(row.applied_at).getTime();
  if (!Number.isFinite(applied) || Date.now() - applied > 7 * 24 * 60 * 60 * 1000) return null;
  return row;
});

function dismissDone() {
  doneDismissed.value = true;
  window.localStorage.setItem(doneKey.value, "1");
}

async function undoSetup() {
  const row = provenance.data.value;
  if (!row || !window.confirm(t("setup.undoConfirm"))) return;
  try {
    await revertSetupApiV1OnboardingSetupsDraftIdRevertPost({
      path: { draft_id: row.draft_id },
      throwOnError: true,
    });
    await qc.invalidateQueries();
    toast.push({ title: t("setup.undone"), tone: "success" });
  } catch (error) {
    toast.push({ title: apiError(error), tone: "danger" });
  }
}

const qc = useQueryClient();
const setupOpen = useQuery({
  queryKey: computed(() => ["today-setup-open", ws.currentId, profileId.value]),
  queryFn: async () => {
    const id = profileId.value;
    if (!id) return null;
    const { data } = await getOpenSetupApiV1OnboardingSetupsGet({
      query: { profile_id: id },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const provenance = useQuery({
  queryKey: computed(() => ["today-setup-provenance", ws.currentId, profileId.value]),
  queryFn: async () => {
    const id = profileId.value;
    if (!id) return null;
    const { data } = await getProvenanceApiV1OnboardingSetupsProvenanceGet({
      query: { profile_id: id },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const setupDismissed = ref(false);
const undoBusy = ref(false);
const recentSetup = computed(() => {
  const applied = provenance.data.value;
  if (!applied) return null;
  const age = Date.now() - new Date(applied.applied_at).getTime();
  return age <= 7 * 86_400_000 ? applied : null;
});
watch(
  recentSetup,
  (applied) => {
    if (!applied || !import.meta.client) return;
    setupDismissed.value = localStorage.getItem(`kame.setupCard.${applied.draft_id}`) === "1";
  },
  { immediate: true },
);
function dismissSetupCard() {
  if (!recentSetup.value || !import.meta.client) return;
  localStorage.setItem(`kame.setupCard.${recentSetup.value.draft_id}`, "1");
  setupDismissed.value = true;
}
async function undoSetup() {
  const applied = recentSetup.value;
  if (!applied || !window.confirm(t("setup.undoConfirm"))) return;
  undoBusy.value = true;
  try {
    await revertSetupApiV1OnboardingSetupsDraftIdRevertPost({
      path: { draft_id: applied.draft_id },
      throwOnError: true,
    });
    await qc.invalidateQueries();
    toast.push({ title: t("setup.undone"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    undoBusy.value = false;
  }
}
const openSetup = useQuery({
  queryKey: computed(() => ["today-open-setup", ws.currentId, profileId.value]),
  queryFn: async () => {
    const id = profileId.value;
    if (!id) return null;
    const { data } = await getOpenSetupApiV1OnboardingSetupsGet({
      query: { profile_id: id },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const provenance = useQuery({
  queryKey: computed(() => ["today-setup-provenance", ws.currentId, profileId.value]),
  queryFn: async () => {
    const id = profileId.value;
    if (!id) return null;
    const { data } = await getProvenanceApiV1OnboardingSetupsProvenanceGet({
      query: { profile_id: id },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const setupDismissed = ref(false);
const undoing = ref(false);
const recentSetup = computed(() => {
  const row = provenance.data.value;
  if (!row) return null;
  const age = Date.now() - new Date(row.applied_at).getTime();
  return age <= 7 * 86_400_000 ? row : null;
});
watch(
  recentSetup,
  (row) => {
    if (!row || !import.meta.client) return;
    setupDismissed.value = localStorage.getItem(`kame.setupDoneCard.${row.draft_id}`) === "1";
  },
  { immediate: true },
);
function dismissSetupCard() {
  if (!recentSetup.value || !import.meta.client) return;
  localStorage.setItem(`kame.setupDoneCard.${recentSetup.value.draft_id}`, "1");
  setupDismissed.value = true;
}
async function undoSetup() {
  const row = recentSetup.value;
  if (!row || !window.confirm(t("setup.undoConfirm"))) return;
  undoing.value = true;
  try {
    await revertSetupApiV1OnboardingSetupsDraftIdRevertPost({
      path: { draft_id: row.draft_id },
      throwOnError: true,
    });
    await qc.invalidateQueries();
    toast.push({ title: t("setup.undone"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    undoing.value = false;
  }
}

const openSetup = useQuery({
  queryKey: computed(() => ["today-setup-open", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data } = await getOpenSetupApiV1OnboardingSetupsGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const provenance = useQuery({
  queryKey: computed(() => ["today-setup-provenance", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data } = await getProvenanceApiV1OnboardingSetupsProvenanceGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const setupDismissed = ref(false);
const undoing = ref(false);
const recentSetup = computed(() => {
  const row = provenance.data.value;
  if (!row) return null;
  const age = Date.now() - new Date(row.applied_at).getTime();
  return age <= 7 * 86_400_000 ? row : null;
});
watch(
  recentSetup,
  (row) => {
    if (!row || !import.meta.client) return;
    setupDismissed.value = localStorage.getItem(`kame.setupDone.${row.draft_id}`) === "1";
  },
  { immediate: true },
);
function dismissSetupCard() {
  if (!recentSetup.value || !import.meta.client) return;
  localStorage.setItem(`kame.setupDone.${recentSetup.value.draft_id}`, "1");
  setupDismissed.value = true;
}
async function undoSetup() {
  const row = recentSetup.value;
  if (!row || !window.confirm(t("setup.undoConfirm"))) return;
  undoing.value = true;
  try {
    await revertSetupApiV1OnboardingSetupsDraftIdRevertPost({
      path: { draft_id: row.draft_id },
      throwOnError: true,
    });
    await qc.invalidateQueries();
    toast.push({ title: t("setup.undone"), tone: "success" });
  } catch (error) {
    toast.push({ title: apiError(error), tone: "danger" });
  } finally {
    undoing.value = false;
  }
}

const home = useQuery({
  queryKey: computed(() => ["home", ws.currentId]),
  queryFn: async () => {
    const { data } = await homeApiV1HomeGet({
      query: { period: "week" },
      throwOnError: true,
    });
    return data as HomeBrief;
  },
  enabled: computed(() => Boolean(ws.currentId)),
  refetchInterval: 30_000,
});

const openSetup = useQuery({
  queryKey: computed(() => ["today-open-setup", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data } = await getOpenSetupApiV1OnboardingSetupsGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const setupProvenance = useQuery({
  queryKey: computed(() => ["today-provenance", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data } = await getProvenanceApiV1OnboardingSetupsProvenanceGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const setupDismissed = ref(false);
const undoing = ref(false);
const recentSetup = computed(() => {
  const row = setupProvenance.data.value;
  if (!row) return null;
  const age = Date.now() - new Date(row.applied_at).getTime();
  return age <= 7 * 86_400_000 ? row : null;
});
watch(
  recentSetup,
  (row) => {
    if (!row || !import.meta.client) return;
    setupDismissed.value = localStorage.getItem(`kame.setupDone.${row.draft_id}`) === "1";
  },
  { immediate: true },
);
function dismissSetup() {
  if (!recentSetup.value || !import.meta.client) return;
  localStorage.setItem(`kame.setupDone.${recentSetup.value.draft_id}`, "1");
  setupDismissed.value = true;
}
async function undoSetup() {
  const row = recentSetup.value;
  if (!row || !window.confirm(t("setup.undoConfirm"))) return;
  undoing.value = true;
  try {
    await revertSetupApiV1OnboardingSetupsDraftIdRevertPost({
      path: { draft_id: row.draft_id },
      throwOnError: true,
    });
    await qc.invalidateQueries();
    toast.push({ title: t("setup.undone"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    undoing.value = false;
  }
}

const openSetup = useQuery({
  queryKey: computed(() => ["today-setup-open", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data: row } = await getOpenSetupApiV1OnboardingSetupsGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return row;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const setupProvenance = useQuery({
  queryKey: computed(() => ["today-setup-provenance", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data: row } = await getProvenanceApiV1OnboardingSetupsProvenanceGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return row;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const setupDismissed = ref(false);
const recentSetup = computed(() => {
  const row = setupProvenance.data.value;
  if (!row) return null;
  const age = Date.now() - new Date(row.applied_at).getTime();
  return age <= 7 * 86_400_000 ? row : null;
});
watch(
  recentSetup,
  (row) => {
    if (!row || !import.meta.client) return;
    setupDismissed.value = localStorage.getItem(`kame.setupDone.${row.draft_id}`) === "1";
  },
  { immediate: true },
);

async function undoSetup() {
  const row = recentSetup.value;
  if (!row || !window.confirm(t("setup.undoConfirm"))) return;
  try {
    await revertSetupApiV1OnboardingSetupsDraftIdRevertPost({
      path: { draft_id: row.draft_id },
      throwOnError: true,
    });
    await qc.invalidateQueries();
    toast.push({ title: t("setup.undone"), tone: "success" });
    setupDismissed.value = true;
  } catch (error) {
    toast.push({ title: apiError(error), tone: "danger" });
  }
}

function dismissSetupDone() {
  if (!recentSetup.value || !import.meta.client) return;
  localStorage.setItem(`kame.setupDone.${recentSetup.value.draft_id}`, "1");
  setupDismissed.value = true;
}

const openSetup = useQuery({
  queryKey: computed(() => ["today-open-setup", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data: row } = await getOpenSetupApiV1OnboardingSetupsGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return row;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const setupProvenance = useQuery({
  queryKey: computed(() => ["today-setup-provenance", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data: row } = await getProvenanceApiV1OnboardingSetupsProvenanceGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return row;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const setupDismissed = ref(false);
const recentSetup = computed(() => {
  const row = setupProvenance.data.value;
  if (!row) return null;
  const age = Date.now() - new Date(row.applied_at).getTime();
  return age <= 7 * 86_400_000 ? row : null;
});
watch(
  recentSetup,
  (row) => {
    if (!row || !import.meta.client) return;
    setupDismissed.value = localStorage.getItem(`kame.setupDone.${row.draft_id}`) === "1";
  },
  { immediate: true },
);
async function undoSetup() {
  const row = recentSetup.value;
  if (!row || !window.confirm(t("setup.undoConfirm"))) return;
  try {
    await revertSetupApiV1OnboardingSetupsDraftIdRevertPost({
      path: { draft_id: row.draft_id },
      throwOnError: true,
    });
    await qc.invalidateQueries();
    toast.push({ title: t("setup.undone"), tone: "success" });
    setupDismissed.value = true;
  } catch (error) {
    toast.push({ title: apiError(error), tone: "danger" });
  }
}
function dismissSetupDone() {
  if (!recentSetup.value || !import.meta.client) return;
  localStorage.setItem(`kame.setupDone.${recentSetup.value.draft_id}`, "1");
  setupDismissed.value = true;
}

const openSetup = useQuery({
  queryKey: computed(() => ["today-open-setup", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data } = await getOpenSetupApiV1OnboardingSetupsGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const setupProvenance = useQuery({
  queryKey: computed(() => ["today-provenance", ws.currentId, profileId.value]),
  queryFn: async () => {
    if (!profileId.value) return null;
    const { data } = await getProvenanceApiV1OnboardingSetupsProvenanceGet({
      query: { profile_id: profileId.value },
      throwOnError: true,
    });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId && profileId.value)),
});
const setupDoneDismissed = ref(false);
const undoing = ref(false);
const recentSetup = computed(() => {
  const row = setupProvenance.data.value;
  if (!row) return null;
  const age = Date.now() - new Date(row.applied_at).getTime();
  return age <= 7 * 86_400_000 ? row : null;
});
watch(
  recentSetup,
  (row) => {
    if (!row || !import.meta.client) return;
    setupDoneDismissed.value = localStorage.getItem(`kame.setupDone.${row.draft_id}`) === "1";
  },
  { immediate: true },
);
async function undoSetup() {
  const row = recentSetup.value;
  if (!row || !window.confirm(t("setup.undoConfirm"))) return;
  undoing.value = true;
  try {
    await revertSetupApiV1OnboardingSetupsDraftIdRevertPost({
      path: { draft_id: row.draft_id },
      throwOnError: true,
    });
    await qc.invalidateQueries();
    toast.push({ title: t("setup.undone"), tone: "success" });
    setupDoneDismissed.value = true;
  } catch (error) {
    toast.push({ title: apiError(error), tone: "danger" });
  } finally {
    undoing.value = false;
  }
}
function dismissSetupCard() {
  if (!recentSetup.value || !import.meta.client) return;
  localStorage.setItem(`kame.setupDone.${recentSetup.value.draft_id}`, "1");
  setupDoneDismissed.value = true;
}

const data = computed(() => home.data.value ?? null);
const greeting = computed(() => {
  const name = auth.user?.name?.split(" ")[0];
  return name ? t("today.hello", { name }) : t("today.helloNoName");
});
const firstTrack = computed(() => data.value?.tracks?.[0] ?? null);
const hasProfile = computed(() => Boolean(profileId.value));
const hasTracks = computed(() => Boolean(data.value?.tracks?.length));

const topJobs = useQuery({
  queryKey: computed(() => ["home-top-jobs", ws.currentId, firstTrack.value?.id]),
  queryFn: async () => {
    const { data: jobs } = await listJobsApiV1JobsGet({
      query: {
        track_id: firstTrack.value!.id,
        include_not_eligible: false,
        sort: "score",
        limit: 3,
      },
      throwOnError: true,
    });
    return (jobs ?? []) as BoardJobRead[];
  },
  enabled: computed(() => Boolean(ws.currentId && firstTrack.value?.id)),
});
const top = computed(() => topJobs.data.value ?? []);

const primary = computed(() => {
  if (!hasProfile.value) {
    return {
      title: t("today.addResumeTitle"),
      body: t("today.addResumeBody"),
      label: t("today.addResume"),
      to: "/start",
    };
  }
  if (!hasTracks.value) {
    return {
      title: t("today.startSearchTitle"),
      body: t("today.startSearchBody"),
      label: t("today.startSearch"),
      to: "/tracks",
    };
  }
  const track = firstTrack.value!;
  const matched = track.pipeline?.found ?? data.value?.kpis?.kpis?.matched ?? 0;
  if (matched === 0) {
    return {
      title: t("today.runFirstSearchTitle"),
      body: t("today.runFirstSearchBody", { track: track.name }),
      label: t("today.runSearch"),
      to: `/tracks/${track.id}`,
    };
  }
  return {
    title: t("today.reviewMatchesTitle"),
    body: t("today.reviewMatchesBody", { n: matched, track: track.name }),
    label: t("today.reviewMatches"),
    to: `/jobs?track=${track.id}`,
  };
});

/** The API can return the same draft twice when two runs finish together. */
const needs = computed(() => {
  const raw = data.value?.needs_you;
  if (!raw) return { count: 0, items: [] };
  const seen = new Set<string>();
  const items = (raw.items ?? []).filter((item) => {
    const key = `${item.href}:${item.title}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  return { count: Math.max(raw.count ?? 0, items.length), items };
});
const week = computed(() => data.value?.kpis?.kpis ?? {});

function detailText(detail: string): string {
  const risk = detail.match(/^risk\s+(red|yellow)$/i);
  if (risk) return risk[1]!.toLowerCase() === "red" ? t("jobs.highRisk") : t("jobs.caution");
  if (/^checkpoint:/i.test(detail)) return t("needsYou.checkpointDetail");
  return detail;
}

function hue(n: number | undefined): 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 {
  return Math.min(8, Math.max(1, n || 1)) as 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
}

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

function workModeLabel(mode: string | null | undefined): string {
  if (!mode) return "";
  return t(`tracks.mode_${mode}`);
}

function topReason(job: BoardJobRead): string {
  return (job.reasons || []).map(reasonText).find(Boolean) ?? "";
}

function trackLine(track: NonNullable<HomeBrief["tracks"]>[number]): string {
  const found = track.pipeline?.found ?? 0;
  const shortlisted = track.pipeline?.shortlisted ?? 0;
  return t("today.trackLine", { found, shortlisted }, found);
}
</script>

<template>
  <section class="mx-auto flex w-full max-w-[1040px] flex-col gap-6 md:gap-8">
    <VerifyEmailBanner />

    <header class="flex flex-col gap-2">
      <p class="text-xs font-semibold tracking-[0.12em] text-ink-400 uppercase">
        {{ ws.current?.name }}
      </p>
      <h1
        class="text-3xl leading-tight font-bold tracking-[-0.04em] text-ink-900 sm:text-4xl md:text-[length:var(--text-display)]"
      >
        {{ greeting }}
      </h1>
      <p class="max-w-2xl text-base leading-7 text-ink-600 sm:text-lg">
        {{ data?.headline || t("today.lede") }}
      </p>
    </header>

    <section
      v-if="openSetup.data.value"
      class="flex flex-col gap-3 rounded-xl border border-brand-200 bg-brand-50 p-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <h2 class="text-base font-bold text-ink-900">{{ t("setup.finishCardTitle") }}</h2>
        <p class="text-sm text-ink-600">{{ t("setup.finishCardBody") }}</p>
      </div>
      <FnButton tone="primary" @click="navigateTo(`/start?setup=${openSetup.data.value!.id}`)">
        {{ t("setup.finishCardAction") }}
      </FnButton>
    </section>

    <section
      v-else-if="recentDone"
      class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    >
      <div class="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 class="text-base font-bold text-ink-900">{{ t("setup.doneCardTitle") }}</h2>
          <p class="text-sm text-ink-600">{{ t("setup.doneCardBody") }}</p>
        </div>
        <FnButton tone="ghost" @click="dismissDone">{{ t("setup.donePanelDismiss") }}</FnButton>
      </div>
      <div class="flex flex-wrap gap-3 text-sm">
        <NuxtLink to="/profile" class="font-semibold text-brand-700 underline">{{
          t("setup.donePage.profile")
        }}</NuxtLink>
        <NuxtLink to="/profile/answers" class="font-semibold text-brand-700 underline">{{
          t("setup.donePage.answers")
        }}</NuxtLink>
        <NuxtLink to="/tracks" class="font-semibold text-brand-700 underline">{{
          t("setup.donePage.searches")
        }}</NuxtLink>
        <NuxtLink to="/studio" class="font-semibold text-brand-700 underline">{{
          t("setup.donePage.studio")
        }}</NuxtLink>
        <NuxtLink
          v-if="provenance.data.value?.created?.searches?.[0]"
          :to="`/tracks/${provenance.data.value.created.searches[0]}/improve`"
          class="font-semibold text-brand-700 underline"
          >{{ t("setup.donePage.improve") }}</NuxtLink
        >
      </div>
      <div class="flex flex-wrap gap-2">
        <FnButton tone="danger" @click="undoSetup">{{ t("setup.undo") }}</FnButton>
      </div>
    </section>

    <section
      v-if="setupOpen.data.value"
      class="flex flex-col gap-2 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    >
      <h2 class="text-lg font-bold text-ink-900">{{ t("setup.openCardTitle") }}</h2>
      <p class="text-sm text-ink-600">{{ t("setup.openCardBody") }}</p>
      <div>
        <FnButton tone="primary" as-child>
          <NuxtLink :to="`/start?setup=${setupOpen.data.value.id}`">
            {{ t("setup.openCardAction") }}
          </NuxtLink>
        </FnButton>
      </div>
    </section>

    <section
      v-else-if="recentSetup && !setupDismissed"
      class="flex flex-col gap-2 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    >
      <div class="flex flex-wrap items-center gap-2">
        <h2 class="text-lg font-bold text-ink-900">{{ t("setup.doneCardTitle") }}</h2>
        <FnChip>{{ t("setup.doneCardChip") }}</FnChip>
      </div>
      <p class="text-sm text-ink-600">{{ t("setup.doneCardBody") }}</p>
      <div class="flex flex-wrap gap-2">
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/profile">{{ t("setup.donePage.profile") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/profile/answers">{{ t("setup.donePage.answers") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/tracks">{{ t("setup.donePage.searches") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/studio">{{ t("setup.donePage.studio") }}</NuxtLink>
        </FnButton>
        <FnButton tone="ghost" :loading="undoBusy" @click="undoSetup">
          {{ t("setup.undo") }}
        </FnButton>
        <FnButton tone="ghost" @click="dismissSetupCard">{{
          t("setup.donePanelDismiss")
        }}</FnButton>
      </div>
    </section>

    <section
      v-if="setupOpen.data.value"
      class="flex flex-col gap-2 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    >
      <h2 class="text-lg font-bold text-ink-900">{{ t("setup.openCardTitle") }}</h2>
      <p class="text-sm text-ink-600">{{ t("setup.openCardBody") }}</p>
      <div>
        <FnButton tone="primary" as-child>
          <NuxtLink :to="`/start?setup=${setupOpen.data.value.id}`">
            {{ t("setup.openCardAction") }}
          </NuxtLink>
        </FnButton>
      </div>
    </section>

    <section
      v-else-if="recentSetup && !setupDismissed"
      class="flex flex-col gap-2 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    >
      <div class="flex flex-wrap items-center gap-2">
        <h2 class="text-lg font-bold text-ink-900">{{ t("setup.doneCardTitle") }}</h2>
        <FnChip>{{ t("setup.doneCardChip") }}</FnChip>
      </div>
      <p class="text-sm text-ink-600">{{ t("setup.doneCardBody") }}</p>
      <div class="flex flex-wrap gap-2">
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/profile">{{ t("setup.donePage.profile") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/profile/answers">{{ t("setup.donePage.answers") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/tracks">{{ t("setup.donePage.searches") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/studio">{{ t("setup.donePage.studio") }}</NuxtLink>
        </FnButton>
        <FnButton tone="ghost" :loading="undoBusy" @click="undoSetup">{{
          t("setup.undo")
        }}</FnButton>
        <FnButton tone="ghost" @click="dismissSetupCard">{{
          t("setup.donePanelDismiss")
        }}</FnButton>
      </div>
    </section>

    <section
      v-if="openSetup.data.value"
      class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    >
      <div class="min-w-0">
        <h2 class="text-lg font-bold text-ink-900">{{ t("setup.openCardTitle") }}</h2>
        <p class="text-sm text-ink-600">{{ t("setup.openCardBody") }}</p>
      </div>
      <FnButton tone="primary" as-child>
        <NuxtLink :to="`/start?setup=${openSetup.data.value.id}`">
          {{ t("setup.openCardAction") }}
        </NuxtLink>
      </FnButton>
    </section>

    <section
      v-else-if="recentSetup && !setupDismissed"
      class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    >
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-lg font-bold text-ink-900">{{ t("setup.donePanelTitle") }}</h2>
        <FnChip>{{ t("setup.doneChip") }}</FnChip>
      </div>
      <p class="text-sm text-ink-600">{{ t("setup.donePanelBody") }}</p>
      <div class="flex flex-wrap gap-2">
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/profile">{{ t("setup.donePage.profile") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/profile/answers">{{ t("setup.donePage.answers") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/tracks">{{ t("setup.donePage.searches") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/studio">{{ t("setup.donePage.studio") }}</NuxtLink>
        </FnButton>
        <FnButton tone="ghost" :loading="undoing" @click="undoSetup">{{
          t("setup.undo")
        }}</FnButton>
        <FnButton tone="ghost" @click="dismissSetup">{{ t("setup.donePanelDismiss") }}</FnButton>
      </div>
    </section>

    <section
      v-if="openSetup.data.value"
      class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    >
      <div class="min-w-0">
        <h2 class="text-lg font-bold text-ink-900">{{ t("setup.openCardTitle") }}</h2>
        <p class="text-sm text-ink-600">{{ t("setup.openCardBody") }}</p>
      </div>
      <FnButton tone="primary" as-child>
        <NuxtLink :to="`/start?setup=${openSetup.data.value.id}`">
          {{ t("setup.openCardAction") }}
        </NuxtLink>
      </FnButton>
    </section>

    <section
      v-else-if="recentSetup && !setupDismissed"
      class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    >
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-lg font-bold text-ink-900">{{ t("setup.doneCardTitle") }}</h2>
        <FnChip>{{ t("setup.doneChip") }}</FnChip>
      </div>
      <p class="text-sm text-ink-600">{{ t("setup.doneCardBody") }}</p>
      <div class="flex flex-wrap gap-2">
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/profile">{{ t("setup.donePage.profile") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/profile/answers">{{ t("setup.donePage.answers") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/tracks">{{ t("setup.donePage.searches") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/studio">{{ t("setup.donePage.studio") }}</NuxtLink>
        </FnButton>
        <FnButton tone="ghost" :loading="undoing" @click="undoSetup">{{
          t("setup.undo")
        }}</FnButton>
        <FnButton tone="ghost" @click="dismissSetupCard">{{ t("setup.gotIt") }}</FnButton>
      </div>
    </section>

    <div v-if="home.isPending.value" class="flex flex-col gap-4">
      <FnSkeleton class="h-40 w-full" />
      <FnSkeleton class="h-24 w-full" />
    </div>

    <template v-else-if="data">
      <section
        class="rounded-2xl border border-brand-100 bg-brand-50 p-5 sm:p-7 md:p-9"
        aria-labelledby="next-step-title"
      >
        <div class="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div class="max-w-xl">
            <p class="text-xs font-bold tracking-[0.12em] text-brand-700 uppercase">
              {{ t("today.nextStep") }}
            </p>
            <h2
              id="next-step-title"
              class="mt-2 text-2xl font-bold tracking-[-0.03em] text-ink-900 sm:text-3xl"
            >
              {{ primary.title }}
            </h2>
            <p class="mt-2 text-base leading-7 text-ink-600">{{ primary.body }}</p>
          </div>
          <FnButton tone="primary" class="shrink-0 max-md:w-full" @click="navigateTo(primary.to)">{{
            primary.label
          }}</FnButton>
        </div>
      </section>

      <section v-if="needs.count" class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold tracking-wide text-ink-600 uppercase">
            {{ t("shell.needsYou") }}
          </h2>
          <NuxtLink to="/needs-you" class="text-sm font-semibold text-brand-700 underline">{{
            t("today.viewAll")
          }}</NuxtLink>
        </div>
        <ul class="divide-y divide-rule border-y border-rule">
          <li v-for="(item, i) in needs.items.slice(0, 4)" :key="i">
            <NuxtLink
              :to="item.href"
              class="flex min-h-11 items-start gap-3 py-3 text-sm hover:bg-paper-1"
            >
              <span class="mt-1 size-2 shrink-0 rounded-full bg-brand-700" aria-hidden="true" />
              <span class="flex min-w-0 flex-col gap-0.5">
                <span class="font-medium text-ink-900">{{ item.title }}</span>
                <span class="text-ink-600">{{ detailText(item.detail) }}</span>
              </span>
              <NavIcon name="ph:caret-right" :size="16" class="mt-1 ml-auto text-ink-400" />
            </NuxtLink>
          </li>
        </ul>
      </section>

      <section
        v-if="top.length"
        class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)] sm:p-5"
      >
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold tracking-wide text-ink-600 uppercase">
            {{ t("today.topMatches") }}
          </h2>
          <NuxtLink
            :to="`/jobs?track=${firstTrack?.id}`"
            class="text-sm font-semibold text-brand-700 underline"
            >{{ t("today.viewAll") }}</NuxtLink
          >
        </div>
        <ul class="divide-y divide-rule border-y border-rule">
          <li v-for="job in top" :key="job.id">
            <NuxtLink
              :to="`/jobs?track=${firstTrack?.id}&job=${job.id}`"
              class="flex items-start gap-3 py-4 hover:bg-paper-1"
            >
              <span
                class="mt-0.5 grid min-w-9 place-items-center rounded-md bg-paper-2 px-1.5 py-0.5 text-sm font-bold tabular-nums text-brand-700"
                >{{ job.score != null ? Math.round(job.score) : "-" }}</span
              >
              <span class="min-w-0 flex-1">
                <span class="block font-medium text-ink-900">{{ job.title }}</span>
                <span class="block text-sm text-ink-600">
                  {{ job.company_name }}
                  <template v-if="job.work_mode"> · {{ workModeLabel(job.work_mode) }}</template>
                </span>
                <span v-if="topReason(job)" class="mt-1 block text-sm text-ink-400">{{
                  topReason(job)
                }}</span>
              </span>
              <FnRiskSeal
                v-if="job.risk_level === 'yellow' || job.risk_level === 'red'"
                :level="sealLevel(job.risk_level)"
                :label="sealLabel(job.risk_level)"
              />
            </NuxtLink>
          </li>
        </ul>
      </section>

      <section v-if="data.tracks?.length" class="flex flex-col gap-3">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold tracking-wide text-ink-600 uppercase">
            {{ t("today.yourSearches") }}
          </h2>
          <NuxtLink to="/tracks" class="text-sm font-semibold text-brand-700 underline">{{
            t("today.viewAllSearches")
          }}</NuxtLink>
        </div>
        <ul class="grid gap-3 sm:grid-cols-2">
          <li v-for="track in data.tracks" :key="track.id">
            <NuxtLink
              :to="`/jobs?track=${track.id}`"
              class="flex h-full flex-col gap-2 rounded-xl border border-rule bg-paper-0 p-4 transition-colors hover:border-brand-200 hover:bg-brand-50"
            >
              <FnFolderTab :hue="hue(track.color_hue)">{{ track.name }}</FnFolderTab>
              <p class="text-sm text-ink-600">{{ trackLine(track) }}</p>
              <span class="mt-auto text-sm font-semibold text-brand-700">{{
                t("tracks.viewMatches")
              }}</span>
            </NuxtLink>
          </li>
        </ul>
      </section>

      <FnEmptyState
        v-if="!top.length && !data.tracks?.length"
        :title="t('today.startSearchTitle')"
        :body="t('today.startSearchBody')"
      >
        <FnButton as-child tone="quiet">
          <NuxtLink to="/start">{{ t("today.startSearch") }}</NuxtLink>
        </FnButton>
      </FnEmptyState>

      <OnboardingChecklist v-if="data.empty" />

      <details class="border-t border-rule pt-4">
        <summary class="min-h-11 cursor-pointer text-sm font-semibold text-ink-600">
          {{ t("today.thisWeek") }}
        </summary>
        <dl class="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div class="rounded-lg bg-paper-2 px-3 py-2">
            <dt class="text-xs text-ink-600">{{ t("today.applicationsSubmitted") }}</dt>
            <dd class="text-lg font-bold tabular-nums">{{ week.submitted ?? 0 }}</dd>
          </div>
          <div class="rounded-lg bg-paper-2 px-3 py-2">
            <dt class="text-xs text-ink-600">{{ t("today.responseRateLabel") }}</dt>
            <dd class="text-lg font-bold tabular-nums">
              {{ Math.round((week.response_rate ?? 0) * 100) }}%
            </dd>
          </div>
          <div class="rounded-lg bg-paper-2 px-3 py-2">
            <dt class="text-xs text-ink-600">{{ t("today.interviewsLabel") }}</dt>
            <dd class="text-lg font-bold tabular-nums">{{ week.interviews ?? 0 }}</dd>
          </div>
          <div class="rounded-lg bg-paper-2 px-3 py-2">
            <dt class="text-xs text-ink-600">{{ t("today.matchesLabel") }}</dt>
            <dd class="text-lg font-bold tabular-nums">{{ week.matched ?? 0 }}</dd>
          </div>
        </dl>
      </details>
    </template>
  </section>
</template>
