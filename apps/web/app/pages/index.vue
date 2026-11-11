<script setup lang="ts">
import { homeApiV1HomeGet, listJobsApiV1JobsGet, type BoardJobRead } from "@kame/api-client";
import { FnButton, FnFolderTab, FnRiskSeal, FnSkeleton } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
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
const auth = useAuthStore();
const ws = useWorkspaceStore();
const { profileId } = useActiveProfile();

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
      to: "/profile/onboarding",
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

const needs = computed(() => data.value?.needs_you);
const week = computed(() => data.value?.kpis?.kpis ?? {});

function hue(n: number | undefined): 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 {
  return Math.min(8, Math.max(1, n || 1)) as 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
}

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
  return `${found} matches · ${shortlisted} shortlisted`;
}
</script>

<template>
  <section class="mx-auto flex w-full max-w-[1040px] flex-col gap-8">
    <VerifyEmailBanner />

    <header class="flex flex-col gap-2">
      <p class="text-xs font-medium tracking-[0.14em] text-ink-400 uppercase">
        {{ ws.current?.name }}
      </p>
      <h1 class="font-serif text-[length:var(--text-display)] leading-tight font-semibold">
        {{ greeting }}
      </h1>
      <p class="max-w-2xl font-serif text-lg text-ink-600">
        {{ data?.headline || t("today.lede") }}
      </p>
    </header>

    <div v-if="home.isPending.value" class="flex flex-col gap-4">
      <FnSkeleton class="h-40 w-full" />
      <FnSkeleton class="h-24 w-full" />
    </div>

    <template v-else-if="data">
      <section
        class="relative overflow-hidden rounded-lg border border-rule bg-paper-1 p-6 md:p-8"
        aria-labelledby="next-step-title"
      >
        <ContourBackdrop />
        <div class="relative flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div class="max-w-xl">
            <p class="text-xs font-medium tracking-[0.14em] text-ink-400 uppercase">
              {{ t("today.nextStep") }}
            </p>
            <h2 id="next-step-title" class="mt-2 font-serif text-2xl font-semibold md:text-3xl">
              {{ primary.title }}
            </h2>
            <p class="mt-2 text-ink-600">{{ primary.body }}</p>
          </div>
          <FnButton tone="primary" class="shrink-0" @click="navigateTo(primary.to)">{{
            primary.label
          }}</FnButton>
        </div>
      </section>

      <section v-if="needs?.count" class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("shell.needsYou") }}
          </h2>
          <NuxtLink to="/notifications" class="text-sm text-persimmon-700 underline">{{
            t("today.viewAll")
          }}</NuxtLink>
        </div>
        <ul class="divide-y divide-rule border-y border-rule">
          <li v-for="(item, i) in needs.items.slice(0, 4)" :key="i">
            <NuxtLink
              :to="item.href"
              class="flex min-h-11 flex-col gap-0.5 py-3 text-sm hover:bg-paper-1"
            >
              <span class="font-medium text-ink-900">{{ item.title }}</span>
              <span class="text-ink-600">{{ item.detail }}</span>
            </NuxtLink>
          </li>
        </ul>
      </section>

      <section v-if="top.length" class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("today.topMatches") }}
          </h2>
          <NuxtLink
            :to="`/jobs?track=${firstTrack?.id}`"
            class="text-sm text-persimmon-700 underline"
            >{{ t("today.viewAll") }}</NuxtLink
          >
        </div>
        <ul class="divide-y divide-rule border-y border-rule">
          <li v-for="job in top" :key="job.id">
            <NuxtLink
              :to="`/jobs?track=${firstTrack?.id}&job=${job.id}`"
              class="flex items-start gap-3 py-4 hover:bg-paper-1"
            >
              <span class="mt-0.5 font-mono text-sm tabular-nums text-persimmon-700">{{
                job.score != null ? Math.round(job.score) : "-"
              }}</span>
              <span class="min-w-0 flex-1">
                <span class="block font-medium text-ink-900">{{ job.title }}</span>
                <span class="block text-sm text-ink-600">
                  {{ job.company_name }}
                  <template v-if="job.work_mode"> · {{ workModeLabel(job.work_mode) }}</template>
                </span>
                <span v-if="topReason(job)" class="mt-1 block text-sm text-ink-500">{{
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
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("today.yourSearches") }}
          </h2>
          <NuxtLink to="/tracks" class="text-sm text-persimmon-700 underline">{{
            t("today.viewAllSearches")
          }}</NuxtLink>
        </div>
        <ul class="grid gap-3 md:grid-cols-2">
          <li v-for="track in data.tracks" :key="track.id">
            <NuxtLink
              :to="`/jobs?track=${track.id}`"
              class="flex h-full flex-col gap-2 rounded-lg border border-rule bg-paper-1 p-4 hover:bg-paper-2"
            >
              <FnFolderTab :hue="hue(track.color_hue)">{{ track.name }}</FnFolderTab>
              <p class="text-sm text-ink-600">{{ trackLine(track) }}</p>
              <span class="mt-auto text-sm font-medium text-persimmon-700">{{
                t("tracks.viewMatches")
              }}</span>
            </NuxtLink>
          </li>
        </ul>
      </section>

      <OnboardingChecklist v-if="data.empty" />

      <details class="border-t border-rule pt-4">
        <summary class="cursor-pointer text-sm text-ink-600">{{ t("today.thisWeek") }}</summary>
        <p class="mt-2 text-sm text-ink-600">
          {{ week.submitted ?? 0 }} {{ t("today.submitted") }} ·
          {{ Math.round((week.response_rate ?? 0) * 100) }}% {{ t("today.responseRate") }} ·
          {{ week.interviews ?? 0 }} {{ t("today.interviews") }} · {{ week.matched ?? 0 }}
          {{ t("today.matched") }}
        </p>
      </details>
    </template>
  </section>
</template>
