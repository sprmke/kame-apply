<script setup lang="ts">
import {
  addWorkspaceIndustryApiV1WorkspaceIndustriesPost,
  createSetupApiV1OnboardingSetupsPost,
  createWorkspaceApiV1WorkspacesPost,
  listIndustriesApiV1IndustriesGet,
  listWorkspaceIndustriesApiV1WorkspaceIndustriesGet,
  removeWorkspaceIndustryApiV1WorkspaceIndustriesKeyDelete,
  uploadDocumentApiV1ProfilesProfileIdDocumentsPost,
  type IndustrySummary,
} from "@kame/api-client";
import { FnButton, FnDialog, FnField, FnInput, FnSkeleton, useToast } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { useExperience } from "~/composables/useExperience";
import { ok } from "~/lib/api";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const open = defineModel<boolean>("open", { default: false });
const ws = useWorkspaceStore();
const exp = useExperience();
const toast = useToast();
const apiError = useApiError();
const { ensureProfile } = useActiveProfile();
const name = ref("");
const file = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const step = ref<0 | 1 | 2>(0);
const selected = ref<string[]>([]);
const primary = ref<string | null>(null);
const busy = ref(false);
const error = ref<string | null>(null);

const industries = useQuery({
  queryKey: ["industries"],
  queryFn: async () => {
    const { data } = await listIndustriesApiV1IndustriesGet({ throwOnError: true });
    return (data?.items ?? []) as IndustrySummary[];
  },
  enabled: computed(() => open.value),
});
const options = computed(() => industries.data.value ?? []);

watch(open, (o) => {
  if (o) {
    name.value = "";
    file.value = null;
    step.value = 0;
    selected.value = [];
    primary.value = null;
    error.value = null;
  }
});

function next() {
  if (!name.value.trim()) {
    error.value = t("validation.required");
    return;
  }
  error.value = null;
  step.value = 1;
}

function toResume() {
  error.value = null;
  step.value = 2;
}

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null;
}

async function submit() {
  busy.value = true;
  error.value = null;
  try {
    const data = await ok(createWorkspaceApiV1WorkspacesPost({ body: { name: name.value } }));
    await ws.load();
    ws.select(data.id);
    const chosen = selected.value.filter((key) => key !== "general");
    const current = await listWorkspaceIndustriesApiV1WorkspaceIndustriesGet({
      throwOnError: true,
    });
    for (const row of current.data?.items ?? []) {
      if (row.key === "general" || chosen.includes(row.key)) continue;
      await removeWorkspaceIndustryApiV1WorkspaceIndustriesKeyDelete({
        path: { key: row.key },
        throwOnError: true,
      }).catch(() => null);
    }
    for (const [index, key] of chosen.entries()) {
      await addWorkspaceIndustryApiV1WorkspaceIndustriesPost({
        body: { key, is_primary: index === 0 },
        throwOnError: true,
      });
    }
    await exp.refresh();
    open.value = false;
    toast.push({ title: t("workspace.created"), tone: "success" });
    if (!file.value) {
      await navigateTo("/");
      return;
    }
    const profileId = await ensureProfile();
    const upload = await uploadDocumentApiV1ProfilesProfileIdDocumentsPost({
      path: { profile_id: profileId },
      body: { file: file.value, kind: "resume_upload" },
      throwOnError: true,
    });
    if (!upload.data?.extracted_text) {
      toast.push({ title: t("setup.fileUnreadable"), tone: "danger" });
      await navigateTo("/start");
      return;
    }
    const setup = await createSetupApiV1OnboardingSetupsPost({
      body: {
        document_id: upload.data.id,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      },
      throwOnError: true,
    });
    await navigateTo(setup.data?.id ? `/start?setup=${setup.data.id}` : "/start");
  } catch (e) {
    error.value = apiError(e);
  } finally {
    busy.value = false;
    if (fileInput.value) fileInput.value.value = "";
  }
}
</script>

<template>
  <FnDialog
    v-model:open="open"
    :title="t('workspace.create')"
    size="lg"
    :close-label="t('common.close')"
  >
    <form
      class="flex flex-col gap-4"
      novalidate
      @submit.prevent="step === 0 ? next() : step === 1 ? toResume() : submit()"
    >
      <p class="text-xs font-semibold tracking-wide text-ink-600 uppercase">
        {{ t("workspace.step", { n: step + 1 }) }}
      </p>

      <template v-if="step === 0">
        <FnField v-slot="{ id, describedby, invalid }" :label="t('workspace.name')" :error="error">
          <FnInput
            :id="id"
            v-model="name"
            :describedby="describedby"
            :invalid="invalid"
            autocomplete="off"
          />
        </FnField>
        <div class="flex justify-end gap-2">
          <FnButton @click="open = false">{{ t("common.cancel") }}</FnButton>
          <FnButton type="submit" tone="primary">{{ t("workspace.next") }}</FnButton>
        </div>
      </template>

      <template v-else-if="step === 1">
        <div class="flex flex-col gap-2">
          <p class="text-sm font-semibold text-ink-900">{{ t("workspace.pickField") }}</p>
          <div v-if="industries.isPending.value" class="grid gap-2 sm:grid-cols-2">
            <FnSkeleton v-for="n in 4" :key="n" class="h-16 w-full" />
          </div>
          <IndustryPicker
            v-else
            v-model:selected="selected"
            v-model:primary="primary"
            :industries="options"
            :disabled="busy"
          />
          <p class="text-xs text-ink-600">{{ t("workspace.pickFieldHint") }}</p>
          <p v-if="selected.length >= 2" class="text-xs text-ink-600">
            {{ t("workspace.limitTwo") }}
          </p>
        </div>
        <p v-if="error" role="alert" class="text-sm text-oxblood-600">{{ error }}</p>
        <div class="flex flex-wrap justify-between gap-2">
          <FnButton :disabled="busy" @click="step = 0">{{ t("workspace.back") }}</FnButton>
          <FnButton type="submit" tone="primary">{{ t("workspace.next") }}</FnButton>
        </div>
      </template>

      <template v-else>
        <div class="flex flex-col gap-1">
          <p class="text-sm font-semibold text-ink-900">{{ t("setup.workspaceResumeTitle") }}</p>
          <p class="text-sm text-ink-600">{{ t("setup.workspaceResumeBody") }}</p>
        </div>
        <input
          ref="fileInput"
          type="file"
          accept=".pdf,.docx,.txt,.md"
          class="sr-only"
          @change="onFile"
        />
        <div class="flex flex-wrap items-center gap-2">
          <FnButton tone="quiet" :disabled="busy" @click="fileInput?.click()">
            {{ file ? file.name : t("setup.upload") }}
          </FnButton>
          <span v-if="file" class="text-sm text-ink-600">{{
            t("setup.workspaceResumeReady")
          }}</span>
        </div>
        <p v-if="error" role="alert" class="text-sm text-oxblood-600">{{ error }}</p>
        <div class="flex flex-wrap justify-between gap-2">
          <FnButton :disabled="busy" @click="step = 1">{{ t("workspace.back") }}</FnButton>
          <FnButton type="submit" tone="primary" :loading="busy">
            {{ t("setup.workspaceCreate") }}
          </FnButton>
        </div>
      </template>
    </form>
  </FnDialog>
</template>
