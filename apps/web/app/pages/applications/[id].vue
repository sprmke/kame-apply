<script setup lang="ts">
import {
  applicationAnswersApiV1ApplicationsApplicationIdAnswersGet,
  client,
  getApplicationApiV1ApplicationsAppIdGet,
  patchNotesApiV1ApplicationsAppIdNotesPatch,
  patchStatusApiV1ApplicationsAppIdStatusPatch,
  type ApplicationRead,
  type ApplicationStatusBody,
  type ItemRead,
} from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

type ApplyRun = {
  id: string;
  status: string;
  ats: string;
  page_url: string;
  submit_approved: boolean;
  last_step_seq: number;
  runner_id: string | null;
  failure_reason: string | null;
};
type Checkpoint = {
  id: string;
  run_id: string;
  kind: string;
  detail: Record<string, unknown>;
  status: string;
  decision: Record<string, unknown> | null;
};
type RunStep = {
  id: string;
  seq: number;
  action: string;
  field_label: string;
  value_redacted: string;
  outcome: string;
  screenshot_r2?: string | null;
};

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
  "job_closed",
] as const;

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const route = useRoute();
const fmt = useFormat();

const appId = computed(() => String(route.params.id));
const notes = ref("");
const noteForStatus = ref("");
const savingNotes = ref(false);
const startingRunner = ref(false);
const runnerWarnings = ref<string[]>([]);
const resolving = ref<string | null>(null);
const typedValue = ref("");

const strategy = useQuery({
  queryKey: computed(() => ["app-strategy", ws.currentId, appId.value]),
  queryFn: async () => {
    const [cap, sal, fu] = await Promise.all([
      client.get({
        url: `/api/v1/applications/${appId.value}/company-cap`,
        throwOnError: true,
      }),
      client.get({
        url: `/api/v1/applications/${appId.value}/salary-advice`,
        throwOnError: true,
      }),
      client.get({
        url: `/api/v1/applications/${appId.value}/follow-up-drafts`,
        throwOnError: true,
      }),
    ]);
    return {
      cap: cap.data as { message: string; warn: boolean; exceeds: boolean },
      salary: sal.data as {
        suggested_min: number | null;
        suggested_max: number | null;
        currency: string;
        rationale: string;
      },
      followUps: fu.data as { day_7: string; day_14: string },
    };
  },
  enabled: computed(() => Boolean(ws.currentId && appId.value)),
});

type InterviewPrep = {
  company_brief: string;
  likely_questions: Array<{ q: string; hint: string }>;
  star_stories: Array<{ situation: string; action: string }>;
  checklist: Array<{ item: string }>;
};
type ReferralMatch = {
  contact: { id: string; name: string; company: string };
  score: number;
  reason: string;
};

const prepGenerating = ref(false);
const draftingReferral = ref<string | null>(null);
const referralDraft = ref("");

const interviewPrep = useQuery({
  queryKey: computed(() => ["interview-prep", ws.currentId, appId.value]),
  queryFn: async () => {
    try {
      const { data } = await client.get({
        url: `/api/v1/applications/${appId.value}/interview-prep`,
        throwOnError: true,
      });
      return data as InterviewPrep;
    } catch {
      return null;
    }
  },
  enabled: computed(() => Boolean(ws.currentId && appId.value)),
});

const referralMatches = useQuery({
  queryKey: computed(() => ["referral-matches", ws.currentId, appId.value]),
  queryFn: async () => {
    const { data } = await client.get({
      url: `/api/v1/applications/${appId.value}/referral-matches`,
      throwOnError: true,
    });
    return data as ReferralMatch[];
  },
  enabled: computed(() => Boolean(ws.currentId && appId.value)),
});

const detail = useQuery({
  queryKey: computed(() => ["application", ws.currentId, appId.value]),
  queryFn: async () => {
    const { data } = await getApplicationApiV1ApplicationsAppIdGet({
      path: { app_id: appId.value },
      throwOnError: true,
    });
    return data as ApplicationRead;
  },
  enabled: computed(() => Boolean(ws.currentId && appId.value)),
});

const runs = useQuery({
  queryKey: computed(() => ["apply-runs", ws.currentId, appId.value]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/runs",
      query: { application_id: appId.value },
      throwOnError: true,
    });
    return (data ?? []) as ApplyRun[];
  },
  enabled: computed(() => Boolean(ws.currentId && appId.value)),
  refetchInterval: 4000,
});

const activeRun = computed(() => {
  const list = runs.data.value ?? [];
  return (
    list.find((r) => ["queued", "running", "needs_you", "paused"].includes(r.status)) ??
    list[0] ??
    null
  );
});

const checkpoints = useQuery({
  queryKey: computed(() => ["apply-checkpoints", ws.currentId, activeRun.value?.id]),
  queryFn: async () => {
    const id = activeRun.value?.id;
    if (!id) return [] as Checkpoint[];
    const { data } = await client.get({
      url: `/api/v1/runs/${id}/checkpoints`,
      throwOnError: true,
    });
    return (data ?? []) as Checkpoint[];
  },
  enabled: computed(() => Boolean(ws.currentId && activeRun.value?.id)),
  refetchInterval: 3000,
});

const steps = useQuery({
  queryKey: computed(() => ["apply-steps", ws.currentId, activeRun.value?.id]),
  queryFn: async () => {
    const id = activeRun.value?.id;
    if (!id) return [] as RunStep[];
    const { data } = await client.get({
      url: `/api/v1/runs/${id}/steps`,
      throwOnError: true,
    });
    return (data ?? []) as RunStep[];
  },
  enabled: computed(() => Boolean(ws.currentId && activeRun.value?.id)),
});

const openCheckpoint = computed(
  () => (checkpoints.data.value ?? []).find((c) => c.status === "open") ?? null,
);

async function startRunner() {
  if (!app.value) return;
  startingRunner.value = true;
  try {
    const { data } = await client.post({
      url: "/api/v1/runs/runner/start",
      body: { application_id: app.value.id, allow_submit: true },
      throwOnError: true,
    });
    runnerWarnings.value =
      (data as { policy?: { warnings?: string[] } } | undefined)?.policy?.warnings ?? [];
    await qc.invalidateQueries({ queryKey: ["apply-runs", ws.currentId, appId.value] });
    await qc.invalidateQueries({ queryKey: ["application", ws.currentId, appId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    startingRunner.value = false;
  }
}

async function resolveCheckpoint(decision: string) {
  const cp = openCheckpoint.value;
  if (!cp) return;
  resolving.value = decision;
  try {
    await client.post({
      url: `/api/v1/runs/checkpoints/${cp.id}/resolve`,
      body: {
        decision,
        value: decision === "typed_value" ? typedValue.value : undefined,
      },
      throwOnError: true,
    });
    typedValue.value = "";
    await qc.invalidateQueries({
      queryKey: ["apply-checkpoints", ws.currentId, activeRun.value?.id],
    });
    await qc.invalidateQueries({ queryKey: ["apply-runs", ws.currentId, appId.value] });
    await qc.invalidateQueries({ queryKey: ["application", ws.currentId, appId.value] });
    await qc.invalidateQueries({ queryKey: ["needs-you", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    resolving.value = null;
  }
}

async function handoff() {
  if (!activeRun.value) return;
  try {
    const { data } = await client.post({
      url: `/api/v1/runs/${activeRun.value.id}/handoff`,
      throwOnError: true,
    });
    const url = (data as { url?: string })?.url;
    if (url) window.open(url, "_blank", "noopener");
    await qc.invalidateQueries({ queryKey: ["apply-runs", ws.currentId, appId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

const deskAnswers = useQuery({
  queryKey: computed(() => ["application-answers", ws.currentId, appId.value]),
  queryFn: async () => {
    const { data } = await applicationAnswersApiV1ApplicationsApplicationIdAnswersGet({
      path: { application_id: appId.value },
      throwOnError: true,
    });
    return (data ?? []) as ItemRead[];
  },
  enabled: computed(() => Boolean(ws.currentId && appId.value)),
});

watch(
  () => detail.data.value?.notes,
  (v) => {
    notes.value = v ?? "";
  },
  { immediate: true },
);

const app = computed(() => detail.data.value ?? null);
const loading = computed(
  () => !ws.loaded || detail.isPending.value || (detail.isFetching.value && !app.value),
);
const jobDescription = computed(() => {
  const job = app.value?.job as Record<string, unknown> | null | undefined;
  return String(job?.description_text || "");
});

async function changeStatus(next: string) {
  if (!app.value) return;
  try {
    await patchStatusApiV1ApplicationsAppIdStatusPatch({
      path: { app_id: app.value.id },
      body: {
        status: next as ApplicationStatusBody["status"],
        note: noteForStatus.value,
      },
      throwOnError: true,
    });
    noteForStatus.value = "";
    await qc.invalidateQueries({ queryKey: ["application", ws.currentId, appId.value] });
    await qc.invalidateQueries({ queryKey: ["applications", ws.currentId] });
    await qc.invalidateQueries({ queryKey: ["home", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function saveNotes() {
  if (!app.value) return;
  savingNotes.value = true;
  try {
    await patchNotesApiV1ApplicationsAppIdNotesPatch({
      path: { app_id: app.value.id },
      body: { notes: notes.value },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["application", ws.currentId, appId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    savingNotes.value = false;
  }
}

async function copyFollowUp() {
  const text = app.value?.follow_up_draft || "";
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    toast.push({ title: t("applications.copied") });
  } catch {
    toast.push({ title: t("applications.copyFailed"), tone: "danger" });
  }
}

async function generatePrep() {
  prepGenerating.value = true;
  try {
    await client.post({
      url: `/api/v1/applications/${appId.value}/interview-prep`,
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["interview-prep", ws.currentId, appId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    prepGenerating.value = false;
  }
}

async function draftReferral(contactId: string) {
  draftingReferral.value = contactId;
  try {
    const { data } = await client.post({
      url: `/api/v1/applications/${appId.value}/referral-drafts`,
      body: { contact_id: contactId },
      throwOnError: true,
    });
    referralDraft.value = (data as { draft: string }).draft;
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    draftingReferral.value = null;
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-6">
    <div>
      <NuxtLink to="/applications" class="text-sm text-brand-700 underline">{{
        t("nav.applications")
      }}</NuxtLink>
    </div>

    <div v-if="loading"><FnSkeleton class="h-40 w-full" /></div>
    <template v-else-if="app">
      <header class="flex flex-col gap-2 border-b border-rule pb-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 class="font-serif text-2xl font-semibold text-ink-900">
              {{ app.job_title || t("applications.title") }}
            </h1>
            <p class="text-ink-600">{{ app.company_name }}</p>
          </div>
          <FnChip>{{ app.status }}</FnChip>
        </div>
        <p v-if="app.duplicate_warning" class="text-sm text-oxblood-700">
          {{ t("applications.duplicate") }}
        </p>
        <div class="flex flex-wrap gap-2 text-sm">
          <a
            v-if="app.apply_url"
            :href="app.apply_url"
            target="_blank"
            rel="noopener"
            class="text-brand-700 underline"
            >{{ t("applications.openPosting") }}</a
          >
          <span class="font-mono text-[0.6875rem] text-ink-600">{{ app.method }}</span>
          <span v-if="app.lens_grade" class="font-mono text-[0.6875rem] text-ink-600">{{
            app.lens_grade
          }}</span>
        </div>
      </header>

      <section class="flex flex-col gap-2">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("applications.status") }}
        </h2>
        <div class="flex flex-wrap gap-2">
          <select
            class="min-h-11 border border-rule bg-paper-0 px-2 text-sm"
            :value="app.status"
            @change="changeStatus(($event.target as HTMLSelectElement).value)"
          >
            <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
          </select>
          <input
            v-model="noteForStatus"
            type="text"
            class="min-h-11 min-w-[12rem] flex-1 border border-rule bg-paper-0 px-2 text-sm"
            :placeholder="t('applications.statusNote')"
          />
        </div>
      </section>

      <section class="flex flex-col gap-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("applications.runner") }}
          </h2>
          <div class="flex flex-wrap gap-2">
            <FnButton
              v-if="['ready', 'in_progress', 'needs_you'].includes(app.status)"
              size="sm"
              :disabled="startingRunner"
              @click="startRunner"
              >{{ t("applications.applyRunner") }}</FnButton
            >
            <FnButton
              v-if="activeRun && ['running', 'needs_you', 'paused'].includes(activeRun.status)"
              size="sm"
              tone="quiet"
              @click="handoff"
              >{{ t("applications.handoff") }}</FnButton
            >
          </div>
        </div>
        <p v-if="runnerWarnings.length" class="text-sm text-saffron-600">
          {{ runnerWarnings.join(" ") }}
        </p>
        <div v-if="activeRun" class="flex flex-wrap items-center gap-2 text-sm">
          <FnChip>{{ activeRun.status }}</FnChip>
          <span class="font-mono text-[0.6875rem] text-ink-600">{{ activeRun.ats }}</span>
          <span v-if="activeRun.runner_id" class="font-mono text-[0.6875rem] text-ink-600">{{
            activeRun.runner_id
          }}</span>
          <span class="font-mono text-[0.6875rem] text-ink-600"
            >{{ activeRun.last_step_seq }} steps</span
          >
        </div>
        <div v-if="openCheckpoint" class="flex flex-col gap-2 border border-rule bg-paper-1 p-3">
          <p class="text-sm font-medium text-ink-900">{{ openCheckpoint.kind }}</p>
          <p class="text-sm text-ink-600">
            {{
              String(
                openCheckpoint.detail.label || openCheckpoint.detail.message || openCheckpoint.kind,
              )
            }}
          </p>
          <input
            v-if="openCheckpoint.kind === 'sensitive_field'"
            v-model="typedValue"
            type="password"
            autocomplete="off"
            class="min-h-11 border border-rule bg-paper-0 px-2 text-sm"
            :aria-label="t('applications.typedValue')"
          />
          <div class="flex flex-wrap gap-2">
            <FnButton
              v-if="openCheckpoint.kind === 'final_review'"
              size="sm"
              :disabled="!!resolving"
              @click="resolveCheckpoint('approve_submit')"
              >{{ t("applications.approveSubmit") }}</FnButton
            >
            <FnButton
              v-if="openCheckpoint.kind === 'final_review'"
              size="sm"
              tone="quiet"
              :disabled="!!resolving"
              @click="resolveCheckpoint('deny_submit')"
              >{{ t("applications.denySubmit") }}</FnButton
            >
            <FnButton
              v-if="openCheckpoint.kind === 'sensitive_field'"
              size="sm"
              :disabled="!!resolving || !typedValue"
              @click="resolveCheckpoint('typed_value')"
              >{{ t("common.save") }}</FnButton
            >
            <FnButton
              v-if="openCheckpoint.kind !== 'final_review'"
              size="sm"
              :disabled="!!resolving"
              @click="resolveCheckpoint('continue')"
              >{{ t("common.continue") }}</FnButton
            >
            <FnButton
              size="sm"
              tone="quiet"
              :disabled="!!resolving"
              @click="resolveCheckpoint('skip')"
              >{{ t("applications.skip") }}</FnButton
            >
            <FnButton
              size="sm"
              tone="quiet"
              :disabled="!!resolving"
              @click="resolveCheckpoint('cancel')"
              >{{ t("common.cancel") }}</FnButton
            >
          </div>
        </div>
        <LiveViewCanvas
          v-if="
            activeRun && ['queued', 'running', 'needs_you', 'paused'].includes(activeRun.status)
          "
          :run-id="activeRun.id"
          :open-checkpoint-kind="openCheckpoint?.kind ?? null"
        />
        <ol
          v-if="(steps.data.value ?? []).length"
          class="divide-y divide-rule border-y border-rule text-sm"
        >
          <li v-for="st in steps.data.value ?? []" :key="st.id" class="py-2">
            <span class="font-mono text-[0.6875rem] text-ink-600">{{ st.seq }}</span>
            <span class="ml-2 font-medium">{{ st.action }}</span>
            <span class="ml-2 text-ink-600">{{ st.field_label }}</span>
            <span v-if="st.value_redacted" class="ml-2 font-mono text-[0.6875rem] text-ink-600">{{
              st.value_redacted
            }}</span>
            <span v-if="st.screenshot_r2" class="ml-2 font-mono text-[0.6875rem] text-brand-700">{{
              t("applications.replay")
            }}</span>
          </li>
        </ol>
      </section>

      <section v-if="strategy.data.value" class="flex flex-col gap-2 text-sm">
        <p
          v-if="strategy.data.value.cap.warn || strategy.data.value.cap.exceeds"
          class="text-brand-800"
        >
          {{ strategy.data.value.cap.message }}
        </p>
        <p v-if="strategy.data.value.salary.suggested_min != null" class="text-ink-600">
          {{ strategy.data.value.salary.suggested_min }}–{{
            strategy.data.value.salary.suggested_max
          }}
          {{ strategy.data.value.salary.currency }}
        </p>
      </section>

      <section class="flex flex-col gap-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("applications.interviewPrep") }}
          </h2>
          <FnButton size="sm" :disabled="prepGenerating" @click="generatePrep">{{
            t("applications.generatePrep")
          }}</FnButton>
        </div>
        <template v-if="interviewPrep.data.value">
          <p class="text-sm text-ink-600">{{ interviewPrep.data.value.company_brief }}</p>
          <ul class="flex flex-col gap-2 text-sm">
            <li v-for="(q, i) in interviewPrep.data.value.likely_questions.slice(0, 5)" :key="i">
              <span class="font-medium text-ink-900">{{ q.q }}</span>
            </li>
          </ul>
        </template>
      </section>

      <section class="flex flex-col gap-3">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("applications.referrals") }}
        </h2>
        <ul class="divide-y divide-rule border-y border-rule text-sm">
          <li
            v-for="m in referralMatches.data.value ?? []"
            :key="m.contact.id"
            class="flex flex-wrap items-center justify-between gap-2 py-2"
          >
            <span
              >{{ m.contact.name }}
              <span class="text-ink-600">· {{ m.contact.company }}</span></span
            >
            <FnButton
              size="sm"
              tone="quiet"
              :disabled="draftingReferral === m.contact.id"
              @click="draftReferral(m.contact.id)"
              >{{ t("applications.draftReferral") }}</FnButton
            >
          </li>
        </ul>
        <pre
          v-if="referralDraft"
          class="whitespace-pre-wrap border border-rule bg-paper-1 p-3 text-sm text-ink-900"
          >{{ referralDraft }}</pre>
      </section>

      <section
        v-if="app.follow_up_draft || strategy.data.value?.followUps"
        class="flex flex-col gap-2"
      >
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("applications.followUp") }}
          </h2>
          <FnButton size="sm" tone="quiet" @click="copyFollowUp">{{
            t("applications.copy")
          }}</FnButton>
        </div>
        <p v-if="app.reminder_at" class="font-mono text-[0.6875rem] text-ink-600">
          {{ fmt.dateTime(app.reminder_at) }}
        </p>
        <pre
          class="whitespace-pre-wrap border border-rule bg-paper-1 p-3 font-serif text-sm text-ink-900"
          >{{ app.follow_up_draft || strategy.data.value?.followUps?.day_7 }}</pre>
        <pre
          v-if="strategy.data.value?.followUps?.day_14"
          class="whitespace-pre-wrap border border-rule bg-paper-1 p-3 font-serif text-sm text-ink-900"
          >{{ strategy.data.value.followUps.day_14 }}</pre>
      </section>

      <section class="flex flex-col gap-2">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("applications.timeline") }}
        </h2>
        <ol class="divide-y divide-rule border-y border-rule text-sm">
          <li v-for="e in app.events ?? []" :key="String(e.id)" class="py-2">
            <div class="flex justify-between gap-3">
              <span class="font-medium text-ink-900">{{ e.type }}</span>
              <span class="shrink-0 font-mono text-[0.6875rem] text-ink-600">{{
                e.at ? fmt.dateTime(String(e.at)) : ""
              }}</span>
            </div>
            <p v-if="e.note" class="text-ink-600">{{ e.note }}</p>
          </li>
        </ol>
      </section>

      <section v-if="(app.reminders ?? []).length" class="flex flex-col gap-2">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("applications.reminders") }}
        </h2>
        <ul class="divide-y divide-rule border-y border-rule text-sm">
          <li v-for="r in app.reminders ?? []" :key="String(r.id)" class="py-2">
            <span class="font-medium">{{ r.kind }}</span>
            <span class="ml-2 font-mono text-[0.6875rem] text-ink-600">{{
              r.due_at ? fmt.dateTime(String(r.due_at)) : ""
            }}</span>
          </li>
        </ul>
      </section>

      <section v-if="app.job" class="flex flex-col gap-2">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("applications.snapshot") }}
        </h2>
        <p class="text-sm text-ink-600">
          {{
            app.job_snapshot_r2 ? t("applications.snapshotSaved") : t("applications.snapshotLive")
          }}
        </p>
        <div
          class="max-h-64 overflow-y-auto border border-rule bg-paper-1 p-3 text-sm whitespace-pre-wrap"
        >
          {{ jobDescription }}
        </div>
      </section>

      <section class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
            {{ t("nav.answers") }}
          </h2>
          <NuxtLink
            :to="`/answers?application=${app.id}`"
            class="text-sm text-brand-700 underline"
            >{{ t("answers.draft") }}</NuxtLink
          >
        </div>
        <ul
          v-if="(deskAnswers.data.value ?? []).length"
          class="divide-y divide-rule border-y border-rule text-sm"
        >
          <li v-for="a in deskAnswers.data.value ?? []" :key="a.id" class="py-2">
            <p class="font-medium text-ink-900">{{ a.question }}</p>
            <p class="text-ink-600">{{ a.draft || t("answers.writeYourself") }}</p>
          </li>
        </ul>
      </section>

      <section class="flex flex-col gap-2">
        <h2 class="text-sm font-medium tracking-wide text-ink-600 uppercase">
          {{ t("applications.notes") }}
        </h2>
        <textarea v-model="notes" rows="5" class="border border-rule bg-paper-0 p-2 text-sm" />
        <div class="flex justify-end">
          <FnButton size="sm" :disabled="savingNotes" @click="saveNotes">{{
            t("common.save")
          }}</FnButton>
        </div>
      </section>
    </template>
  </div>
</template>
