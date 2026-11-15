<script setup lang="ts">
import { needsYouApiV1NeedsYouGet } from "@kame/api-client";
import { FnButton, FnEmptyState, FnSkeleton } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

type Item = {
  kind: string;
  title: string;
  detail: string;
  href: string;
  created_at?: string | null;
};

const { t } = useI18n();
const ws = useWorkspaceStore();
const fmt = useFormat();

const query = useQuery({
  queryKey: computed(() => ["needs-you", ws.currentId]),
  queryFn: async () => {
    const { data } = await needsYouApiV1NeedsYouGet({ throwOnError: true });
    return (data?.items ?? []) as Item[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
  refetchInterval: 20_000,
});

/** The API can return the same draft twice when two runs finish together. */
const items = computed(() => {
  const seen = new Set<string>();
  return (query.data.value ?? []).filter((item) => {
    const key = `${item.kind}:${item.href}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
});

const LABELS: Record<string, string> = {
  apply_checkpoint: "application",
  tailoring_review: "draft",
  risk_review: "safety",
  proposal: "reply",
};

function label(kind: string): string {
  return LABELS[kind] ?? "decision";
}

function detailText(detail: string): string {
  const risk = detail.match(/^risk\s+(red|yellow)$/i);
  if (risk) return risk[1]!.toLowerCase() === "red" ? t("jobs.highRisk") : t("jobs.caution");
  if (/^checkpoint:/i.test(detail)) return t("needsYou.checkpointDetail");
  return detail;
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-6">
    <PageHeader :title="t('needsYou.title')" :lede="t('needsYou.intro')" />

    <div v-if="query.isPending.value" class="flex flex-col gap-3">
      <FnSkeleton class="h-20 w-full" />
      <FnSkeleton class="h-20 w-full" />
    </div>

    <FnEmptyState
      v-else-if="!items.length"
      :title="t('needsYou.empty')"
      :body="t('notifications.empty')"
    >
      <FnButton as-child tone="quiet">
        <NuxtLink to="/jobs">{{ t("nav.jobs") }}</NuxtLink>
      </FnButton>
    </FnEmptyState>

    <ul v-else class="flex flex-col gap-2">
      <li v-for="item in items" :key="`${item.kind}-${item.href}`">
        <NuxtLink
          :to="item.href"
          class="flex min-h-16 items-start gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)] transition-colors hover:border-brand-200 hover:bg-brand-50"
        >
          <span
            class="mt-0.5 rounded-full bg-brand-100 px-2 py-0.5 text-[0.6875rem] font-semibold text-brand-700"
            >{{ label(item.kind) }}</span
          >
          <span class="min-w-0 flex-1">
            <span class="block font-semibold text-ink-900">{{ item.title }}</span>
            <span class="block text-sm text-ink-600">{{ detailText(item.detail) }}</span>
          </span>
          <span v-if="item.created_at" class="hidden shrink-0 text-xs text-ink-400 sm:block">{{
            fmt.dateTime(item.created_at)
          }}</span>
          <NavIcon name="ph:caret-right" :size="16" class="mt-1 shrink-0 text-ink-400" />
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
