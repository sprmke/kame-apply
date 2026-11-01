<script setup lang="ts">
import { FnButton, FnSelect } from "@kame/ui";
import { computed, onMounted, ref, watch } from "vue";

type Session = {
  token: string;
  workspaceId: string;
  apiBase: string;
  trackId?: string;
  profileId?: string;
};

type Summary = {
  workspace_id: string;
  tracks: { id: string; name: string; profile_id: string }[];
  profiles: { id: string; display_name: string; is_default: boolean }[];
};

const session = ref<Session | null>(null);
const summary = ref<Summary | null>(null);
const status = ref("");
const busy = ref(false);
const trackId = ref("");
const profileId = ref("");
const lastJob = ref<{
  job_id?: string;
  track_job_id?: string;
  title?: string;
  risk_level?: string;
} | null>(null);
const lastPlan = ref<{
  autofill_allowed?: boolean;
  page_ai_restricted?: boolean;
  notes?: string[];
  result?: { filled: number; checkpoints: number; skipped: number };
} | null>(null);

const trackOptions = computed(() =>
  (summary.value?.tracks || []).map((t) => ({ value: t.id, label: t.name })),
);
const profileOptions = computed(() =>
  (summary.value?.profiles || []).map((p) => ({
    value: p.id,
    label: p.display_name + (p.is_default ? " (default)" : ""),
  })),
);

async function refresh() {
  session.value = await browser.runtime.sendMessage({ type: "kame.getSession" });
  if (!session.value) {
    summary.value = null;
    return;
  }
  trackId.value = session.value.trackId || "";
  profileId.value = session.value.profileId || "";
  try {
    summary.value = await browser.runtime.sendMessage({ type: "kame.sessionSummary" });
    if (!profileId.value && summary.value?.profiles?.length) {
      const def = summary.value.profiles.find((p) => p.is_default) ?? summary.value.profiles[0];
      if (def) profileId.value = def.id;
    }
    if (!trackId.value && summary.value?.tracks?.length) {
      const first = summary.value.tracks[0];
      if (first) trackId.value = first.id;
    }
  } catch (e) {
    status.value = e instanceof Error ? e.message : "Session error";
  }
}

watch([trackId, profileId], async ([t, p]) => {
  if (!session.value) return;
  session.value = await browser.runtime.sendMessage({
    type: "kame.setPrefs",
    trackId: t,
    profileId: p,
  });
});

async function run(action: "clip" | "autofill" | "logApplied") {
  busy.value = true;
  status.value = "";
  try {
    if (action === "clip") {
      lastJob.value = await browser.runtime.sendMessage({ type: "kame.clip" });
      status.value = "Saved";
    } else if (action === "autofill") {
      lastPlan.value = await browser.runtime.sendMessage({
        type: "kame.autofill",
        jobId: lastJob.value?.job_id,
      });
      status.value = lastPlan.value?.autofill_allowed ? "Filled" : "Autofill off";
    } else {
      await browser.runtime.sendMessage({
        type: "kame.logApplied",
        trackJobId: lastJob.value?.track_job_id,
        jobId: lastJob.value?.job_id,
      });
      status.value = "Logged";
    }
  } catch (e) {
    status.value = e instanceof Error ? e.message : "Failed";
  } finally {
    busy.value = false;
  }
}

async function disconnect() {
  await browser.runtime.sendMessage({ type: "kame.clearSession" });
  session.value = null;
  summary.value = null;
  status.value = "";
}

onMounted(refresh);
</script>

<template>
  <main class="flex min-h-full flex-col gap-4 bg-paper-0 p-4 text-ink-900">
    <header class="flex items-baseline justify-between gap-2">
      <h1 class="font-serif text-xl font-semibold">Kame Apply</h1>
      <button
        v-if="session"
        type="button"
        class="text-xs text-ink-600 underline"
        @click="disconnect"
      >
        Disconnect
      </button>
    </header>

    <p v-if="!session" class="text-sm text-ink-700">
      Connect from Settings → Integrations in the web app.
    </p>

    <template v-else>
      <div class="flex flex-col gap-2">
        <FnSelect v-model="trackId" :options="trackOptions" placeholder="Track" />
        <FnSelect v-model="profileId" :options="profileOptions" placeholder="Profile" />
      </div>

      <div
        v-if="lastJob?.risk_level === 'red' || lastJob?.risk_level === 'high'"
        class="border border-persimmon-700 bg-paper-2 px-3 py-2 text-sm"
        role="status"
      >
        Risk flagged for this job
      </div>

      <div class="flex flex-col gap-2">
        <FnButton tone="primary" :disabled="busy" @click="run('clip')">Save to Track</FnButton>
        <FnButton :disabled="busy" @click="run('autofill')">Autofill</FnButton>
        <FnButton tone="ghost" :disabled="busy" @click="run('logApplied')">I applied</FnButton>
      </div>

      <p v-if="status" class="text-sm text-ink-700">{{ status }}</p>
      <p v-if="lastJob?.title" class="text-xs text-ink-600">{{ lastJob.title }}</p>
      <p v-if="lastPlan?.notes?.length" class="text-xs text-ink-600">
        {{ lastPlan.notes.join(" ") }}
      </p>
      <p v-if="lastPlan?.result" class="font-mono text-xs text-ink-600">
        filled {{ lastPlan.result.filled }} · review {{ lastPlan.result.checkpoints }} · skip
        {{ lastPlan.result.skipped }}
      </p>
      <p v-if="lastPlan?.page_ai_restricted" class="text-xs text-ink-700">
        AI drafts blocked on this page
      </p>
    </template>
  </main>
</template>
