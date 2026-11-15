<script setup lang="ts">
import {
  acceptTailorApiV1TailorRunsRunIdAcceptPost,
  decideTailorChangeApiV1TailorRunsRunIdChangesChangeIdPost,
  getTailorRunApiV1TailorRunsRunIdGet,
  startTailorApiV1TrackJobsTrackJobIdTailorPost,
  type TailorRunRead,
} from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton, FnStepper, useToast } from "@kame/ui";
import { useMutation } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const route = useRoute();
const router = useRouter();
const { waiting: inboxWaiting } = useAgentInboxStatus();

const trackJobId = computed(() => String(route.params.trackJobId || ""));
const tab = ref<"preview" | "letter">("preview");
const step = ref("match");
const run = ref<TailorRunRead | null>(null);

const startMut = useMutation({
  mutationFn: async () => {
    const { data } = await startTailorApiV1TrackJobsTrackJobIdTailorPost({
      path: { track_job_id: trackJobId.value },
      body: { include_cover_letter: true },
      throwOnError: true,
    });
    return data as TailorRunRead;
  },
  onSuccess: async (data) => {
    run.value = data;
    // Deployed runs are queued and finish in a worker; poll until it stops changing.
    if (data && (data.status === "queued" || data.status === "running")) {
      for (let i = 0; i < 60; i += 1) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        try {
          const { data: latest } = await getTailorRunApiV1TailorRunsRunIdGet({
            path: { run_id: String(data.id) },
            throwOnError: true,
          });
          run.value = latest as TailorRunRead;
          if (latest && latest.status !== "queued" && latest.status !== "running") break;
        } catch {
          break;
        }
      }
    }
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const changeMut = useMutation({
  mutationFn: async ({
    changeId,
    status,
  }: {
    changeId: string;
    status: "accepted" | "rejected";
  }) => {
    if (!run.value?.id) throw new Error("No run");
    const { data } = await decideTailorChangeApiV1TailorRunsRunIdChangesChangeIdPost({
      path: { run_id: String(run.value.id), change_id: changeId },
      body: { status },
      throwOnError: true,
    });
    return data as TailorRunRead;
  },
  onSuccess: (data) => {
    run.value = data;
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

function decideChange(changeId: string | undefined, status: "accepted" | "rejected") {
  if (changeId) changeMut.mutate({ changeId, status });
}

const acceptMut = useMutation({
  mutationFn: async () => {
    if (!run.value?.id) throw new Error("No run");
    const { data } = await acceptTailorApiV1TailorRunsRunIdAcceptPost({
      path: { run_id: String(run.value.id) },
      body: { include_cover_letter: true, method: "manual" },
      throwOnError: true,
    });
    return data;
  },
  onSuccess: () => {
    toast.push({ title: "Application ready" });
    router.push("/jobs");
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

watch(
  () => [trackJobId.value, ws.currentId] as const,
  ([id, wsId]) => {
    if (id && wsId) startMut.mutate();
  },
  { immediate: true },
);

function verdictGlyph(v: string): string {
  if (v === "met") return "●";
  if (v === "partial") return "◐";
  if (v === "not_met") return "✕";
  return "○";
}

const beforeGrade = computed(
  () => (run.value?.lens_before as { grade?: string } | undefined)?.grade || "-",
);
const afterGrade = computed(
  () => (run.value?.lens_after as { grade?: string } | undefined)?.grade || "-",
);

const ledgerRows = computed(() => {
  const after =
    ((run.value?.lens_after as { qualifications?: unknown[] }) || {}).qualifications || [];
  const before =
    ((run.value?.lens_before as { qualifications?: unknown[] }) || {}).qualifications || [];
  const beforeById = new Map(
    before.map((r) => {
      const row = r as { qual_id?: string; verdict?: string };
      return [String(row.qual_id), row.verdict || ""];
    }),
  );
  return after.map((r) => {
    const row = r as {
      qual_id?: string;
      kind?: string;
      text?: string;
      verdict?: string;
      evidence_quote?: string;
    };
    return { ...row, before: beforeById.get(String(row.qual_id)) || "" };
  });
});

const gaps = computed(() => (run.value?.gaps as Array<{ text?: string; message?: string }>) || []);
const knockouts = computed(
  () => (run.value?.knockouts as Array<{ reason?: string; quote?: string }>) || [],
);
const changes = computed(
  () =>
    (run.value?.proposed_changes as Array<{
      change_id?: string;
      status?: string;
      op?: string;
      before?: string;
      after?: string;
      reason?: string;
    }>) || [],
);

const previewText = computed(() => {
  const c = run.value?.draft_content as Record<string, unknown> | undefined;
  if (!c) return "";
  const contact = (c.contact || {}) as { full_name?: string };
  const summary = (c.summary as { text?: string } | undefined)?.text || "";
  const sections =
    (c.sections as Array<{
      heading?: string;
      lines?: { text: string }[];
      items?: { title?: string; subtitle?: string; lines?: { text: string }[] }[];
    }>) || [];
  const parts = [contact.full_name || "", summary];
  for (const sec of sections) {
    parts.push("", (sec.heading || "").toUpperCase());
    for (const line of sec.lines || []) parts.push(`• ${line.text}`);
    for (const item of sec.items || []) {
      parts.push([item.title, item.subtitle].filter(Boolean).join(", "));
      for (const line of item.lines || []) parts.push(`• ${line.text}`);
    }
  }
  return parts.filter(Boolean).join("\n");
});

const letter = computed(
  () => run.value?.cover_letter as { content?: string; word_count?: number } | null,
);
</script>

<template>
  <div class="mx-auto flex w-full max-w-4xl flex-col gap-5">
    <PageHeader :title="t('jobs.tailorResume')" :lede="t('tailor.lede')">
      <template #actions>
        <FnButton size="sm" tone="ghost" @click="router.push('/jobs')">{{
          t("start.back")
        }}</FnButton>
        <FnButton
          size="sm"
          tone="primary"
          :disabled="!run || acceptMut.isPending.value || run.status !== 'ready'"
          @click="acceptMut.mutate()"
        >
          {{ t("tailor.acceptAttach") }}
        </FnButton>
      </template>
    </PageHeader>

    <FnStepper
      v-model="step"
      :steps="[
        { key: 'match', label: t('tailor.stepMatch') },
        { key: 'edits', label: t('tailor.stepEdits') },
        { key: 'check', label: t('tailor.stepCheck') },
      ]"
      :label="t('jobs.tailorResume')"
      clickable
    />
    <div class="flex flex-wrap items-center gap-2 text-sm text-ink-600">
      <span class="tabular-nums">{{ beforeGrade }} → {{ afterGrade }}</span>
      <FnChip v-if="run && (run.status === 'queued' || run.status === 'running')">{{
        run.status
      }}</FnChip>
    </div>

    <WaitingForClaude v-if="inboxWaiting > 0" :waiting="inboxWaiting" />

    <div v-if="startMut.isPending.value" class="space-y-2">
      <FnSkeleton class="h-10" />
      <FnSkeleton class="h-40" />
    </div>

    <template v-else-if="run">
      <section
        v-if="step === 'match'"
        class="min-w-0 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)] sm:p-5"
      >
        <div class="mb-3 flex flex-col gap-1">
          <h2 class="text-lg font-bold tracking-[-0.02em] text-ink-900">
            {{ t("tailor.ledger") }}
          </h2>
          <p class="text-sm leading-6 text-ink-600">{{ t("tailor.ledgerHint") }}</p>
        </div>
        <div
          v-if="knockouts.length"
          class="mb-3 rounded-lg border border-oxblood-600 bg-paper-0 p-3 text-sm"
        >
          <p class="font-medium text-ink-900">{{ t("tailor.knockouts") }}</p>
          <ul class="mt-1 space-y-1 text-ink-600">
            <li v-for="(k, i) in knockouts" :key="i">{{ k.reason }} · {{ k.quote }}</li>
          </ul>
        </div>
        <ul class="divide-y divide-rule text-sm">
          <li v-for="(row, i) in ledgerRows" :key="i" class="px-1 py-3">
            <div class="flex gap-2">
              <span class="mt-0.5 w-4 shrink-0 text-center text-xs font-bold">{{
                verdictGlyph(String(row.verdict))
              }}</span>
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-1.5">
                  <FnChip>{{ row.kind }}</FnChip>
                  <span class="text-ink-900">{{ row.text }}</span>
                </div>
                <p class="mt-1 text-xs leading-5 text-ink-400">
                  {{ row.before || "-" }} → {{ row.verdict }}
                  <span v-if="row.evidence_quote"> · {{ row.evidence_quote }}</span>
                </p>
              </div>
            </div>
          </li>
        </ul>
        <ul v-if="gaps.length" class="mt-3 space-y-2 text-sm">
          <li v-for="(g, i) in gaps" :key="i" class="rounded-lg border border-rule bg-paper-0 p-3">
            <p class="font-medium">{{ g.text }}</p>
            <p class="text-ink-600">{{ g.message }}</p>
          </li>
        </ul>
        <FnButton class="mt-4" size="sm" tone="primary" @click="step = 'edits'">
          {{ t("start.next") }}
        </FnButton>
      </section>

      <section
        v-else-if="step === 'edits'"
        class="min-w-0 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)] sm:p-5"
      >
        <div class="mb-3 flex flex-col gap-1">
          <h2 class="text-lg font-bold tracking-[-0.02em] text-ink-900">
            {{ t("tailor.changes") }}
          </h2>
          <p class="text-sm leading-6 text-ink-600">{{ t("tailor.changesHint") }}</p>
        </div>
        <p v-if="!changes.length" class="text-sm text-ink-600">{{ t("tailor.noChanges") }}</p>
        <ul v-else class="divide-y divide-rule text-sm">
          <li v-for="(ch, i) in changes" :key="ch.change_id || i" class="py-3">
            <p class="text-ink-600">{{ ch.reason }}</p>
            <p v-if="ch.before" class="mt-1 text-ink-400 line-through">{{ ch.before }}</p>
            <p v-if="ch.after" class="text-ink-900">{{ ch.after }}</p>
            <div v-if="ch.change_id" class="mt-2 flex gap-1">
              <FnButton
                size="sm"
                :tone="ch.status === 'accepted' ? 'quiet' : 'ghost'"
                :disabled="ch.status === 'accepted' || changeMut.isPending.value"
                @click="decideChange(ch.change_id, 'accepted')"
              >
                {{ t("tailor.keep") }}
              </FnButton>
              <FnButton
                size="sm"
                :tone="ch.status === 'rejected' ? 'quiet' : 'ghost'"
                :disabled="ch.status === 'rejected' || changeMut.isPending.value"
                @click="decideChange(ch.change_id, 'rejected')"
              >
                {{ t("tailor.remove") }}
              </FnButton>
            </div>
          </li>
        </ul>
        <div class="mt-4 flex flex-wrap gap-2">
          <FnButton size="sm" tone="ghost" @click="step = 'match'">{{ t("start.back") }}</FnButton>
          <FnButton size="sm" tone="primary" @click="step = 'check'">{{
            t("start.next")
          }}</FnButton>
        </div>
      </section>

      <section
        v-else
        class="min-w-0 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)] sm:p-5"
      >
        <p class="mb-3 text-sm leading-6 text-ink-600">{{ t("tailor.previewHint") }}</p>
        <div class="mb-3 flex gap-1 rounded-lg bg-paper-2 p-1">
          <button
            type="button"
            class="min-h-11 rounded-md px-4 text-sm font-semibold"
            :class="
              tab !== 'letter'
                ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
                : 'text-ink-600'
            "
            @click="tab = 'preview'"
          >
            {{ t("tailor.resume") }}
          </button>
          <button
            type="button"
            class="min-h-11 rounded-md px-4 text-sm font-semibold"
            :class="
              tab === 'letter'
                ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
                : 'text-ink-600'
            "
            @click="tab = 'letter'"
          >
            {{ t("tailor.letter") }}
          </button>
        </div>
        <pre
          v-if="tab !== 'letter'"
          class="overflow-x-auto whitespace-pre-wrap rounded-lg bg-paper-0 p-4 text-sm text-ink-900"
          >{{ previewText }}</pre>
        <div v-else class="rounded-lg bg-paper-0 p-4 text-sm text-ink-900">
          <p v-if="!letter" class="text-ink-600">{{ t("tailor.noLetter") }}</p>
          <template v-else>
            <p class="mb-2 text-xs text-ink-400">{{ letter.word_count }} {{ t("tailor.words") }}</p>
            <pre class="whitespace-pre-wrap font-sans">{{ letter.content }}</pre>
          </template>
        </div>
        <div class="mt-4 flex flex-wrap gap-2">
          <FnButton size="sm" tone="ghost" @click="step = 'edits'">{{ t("start.back") }}</FnButton>
          <FnButton
            size="sm"
            tone="primary"
            :disabled="!run || acceptMut.isPending.value || run.status !== 'ready'"
            @click="acceptMut.mutate()"
          >
            {{ t("tailor.acceptAttach") }}
          </FnButton>
        </div>
      </section>
    </template>
  </div>
</template>
