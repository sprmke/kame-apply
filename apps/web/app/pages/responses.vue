<script setup lang="ts">
import { client } from "@kame/api-client";
import { FnButton, FnChip, FnInput, FnSkeleton, FnTextarea, useToast } from "@kame/ui";
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

type IngestForm = {
  application_id: string;
  sender: string;
  subject: string;
  body_text: string;
};

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const deciding = ref<string | null>(null);
const form = reactive<IngestForm>({
  application_id: "",
  sender: "",
  subject: "",
  body_text: "",
});
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
        application_id: form.application_id.trim() || null,
        sender: form.sender,
        subject: form.subject,
        body_text: form.body_text,
      },
      throwOnError: true,
    });
    form.body_text = "";
    form.subject = "";
    await qc.invalidateQueries({ queryKey: ["response-proposals", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    ingesting.value = false;
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-8">
    <div class="flex flex-col gap-1">
      <h1 class="text-3xl font-bold tracking-[-0.03em] text-ink-900">{{ t("responses.title") }}</h1>
      <p class="max-w-2xl text-sm leading-6 text-ink-600">{{ t("responses.lede") }}</p>
    </div>

    <section
      class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-6 shadow-[var(--shadow-card)]"
    >
      <h2 class="text-sm font-semibold tracking-wide text-ink-600 uppercase">
        {{ t("responses.proposals") }}
      </h2>
      <div v-if="proposals.isPending.value"><FnSkeleton class="h-24 w-full" /></div>
      <ul v-else class="divide-y divide-rule border-y border-rule">
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
            <p class="text-sm text-ink-600">{{ p.from_status }} → {{ p.to_status }}</p>
            <p class="mt-1 text-sm text-ink-600">{{ p.citation }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <FnButton size="sm" :disabled="deciding === p.id" @click="decide(p.id, true)">{{
              t("responses.accept")
            }}</FnButton>
            <FnButton
              size="sm"
              tone="quiet"
              :disabled="deciding === p.id"
              @click="decide(p.id, false)"
              >{{ t("responses.reject") }}</FnButton
            >
          </div>
        </li>
        <li v-if="!(proposals.data.value ?? []).length" class="py-6 text-sm text-ink-600">
          {{ t("responses.emptyProposals") }}
        </li>
      </ul>
    </section>

    <section
      class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-6 shadow-[var(--shadow-card)]"
    >
      <h2 class="text-sm font-semibold tracking-wide text-ink-600 uppercase">
        {{ t("responses.paste") }}
      </h2>
      <FnInput
        v-model="form.application_id"
        :placeholder="t('responses.appId')"
        :aria-label="t('responses.appId')"
      />
      <FnInput
        v-model="form.subject"
        :placeholder="t('responses.subject')"
        :aria-label="t('responses.subject')"
      />
      <FnTextarea
        v-model="form.body_text"
        :rows="6"
        :placeholder="t('responses.body')"
        :aria-label="t('responses.body')"
      />
      <div class="flex items-center gap-2">
        <FnButton tone="primary" :disabled="ingesting || !form.body_text.trim()" @click="ingest">{{
          t("responses.classify")
        }}</FnButton>
        <FnChip v-if="form.application_id" tone="neutral">app</FnChip>
      </div>
    </section>
  </div>
</template>
