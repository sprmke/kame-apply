<script setup lang="ts">
import {
  acceptTailorApiV1TailorRunsRunIdAcceptPost,
  decideTailorChangeApiV1TailorRunsRunIdChangesChangeIdPost,
  startTailorApiV1TrackJobsTrackJobIdTailorPost,
  type TailorRunRead,
} from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton, useToast } from "@kame/ui";
import { useMutation } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const route = useRoute();
const router = useRouter();
const { waiting: inboxWaiting } = useAgentInboxStatus();

const trackJobId = computed(() => String(route.params.trackJobId || ""));
const tab = ref<"ledger" | "changes" | "preview" | "letter">("ledger");
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
  onSuccess: (data) => {
    run.value = data;
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
  <div class="mx-auto flex max-w-6xl flex-col gap-4 p-4 md:p-6">
    <header class="flex flex-wrap items-center gap-2">
      <h1 class="font-display text-xl text-ink-900">Tailor</h1>
      <div class="font-mono text-sm text-ink-700">{{ beforeGrade }} → {{ afterGrade }}</div>
      <div class="ml-auto flex flex-wrap gap-1">
        <FnButton size="sm" tone="ghost" @click="router.push('/jobs')">Back</FnButton>
        <FnButton
          size="sm"
          :disabled="!run || acceptMut.isPending.value || run.status !== 'ready'"
          @click="acceptMut.mutate()"
        >
          Accept
        </FnButton>
      </div>
    </header>
    <WaitingForClaude v-if="inboxWaiting > 0" :waiting="inboxWaiting" />

    <div v-if="startMut.isPending.value" class="space-y-2">
      <FnSkeleton class="h-10" />
      <FnSkeleton class="h-40" />
    </div>

    <template v-else-if="run">
      <div class="flex flex-wrap gap-1 border-b border-ink-100 pb-2 lg:hidden">
        <FnButton
          v-for="item in [
            ['ledger', 'Ledger'],
            ['changes', 'Changes'],
            ['preview', 'Preview'],
            ['letter', 'Letter'],
          ] as const"
          :key="item[0]"
          size="sm"
          :tone="tab === item[0] ? 'primary' : 'ghost'"
          @click="tab = item[0]"
        >
          {{ item[1] }}
        </FnButton>
      </div>

      <div class="grid gap-4 lg:grid-cols-3">
        <section v-show="tab === 'ledger'" class="min-w-0 lg:!block">
          <div v-if="knockouts.length" class="mb-3 border border-oxblood-600 p-2 text-sm">
            <p class="font-medium text-ink-900">Knockouts</p>
            <ul class="mt-1 space-y-1 text-ink-700">
              <li v-for="(k, i) in knockouts" :key="i">{{ k.reason }} · {{ k.quote }}</li>
            </ul>
          </div>
          <ul class="divide-y divide-ink-100 border border-ink-100 text-sm">
            <li v-for="(row, i) in ledgerRows" :key="i" class="px-3 py-2">
              <div class="flex gap-2">
                <span class="font-mono text-xs">{{ verdictGlyph(String(row.verdict)) }}</span>
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap gap-1">
                    <FnChip>{{ row.kind }}</FnChip>
                    <span class="text-ink-800">{{ row.text }}</span>
                  </div>
                  <p class="mt-1 text-xs text-ink-500">
                    {{ row.before || "-" }} → {{ row.verdict }}
                    <span v-if="row.evidence_quote"> · {{ row.evidence_quote }}</span>
                  </p>
                </div>
              </div>
            </li>
          </ul>
          <ul v-if="gaps.length" class="mt-3 space-y-2 text-sm">
            <li v-for="(g, i) in gaps" :key="i" class="border border-ink-100 p-2">
              <p class="font-medium">{{ g.text }}</p>
              <p class="text-ink-600">{{ g.message }}</p>
            </li>
          </ul>
        </section>

        <section v-show="tab === 'changes'" class="min-w-0 lg:!block">
          <p v-if="!changes.length" class="text-sm text-ink-600">No text changes</p>
          <ul v-else class="divide-y divide-ink-100 border border-ink-100 text-sm">
            <li v-for="(ch, i) in changes" :key="ch.change_id || i" class="p-3">
              <p class="font-medium">{{ ch.op }}</p>
              <p class="text-ink-600">{{ ch.reason }}</p>
              <p v-if="ch.before" class="mt-1 text-ink-500 line-through">{{ ch.before }}</p>
              <p v-if="ch.after" class="text-ink-900">{{ ch.after }}</p>
              <div v-if="ch.change_id" class="mt-2 flex gap-1">
                <FnButton
                  size="sm"
                  :tone="ch.status === 'accepted' ? 'primary' : 'ghost'"
                  :disabled="ch.status === 'accepted' || changeMut.isPending.value"
                  @click="decideChange(ch.change_id, 'accepted')"
                >
                  Keep
                </FnButton>
                <FnButton
                  size="sm"
                  :tone="ch.status === 'rejected' ? 'primary' : 'ghost'"
                  :disabled="ch.status === 'rejected' || changeMut.isPending.value"
                  @click="decideChange(ch.change_id, 'rejected')"
                >
                  Remove
                </FnButton>
              </div>
            </li>
          </ul>
        </section>

        <section v-show="tab === 'preview' || tab === 'letter'" class="min-w-0 lg:!block">
          <div class="mb-2 hidden gap-1 lg:flex">
            <FnButton
              size="sm"
              :tone="tab !== 'letter' ? 'primary' : 'ghost'"
              @click="tab = 'preview'"
            >
              Preview
            </FnButton>
            <FnButton
              size="sm"
              :tone="tab === 'letter' ? 'primary' : 'ghost'"
              @click="tab = 'letter'"
            >
              Letter
            </FnButton>
          </div>
          <pre
            v-if="tab !== 'letter'"
            class="whitespace-pre-wrap border border-ink-100 p-3 font-mono text-xs text-ink-800"
            >{{ previewText }}</pre>
          <div v-else class="border border-ink-100 p-3 text-sm text-ink-800">
            <p v-if="!letter" class="text-ink-600">No cover letter</p>
            <template v-else>
              <p class="mb-2 text-xs text-ink-500">{{ letter.word_count }} words</p>
              <pre class="whitespace-pre-wrap font-sans">{{ letter.content }}</pre>
            </template>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
