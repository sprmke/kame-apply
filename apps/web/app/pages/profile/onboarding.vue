<script setup lang="ts">
import { useActiveProfile } from "~/composables/useActiveProfile";
import {
  listCredentialsApiV1AiCredentialsGet,
  uploadDocumentApiV1ProfilesProfileIdDocumentsPost,
} from "@kame/api-client";
import { FnButton, FnTextarea, useToast } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const { ensureProfile } = useActiveProfile();
const ws = useWorkspaceStore();
const { data: creds, isPending: credsLoading } = useQuery({
  queryKey: computed(() => ["onboarding-credentials", ws.currentId]),
  queryFn: async () => (await listCredentialsApiV1AiCredentialsGet()).data ?? [],
  enabled: computed(() => Boolean(ws.currentId)),
});
const hasKey = computed(() => (creds.value?.length ?? 0) > 0);
const file = ref<File | null>(null);
const paste = ref("");
const busy = ref(false);
const input = ref<HTMLInputElement | null>(null);

function onPick(e: Event) {
  const list = (e.target as HTMLInputElement).files;
  file.value = list?.[0] ?? null;
}

async function upload() {
  busy.value = true;
  try {
    const profileId = await ensureProfile();
    let body: File;
    if (file.value) {
      body = file.value;
    } else if (paste.value.trim().length >= 40) {
      body = new File([paste.value], "paste.txt", { type: "text/plain" });
    } else {
      toast.push({ title: t("career.uploadNeeded"), tone: "danger" });
      return;
    }
    const { data } = await uploadDocumentApiV1ProfilesProfileIdDocumentsPost({
      path: { profile_id: profileId },
      body: { file: body, kind: file.value ? "resume_upload" : "paste" },
      throwOnError: true,
    });
    await navigateTo(`/profile/review/${data!.id}`);
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-xl flex-col gap-6 px-4 py-6">
    <PageHeader :title="t('career.onboardingTitle')" />
    <section class="flex flex-col gap-3">
      <div
        v-if="!credsLoading && !hasKey"
        class="rounded-md border border-saffron-600 bg-paper-1 p-3 text-sm"
      >
        {{ t("career.aiKeyNeeded") }}
        <NuxtLink to="/settings/ai" class="text-brand-700 underline">{{
          t("settings.ai")
        }}</NuxtLink>
      </div>
      <input
        ref="input"
        type="file"
        class="sr-only"
        accept=".pdf,.docx,.txt,.md,.json,application/pdf,text/plain"
        @change="onPick"
      />
      <FnButton tone="quiet" @click="input?.click()">{{
        file ? file.name : t("career.chooseFile")
      }}</FnButton>
      <label class="flex flex-col gap-1 text-sm">
        <span class="text-ink-600">{{ t("career.pasteResume") }}</span>
        <FnTextarea v-model="paste" :rows="8" :aria-label="t('career.pasteResume')" />
      </label>
      <FnButton tone="primary" :loading="busy" @click="upload">{{
        t("career.continueParse")
      }}</FnButton>
    </section>
  </div>
</template>
