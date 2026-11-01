<script setup lang="ts">
import { homeApiV1HomeGet } from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
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
    autonomy?: string;
    pipeline?: Record<string, number>;
  }[];
  reminders?: {
    id: string;
    application_id: string;
    job_title?: string;
    company_name?: string;
    due_at?: string;
  }[];
  upcoming_runs?: { track_name?: string; next_run_at?: string; preview?: string }[];
  activity?: { id: string; action?: string; at?: string }[];
};

const { t } = useI18n();
const auth = useAuthStore();
const ws = useWorkspaceStore();
const fmt = useFormat();
const period = ref<"today" | "week" | "total">("week");

const home = useQuery({
  queryKey: computed(() => ["home", ws.currentId, period.value]),
  queryFn: async () => {
    const { data } = await homeApiV1HomeGet({
      query: { period: period.value },
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
</script>

<template>
  <section class="mx-auto flex max-w-[960px] flex-col gap-8">
    <VerifyEmailBanner />
    <header class="relative overflow-hidden rounded-md border border-rule bg-paper-1 px-6 py-8">
      <ContourBackdrop />
      <p class="relative text-sm text-ink-600">{{ ws.current?.name }}</p>
      <h1
        class="relative mt-1 font-serif text-[length:var(--text-display)] leading-tight font-semibold"
      >
        {{ greeting }}
      </h1>
      <p v-if="data?.headline" class="relative mt-2 max-w-prose font-serif text-lg text-ink-600">
        {{ data.headline }}
      </p>
      <p v-else class="relative mt-2 max-w-prose font-serif text-lg text-ink-600">
        {{ t("today.lede") }}
      </p>
    </header>

    <div v-if="home.isPending.value"><FnSkeleton class="h-32 w-full" /></div>
    <template v-else-if="data">
      <OnboardingChecklist v-if="data.empty" />

      <section v-if="data.needs_you?.count" class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("shell.needsYou") }}
          </h2>
          <NuxtLink to="/notifications" class="text-sm text-persimmon-700 underline">{{
            t("today.viewAll")
          }}</NuxtLink>
        </div>
        <ul class="divide-y divide-rule border-y border-rule">
          <li v-for="(item, i) in data.needs_you.items.slice(0, 5)" :key="i">
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

      <section class="flex flex-col gap-3">
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("today.numbers") }}
          </h2>
          <select
            v-model="period"
            class="min-h-11 border border-rule bg-paper-0 px-2 text-sm"
            :aria-label="t('today.period')"
          >
            <option value="today">{{ t("today.periodToday") }}</option>
            <option value="week">{{ t("today.periodWeek") }}</option>
            <option value="total">{{ t("today.periodTotal") }}</option>
          </select>
        </div>
        <div class="flex flex-wrap gap-x-6 gap-y-2 font-mono text-sm">
          <NuxtLink to="/applications" class="text-ink-900"
            >{{ data.kpis?.kpis?.submitted ?? 0 }}
            <span class="text-ink-600">{{ t("today.submitted") }}</span></NuxtLink
          >
          <span
            >{{ Math.round((data.kpis?.kpis?.response_rate ?? 0) * 100) }}%
            <span class="text-ink-600">{{ t("today.responseRate") }}</span></span
          >
          <span
            >{{ data.kpis?.kpis?.interviews ?? 0 }}
            <span class="text-ink-600">{{ t("today.interviews") }}</span></span
          >
          <NuxtLink to="/jobs" class="text-ink-900"
            >{{ data.kpis?.kpis?.matched ?? 0 }}
            <span class="text-ink-600">{{ t("today.matched") }}</span></NuxtLink
          >
        </div>
      </section>

      <section v-if="data.tracks?.length" class="flex flex-col gap-2">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("nav.tracks") }}
        </h2>
        <ul class="divide-y divide-rule border-y border-rule">
          <li
            v-for="tr in data.tracks"
            :key="tr.id"
            class="flex flex-col gap-2 py-3 md:flex-row md:items-center md:justify-between"
          >
            <div class="min-w-0">
              <NuxtLink
                :to="`/tracks/${tr.id}`"
                class="font-medium text-ink-900 underline-offset-2 hover:underline"
                >{{ tr.name }}</NuxtLink
              >
              <p class="mt-1 font-mono text-[0.6875rem] text-ink-600">
                {{ tr.pipeline?.found ?? 0 }} → {{ tr.pipeline?.shortlisted ?? 0 }} →
                {{ tr.pipeline?.tailored ?? 0 }} → {{ tr.pipeline?.applied ?? 0 }} →
                {{ tr.pipeline?.responded ?? 0 }} → {{ tr.pipeline?.interview ?? 0 }}
              </p>
            </div>
            <div class="flex items-center gap-2">
              <FnChip>{{ tr.autonomy }}</FnChip>
              <FnButton
                tone="quiet"
                size="sm"
                :to="`/tracks/${tr.id}`"
                @click="navigateTo(`/tracks/${tr.id}`)"
                >{{ t("tracks.runNow") }}</FnButton
              >
            </div>
          </li>
        </ul>
      </section>

      <section
        v-if="data.reminders?.length || data.upcoming_runs?.length"
        class="grid gap-6 md:grid-cols-2"
      >
        <div v-if="data.reminders?.length" class="flex flex-col gap-2">
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("today.reminders") }}
          </h2>
          <ul class="divide-y divide-rule border-y border-rule text-sm">
            <li v-for="r in data.reminders" :key="r.id" class="py-2">
              <NuxtLink :to="`/applications/${r.application_id}`" class="font-medium text-ink-900"
                >{{ r.job_title }} · {{ r.company_name }}</NuxtLink
              >
              <p class="font-mono text-[0.6875rem] text-ink-600">
                {{ r.due_at ? fmt.dateTime(r.due_at) : "" }}
              </p>
            </li>
          </ul>
        </div>
        <div v-if="data.upcoming_runs?.length" class="flex flex-col gap-2">
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("today.upcomingRuns") }}
          </h2>
          <ul class="divide-y divide-rule border-y border-rule text-sm">
            <li v-for="(u, i) in data.upcoming_runs" :key="i" class="py-2">
              <span class="font-medium text-ink-900">{{ u.track_name }}</span>
              <p class="font-mono text-[0.6875rem] text-ink-600">
                {{ u.next_run_at ? fmt.dateTime(u.next_run_at) : "" }} · {{ u.preview }}
              </p>
            </li>
          </ul>
        </div>
      </section>

      <section v-if="data.activity?.length" class="flex flex-col gap-2">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("today.activity") }}
        </h2>
        <ul class="divide-y divide-rule border-y border-rule text-sm">
          <li
            v-for="a in data.activity.slice(0, 8)"
            :key="a.id"
            class="flex justify-between gap-3 py-2"
          >
            <span class="text-ink-900">{{ a.action }}</span>
            <span class="shrink-0 font-mono text-[0.6875rem] text-ink-600">{{
              a.at ? fmt.dateTime(a.at) : ""
            }}</span>
          </li>
        </ul>
      </section>
    </template>
  </section>
</template>
