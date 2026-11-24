<script setup lang="ts">
import {
  client,
  listApplicationsApiV1ApplicationsGet,
  matchReplyApiV1ResponsesMatchPost,
  type ApplicationRead,
  type ReplyMatchRead,
} from "@kame/api-client";
import {
  FnButton,
  FnChip,
  FnEmptyState,
  FnField,
  FnInput,
  FnSectionCard,
  FnSelect,
  FnSkeleton,
  FnSkeletonGroup,
  FnTextarea,
  useToast,
} from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

type Proposal = {
  id: string;
  application_id: string;
  from_status: string;
  to_status: string;
  reason: string;
  citation: string;
  status: string;
  company_name: string;
  job_title: string;
};

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const deciding = ref<string | null>(null);
const sender = ref("");
const subject = ref("");
const body = ref("");
const chosenId = ref("__none__");
const ingesting = ref(false);

const proposals = useQuery({
  queryKey: computed(() => ["response-proposals", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/responses/proposals",
      throwOnError: true,
    });
    return data as Proposal[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const applications = useQuery({
  queryKey: computed(() => ["applications", ws.currentId]),
  queryFn: async () => {
    const { data } = await listApplicationsApiV1ApplicationsGet({
      query: { limit: 200 },
      throwOnError: true,
    });
    return (data?.items ?? []) as ApplicationRead[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const NONE = "__none__";
const applicationOptions = computed(() => [
  { value: NONE, label: t("responses.chooseApplication") },
  ...(applications.data.value ?? []).map((a) => ({
    value: String(a.id),
    label: [a.job_title, a.company_name].filter(Boolean).join(" · ") || String(a.id),
  })),
]);

function words(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((w) => w.length > 2);
}

type BestMatch = {
  id: string;
  title: string;
  company: string;
  score: number;
  reason: string;
};

const serverMatch = ref<BestMatch | null>(null);
const serverBusy = ref(false);
let matchTimer: ReturnType<typeof setTimeout> | null = null;

/** Local fallback: company, title, and sender domain. No ids. */
const localMatch = computed<BestMatch | null>(() => {
  const rows = applications.data.value ?? [];
  const text = `${sender.value} ${subject.value} ${body.value}`.toLowerCase();
  if (!text.trim() || !rows.length) return null;
  const hit =
    rows
      .map((row) => {
        const company = words(String(row.company_name ?? ""));
        const title = words(String(row.job_title ?? ""));
        const domain = String(sender.value.split("@")[1] ?? "").split(".")[0] ?? "";
        let score = 0;
        for (const w of company) if (w.length > 3 && text.includes(w)) score += 3;
        for (const w of title) if (w.length > 3 && text.includes(w)) score += 1;
        if (domain.length > 3 && text.includes(domain)) score += 2;
        return { row, score };
      })
      .sort((a, b) => b.score - a.score)
      .find((entry) => entry.score >= 3) ?? null;
  if (!hit) return null;
  return {
    id: String(hit.row.id),
    title: String(hit.row.job_title ?? ""),
    company: String(hit.row.company_name ?? ""),
    score: hit.score,
    reason: "Company or sender in the email",
  };
});

const match = computed<BestMatch | null>(() => serverMatch.value ?? localMatch.value);

watch(
  [sender, subject, body],
  () => {
    if (matchTimer) clearTimeout(matchTimer);
    if (!body.value.trim()) {
      serverMatch.value = null;
      return;
    }
    matchTimer = setTimeout(async () => {
      serverBusy.value = true;
      try {
        const { data } = await matchReplyApiV1ResponsesMatchPost({
          body: {
            sender: sender.value,
            subject: subject.value,
            body_text: body.value,
          },
          throwOnError: true,
        });
        const row = data as ReplyMatchRead | null;
        serverMatch.value = row
          ? {
              id: String(row.application_id),
              title: row.job_title,
              company: row.company_name,
              score: row.score,
              reason: row.reason,
            }
          : null;
      } catch {
        serverMatch.value = null;
      } finally {
        serverBusy.value = false;
      }
    }, 500);
  },
  { immediate: false },
);

onUnmounted(() => {
  if (matchTimer) clearTimeout(matchTimer);
});

watch(match, (value) => {
  if (value) chosenId.value = value.id;
});

async function decide(id: string, accept: boolean) {
  deciding.value = id;
  try {
    await client.post({
      url: `/api/v1/responses/proposals/${id}/decide`,
      body: { accept },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["response-proposals", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    deciding.value = null;
  }
}

async function ingest() {
  ingesting.value = true;
  try {
    await client.post({
      url: "/api/v1/responses/ingest",
      body: {
        application_id: chosenId.value && chosenId.value !== NONE ? chosenId.value : null,
        sender: sender.value,
        subject: subject.value,
        body_text: body.value,
      },
      throwOnError: true,
    });
    body.value = "";
    subject.value = "";
    sender.value = "";
    await qc.invalidateQueries({ queryKey: ["response-proposals", ws.currentId] });
    toast.push({ title: t("responses.read"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    ingesting.value = false;
  }
}

function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-5">
    <PageHeader :title="t('responses.title')" :lede="t('responses.lede')" />

    <FnSectionCard :title="t('responses.paste')" :intro="t('responses.pasteIntro')">
      <FnField v-slot="{ id }" :label="t('responses.sender')">
        <FnInput
          :id="id"
          v-model="sender"
          type="email"
          placeholder="recruiter@acme.com"
          autocomplete="off"
        />
      </FnField>
      <FnField v-slot="{ id }" :label="t('responses.subject')">
        <FnInput :id="id" v-model="subject" />
      </FnField>
      <FnField v-slot="{ id }" :label="t('responses.body')">
        <FnTextarea :id="id" v-model="body" :rows="6" />
      </FnField>

      <p
        v-if="match && chosenId === match.id"
        class="rounded-lg bg-brand-50 px-3 py-2 text-sm leading-6 text-brand-800"
      >
        {{
          t("responses.matchFound", {
            title: match.title,
            company: match.company,
          })
        }}
      </p>

      <FnField
        v-slot="{ id }"
        :label="t('responses.application')"
        :help="t('responses.applicationHelp')"
      >
        <FnSelect :id="id" v-model="chosenId" :options="applicationOptions" />
      </FnField>

      <div class="flex flex-wrap items-center gap-2">
        <FnButton
          tone="primary"
          :disabled="ingesting || !body.trim()"
          :loading="ingesting"
          @click="ingest"
        >
          {{ t("responses.classify") }}
        </FnButton>
        <span v-if="serverBusy" class="text-sm text-ink-600">{{ t("responses.reading") }}</span>
        <span v-else-if="match" class="text-sm text-ink-600">{{ t("responses.matched") }}</span>
      </div>
      <p v-if="!applications.data.value?.length" class="text-sm text-ink-600">
        {{ t("responses.noApplications") }}
      </p>
    </FnSectionCard>

    <FnSectionCard :title="t('responses.proposals')" :intro="t('responses.proposalsIntro')">
      <FnSkeletonGroup v-if="proposals.isPending.value" :label="t('common.loading')">
        <ul class="divide-y divide-rule">
          <li
            v-for="n in 3"
            :key="n"
            class="flex flex-col gap-2 py-3 sm:flex-row sm:items-start sm:justify-between"
          >
            <div class="flex min-w-0 flex-1 flex-col gap-2">
              <FnSkeleton class="h-4 w-3/5" />
              <div class="flex items-center gap-2">
                <FnSkeleton class="h-6 w-20 rounded-full" />
                <FnSkeleton class="size-3 rounded" />
                <FnSkeleton class="h-6 w-24 rounded-full" />
              </div>
              <FnSkeleton class="h-3.5 w-4/5" />
            </div>
            <div class="flex flex-wrap gap-2">
              <FnSkeleton class="h-11 w-24 rounded-md" />
              <FnSkeleton class="h-11 w-20 rounded-md" />
            </div>
          </li>
        </ul>
      </FnSkeletonGroup>
      <FnEmptyState
        v-else-if="!(proposals.data.value ?? []).length"
        :title="t('responses.emptyProposals')"
      />
      <ul v-else class="divide-y divide-rule">
        <li
          v-for="p in proposals.data.value ?? []"
          :key="p.id"
          class="flex flex-col gap-2 py-3 sm:flex-row sm:items-start sm:justify-between"
        >
          <div class="min-w-0">
            <p class="font-medium text-ink-900">
              {{ p.job_title || t("applications.title") }}
              <span class="text-ink-600">· {{ p.company_name }}</span>
            </p>
            <p class="flex flex-wrap items-center gap-1.5 text-sm text-ink-600">
              <FnChip>{{ statusLabel(p.from_status) }}</FnChip>
              <span aria-hidden="true">→</span>
              <FnChip tone="accent">{{ statusLabel(p.to_status) }}</FnChip>
            </p>
            <p v-if="p.citation" class="mt-1 text-sm text-ink-600">{{ p.citation }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <FnButton
              size="sm"
              tone="primary"
              :disabled="deciding === p.id"
              @click="decide(p.id, true)"
              >{{ t("responses.accept") }}</FnButton
            >
            <FnButton
              size="sm"
              tone="quiet"
              :disabled="deciding === p.id"
              @click="decide(p.id, false)"
              >{{ t("responses.reject") }}</FnButton
            >
          </div>
        </li>
      </ul>
    </FnSectionCard>
  </div>
</template>
