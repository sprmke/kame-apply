<script setup lang="ts">
import { useActiveProfile } from "~/composables/useActiveProfile";
import {
  acceptInterviewProposalApiV1ProfilesProfileIdInterviewProposalsProposalIdAcceptPost,
  interviewTurnApiV1ProfilesProfileIdInterviewTurnsPost,
  listInterviewGapsApiV1ProfilesProfileIdInterviewGapsGet,
  listInterviewProposalsApiV1ProfilesProfileIdInterviewProposalsGet,
  rejectInterviewProposalApiV1ProfilesProfileIdInterviewProposalsProposalIdRejectPost,
  type InterviewGapRead,
  type ProposalRead,
} from "@kame/api-client";
import { FnButton, FnDialog, FnPencilText, FnTextarea, useToast } from "@kame/ui";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

const open = defineModel<boolean>("open", { default: false });
const props = defineProps<{ profileId: string }>();

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const auth = useAuthStore();
const ws = useWorkspaceStore();
const { refresh } = useActiveProfile();
const { public: cfg } = useRuntimeConfig();

const gap = ref<InterviewGapRead | null>(null);
const typed = ref("");
const answer = ref("");
const proposal = ref<ProposalRead | null>(null);
const pending = ref<ProposalRead[]>([]);
const busy = ref(false);
const streaming = ref(false);

async function loadGaps() {
  const { data } = await listInterviewGapsApiV1ProfilesProfileIdInterviewGapsGet({
    path: { profile_id: props.profileId },
    throwOnError: true,
  });
  gap.value = data?.[0] ?? null;
  typed.value = gap.value?.question ?? "";
}

async function loadPending() {
  const { data } = await listInterviewProposalsApiV1ProfilesProfileIdInterviewProposalsGet({
    path: { profile_id: props.profileId },
    query: { status: "pending" },
    throwOnError: true,
  });
  pending.value = data ?? [];
}

async function streamQuestion() {
  streaming.value = true;
  typed.value = "";
  try {
    const token = await auth.ensureFresh();
    const res = await fetch(`${cfg.apiBase}/api/v1/profiles/${props.profileId}/interview/stream`, {
      headers: {
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(ws.currentId ? { "X-Workspace-Id": ws.currentId } : {}),
      },
      credentials: "include",
    });
    if (!res.ok || !res.body) {
      await loadGaps();
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() ?? "";
      for (const chunk of parts) {
        const lines = chunk.split("\n");
        const event = lines
          .find((l) => l.startsWith("event:"))
          ?.slice(6)
          .trim();
        const dataLine = lines
          .find((l) => l.startsWith("data:"))
          ?.slice(5)
          .trim();
        if (!event || !dataLine) continue;
        const data = JSON.parse(dataLine) as Record<string, unknown>;
        if (event === "gap") {
          gap.value = {
            id: String(data.id),
            kind: data.kind as InterviewGapRead["kind"],
            target_type: data.target_type as InterviewGapRead["target_type"],
            target_id: String(data.target_id),
            question: "",
            context: (data.context as Record<string, unknown>) ?? {},
          };
        } else if (event === "token") {
          typed.value += String(data.text ?? "");
        } else if (event === "done" && !typed.value) {
          await loadGaps();
        }
      }
    }
    if (gap.value) gap.value = { ...gap.value, question: typed.value };
  } catch {
    await loadGaps();
  } finally {
    streaming.value = false;
  }
}

watch(open, async (v) => {
  if (!v) return;
  answer.value = "";
  proposal.value = null;
  await loadPending();
  await streamQuestion();
});

async function submitAnswer() {
  if (!gap.value || !answer.value.trim()) return;
  busy.value = true;
  try {
    const { data } = await interviewTurnApiV1ProfilesProfileIdInterviewTurnsPost({
      path: { profile_id: props.profileId },
      body: { gap_id: gap.value.id, answer: answer.value.trim() },
      throwOnError: true,
    });
    proposal.value = data!.proposal;
    await loadPending();
    answer.value = "";
    if (data?.next_gap) {
      gap.value = data.next_gap;
      typed.value = data.next_gap.question;
    } else {
      gap.value = null;
      typed.value = "";
    }
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}

async function accept(p: ProposalRead) {
  busy.value = true;
  try {
    await acceptInterviewProposalApiV1ProfilesProfileIdInterviewProposalsProposalIdAcceptPost({
      path: { profile_id: props.profileId, proposal_id: p.id },
      throwOnError: true,
    });
    proposal.value = null;
    await loadPending();
    await refresh();
    toast.push({ title: t("career.proposalAccepted"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}

async function reject(p: ProposalRead) {
  busy.value = true;
  try {
    await rejectInterviewProposalApiV1ProfilesProfileIdInterviewProposalsProposalIdRejectPost({
      path: { profile_id: props.profileId, proposal_id: p.id },
      throwOnError: true,
    });
    proposal.value = null;
    await loadPending();
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}

const shownProposals = computed(() => {
  if (!proposal.value) return pending.value;
  return [proposal.value, ...pending.value.filter((x) => x.id !== proposal.value!.id)];
});

function payloadLabel(p: ProposalRead): string {
  const payload = p.payload ?? {};
  if (Array.isArray(payload.metrics) && payload.metrics.length) {
    return payload.metrics
      .map((m: { name?: string; change?: string }) => `${m.name ?? ""} ${m.change ?? ""}`.trim())
      .join(", ");
  }
  if (payload.years != null) return `${payload.years} years`;
  if (typeof payload.note === "string") return payload.note;
  return p.kind;
}
</script>

<template>
  <FnDialog
    v-model:open="open"
    variant="sheet"
    :title="t('career.interview')"
    :close-label="t('common.close')"
  >
    <div class="flex flex-col gap-4">
      <div v-if="typed" class="rounded-sm border border-rule bg-paper-0 p-3 text-sm text-ink-900">
        <FnPencilText>{{ typed }}</FnPencilText>
        <span
          v-if="streaming"
          class="ml-1 inline-block h-3 w-1 animate-pulse bg-ink-600"
          aria-hidden="true"
        />
      </div>
      <p v-else-if="!pending.length" class="text-sm text-ink-600">
        {{ t("career.interviewDone") }}
      </p>

      <form v-if="gap && !streaming" class="flex flex-col gap-3" @submit.prevent="submitAnswer">
        <FnTextarea v-model="answer" :rows="4" :aria-label="t('career.yourAnswer')" />
        <FnButton type="submit" tone="primary" :loading="busy">{{ t("common.continue") }}</FnButton>
      </form>

      <div v-if="shownProposals.length" class="flex flex-col gap-3 border-t border-rule pt-4">
        <h3 class="text-sm font-medium text-ink-900">{{ t("career.proposals") }}</h3>
        <article
          v-for="p in shownProposals"
          :key="p.id"
          class="flex flex-col gap-2 rounded-sm border border-dashed border-pencil p-3"
        >
          <FnPencilText class="text-sm">{{ payloadLabel(p) }}</FnPencilText>
          <div class="flex gap-2">
            <FnButton size="sm" tone="primary" :loading="busy" @click="accept(p)">{{
              t("career.accept")
            }}</FnButton>
            <FnButton size="sm" tone="ghost" :loading="busy" @click="reject(p)">{{
              t("career.reject")
            }}</FnButton>
          </div>
        </article>
      </div>
    </div>
  </FnDialog>
</template>
