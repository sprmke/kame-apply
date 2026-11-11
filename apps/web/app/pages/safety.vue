<script setup lang="ts">
import {
  checkThisApiV1SafetyCheckThisPost,
  flaggedJobsApiV1SafetyFlaggedGet,
  riskDecisionApiV1JobsJobIdRiskDecisionPost,
  type CheckThisRead,
  type FlaggedJobRead,
} from "@kame/api-client";
import { FnButton, FnRiskSeal, FnSkeleton, FnTextarea, useToast } from "@kame/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();

const tab = ref<"flagged" | "check">("flagged");
const checkInput = ref("");
const checkResult = ref<CheckThisRead | null>(null);
const confirmJobId = ref<string | null>(null);

function sealLevel(level: string): "clear" | "caution" | "danger" {
  if (level === "red") return "danger";
  if (level === "yellow") return "caution";
  return "clear";
}

function sealLabel(level: string): string {
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

function reasonText(r: unknown): string {
  if (typeof r === "string") return r;
  if (r && typeof r === "object") {
    const o = r as { evidence?: string; signal?: string };
    return o.evidence || o.signal || "";
  }
  return "";
}

function visibleReasons(reasons: unknown[] | undefined): unknown[] {
  return (reasons || []).filter((r) => {
    const text = reasonText(r).toLowerCase();
    const parts = text
      .split(/[,·|]/)
      .map((part) => part.trim())
      .filter(Boolean);
    return parts.length > 0 && !parts.every((part) => STOP_REASONS.has(part));
  });
}

const flagged = useQuery({
  queryKey: computed(() => ["safety-flagged", ws.currentId]),
  queryFn: async () => {
    const { data } = await flaggedJobsApiV1SafetyFlaggedGet({ throwOnError: true });
    return (data ?? []) as FlaggedJobRead[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const checkMut = useMutation({
  mutationFn: async () => {
    const text = checkInput.value.trim();
    const looksUrl = /^https?:\/\//i.test(text);
    const { data } = await checkThisApiV1SafetyCheckThisPost({
      body: looksUrl ? { url: text } : { text },
      throwOnError: true,
    });
    return data as CheckThisRead;
  },
  onSuccess: (data) => {
    checkResult.value = data;
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

async function decide(jobId: string, decision: "continue" | "skip" | "reported" | "not_scam") {
  try {
    await riskDecisionApiV1JobsJobIdRiskDecisionPost({
      path: { job_id: jobId },
      body: {
        decision,
        confirm_risk: decision === "continue",
      },
      throwOnError: true,
    });
    confirmJobId.value = null;
    await qc.invalidateQueries({ queryKey: ["safety-flagged", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-8 p-4 md:p-6">
    <header class="flex flex-wrap items-center gap-2">
      <h1 class="text-3xl font-bold tracking-[-0.03em] text-ink-900">{{ $t("nav.safety") }}</h1>
      <div class="ml-auto flex gap-1 rounded-lg bg-paper-2 p-1">
        <button
          type="button"
          class="min-h-11 rounded-md px-4 text-sm font-semibold transition-colors"
          :class="
            tab === 'flagged'
              ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
              : 'text-ink-600 hover:text-ink-900'
          "
          @click="tab = 'flagged'"
        >
          Flagged
        </button>
        <button
          type="button"
          class="min-h-11 rounded-md px-4 text-sm font-semibold transition-colors"
          :class="
            tab === 'check'
              ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
              : 'text-ink-600 hover:text-ink-900'
          "
          @click="tab = 'check'"
        >
          Check this
        </button>
      </div>
    </header>

    <section v-if="tab === 'flagged'">
      <div v-if="flagged.isPending.value" class="space-y-2">
        <FnSkeleton class="h-12" />
        <FnSkeleton class="h-12" />
      </div>
      <p
        v-else-if="!(flagged.data.value || []).length"
        class="rounded-xl border border-dashed border-rule bg-paper-1 p-6 text-sm text-ink-600"
      >
        No flagged jobs
      </p>
      <ul
        v-else
        class="divide-y divide-rule overflow-hidden rounded-xl border border-rule bg-paper-1 shadow-[var(--shadow-card)]"
      >
        <li
          v-for="row in flagged.data.value"
          :key="String(row.job_id)"
          class="flex flex-col gap-3 p-5 sm:flex-row sm:items-start"
        >
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <FnRiskSeal :level="sealLevel(row.level)" :label="sealLabel(row.level)" />
              <span class="line-clamp-2 font-medium text-ink-900">{{ row.title }}</span>
            </div>
            <p class="mt-0.5 text-sm text-ink-400">{{ row.company_name }}</p>
            <ul class="mt-2 space-y-1 text-sm text-ink-600">
              <li v-for="(r, i) in visibleReasons(row.reasons).slice(0, 4)" :key="i">
                {{ reasonText(r) }}
              </li>
            </ul>
            <p v-if="row.override" class="mt-1 text-xs text-ink-400">
              Decision: {{ row.override }}
            </p>
          </div>
          <div class="flex flex-wrap gap-1">
            <FnButton size="sm" tone="quiet" @click="decide(String(row.job_id), 'skip')"
              >Skip</FnButton
            >
            <FnButton size="sm" tone="quiet" @click="decide(String(row.job_id), 'reported')"
              >Report</FnButton
            >
            <FnButton size="sm" tone="quiet" @click="decide(String(row.job_id), 'not_scam')"
              >Not a scam</FnButton
            >
            <FnButton
              v-if="row.level === 'red'"
              size="sm"
              tone="quiet"
              @click="confirmJobId = String(row.job_id)"
              >Continue</FnButton
            >
            <FnButton v-else size="sm" tone="quiet" @click="decide(String(row.job_id), 'continue')"
              >Continue</FnButton
            >
          </div>
          <div
            v-if="confirmJobId === String(row.job_id)"
            class="w-full rounded-xl border border-oxblood-600 bg-paper-2 p-4 text-sm text-ink-900"
          >
            <p>This job is marked high risk. Continue anyway?</p>
            <div class="mt-2 flex gap-2">
              <FnButton size="sm" tone="danger" @click="decide(String(row.job_id), 'continue')"
                >Confirm</FnButton
              >
              <FnButton size="sm" tone="ghost" @click="confirmJobId = null">Cancel</FnButton>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <section
      v-else
      class="space-y-4 rounded-xl border border-rule bg-paper-1 p-6 shadow-[var(--shadow-card)]"
    >
      <FnTextarea v-model="checkInput" :rows="6" class="w-full" aria-label="Message or URL" />
      <FnButton
        size="sm"
        tone="primary"
        :disabled="!checkInput.trim() || checkMut.isPending.value"
        @click="checkMut.mutate()"
        >Check</FnButton
      >
      <div v-if="checkResult" class="space-y-3 rounded-xl border border-rule bg-paper-0 p-5">
        <FnRiskSeal :level="sealLevel(checkResult.level)" :label="sealLabel(checkResult.level)" />
        <ul class="space-y-1 text-sm text-ink-900">
          <li v-for="(r, i) in visibleReasons(checkResult.reasons).slice(0, 6)" :key="i">
            {{ reasonText(r) }}
          </li>
        </ul>
        <p class="text-sm text-ink-600">{{ checkResult.advice }}</p>
      </div>
    </section>
  </div>
</template>
