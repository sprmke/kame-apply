<script setup lang="ts">
import { ok } from "~/lib/api";
import {
  createSetupApiV1OnboardingSetupsPost,
  createWorkspaceApiV1WorkspacesPost,
  uploadDocumentApiV1ProfilesProfileIdDocumentsPost,
} from "@kame/api-client";
import { FnButton, FnDialog, FnField, FnInput, useToast } from "@kame/ui";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const open = defineModel<boolean>("open", { default: false });
const ws = useWorkspaceStore();
const toast = useToast();
const apiError = useApiError();
const { ensureProfile } = useActiveProfile();
const name = ref("");
const file = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const step = ref<1 | 2>(1);
const busy = ref(false);
const error = ref<string | null>(null);

watch(open, (o) => {
  if (o) {
    name.value = "";
    file.value = null;
    step.value = 1;
    error.value = null;
  }
});

function next() {
  if (!name.value.trim()) {
    error.value = t("validation.required");
    return;
  }
  error.value = null;
  step.value = 2;
}

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null;
}

async function submit(withResume: boolean) {
  busy.value = true;
  error.value = null;
  try {
    const data = await ok(createWorkspaceApiV1WorkspacesPost({ body: { name: name.value } }));
    await ws.load();
    ws.select(data.id);
    open.value = false;
    toast.push({ title: t("workspace.created"), tone: "success" });
    if (!withResume || !file.value) {
      await navigateTo("/start");
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
  <FnDialog v-model:open="open" :title="t('workspace.create')" :close-label="t('common.close')">
    <div v-if="step === 1" class="flex flex-col gap-4">
      <FnField v-slot="{ id, describedby, invalid }" :label="t('workspace.name')" :error="error">
        <FnInput
          :id="id"
          v-model="name"
          :describedby="describedby"
          :invalid="invalid"
          autocomplete="off"
          @keyup.enter="next"
        />
      </FnField>
      <div class="flex justify-end gap-2">
        <FnButton @click="open = false">{{ t("common.cancel") }}</FnButton>
        <FnButton tone="primary" @click="next">{{ t("common.continue") }}</FnButton>
      </div>
    </div>

    <div v-else class="flex flex-col gap-4">
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
        <FnButton tone="quiet" @click="fileInput?.click()">
          {{ file ? file.name : t("setup.upload") }}
        </FnButton>
        <span v-if="file" class="text-sm text-ink-600">{{ t("setup.workspaceResumeReady") }}</span>
      </div>
      <p v-if="error" role="alert" class="text-sm text-oxblood-600">{{ error }}</p>
      <p class="text-sm text-ink-600">{{ t("setup.workspaceNoFile") }}</p>
      <div class="flex flex-wrap justify-end gap-2">
        <FnButton tone="primary" :loading="busy" @click="submit(Boolean(file))">
          {{ t("setup.workspaceCreate") }}
        </FnButton>
      </div>
    </div>
  </FnDialog>
</template>
