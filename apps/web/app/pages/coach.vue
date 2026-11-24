<script setup lang="ts">
import {
  client,
  createSetupApiV1OnboardingSetupsPost,
  uploadDocumentApiV1ProfilesProfileIdDocumentsPost,
} from "@kame/api-client";
import {
  FnButton,
  FnEmptyState,
  FnInput,
  FnSectionCard,
  FnSkeleton,
  FnSkeletonGroup,
  useToast,
} from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { useWorkspaceStore } from "~/stores/workspace";

type CoachRow = {
  id: string;
  display_name: string;
  headline: string | null;
  is_default: boolean;
  application_count: number;
};

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const { selectProfile } = useActiveProfile();
const creating = ref(false);
const newName = ref("");
const fileInput = ref<HTMLInputElement | null>(null);
const resumeStarting = ref(false);

const coach = useQuery({
  queryKey: computed(() => ["coach-profiles", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({ url: "/api/v1/coach/profiles", throwOnError: true });
    return data as CoachRow[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

async function openProfile(id: string) {
  selectProfile(id);
  await navigateTo("/profile");
}

async function startFromResume(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  resumeStarting.value = true;
  let createdProfile: string | null = null;
  try {
    const { data: profile } = await client.post({
      url: "/api/v1/profiles",
      body: { display_name: "New person" },
      throwOnError: true,
    });
    const profileId = (profile as { id: string }).id;
    createdProfile = profileId;
    const upload = await uploadDocumentApiV1ProfilesProfileIdDocumentsPost({
      path: { profile_id: profileId },
      body: { file, kind: "resume_upload" },
      throwOnError: true,
    });
    if (!upload.data?.extracted_text) {
      toast.push({ title: t("setup.fileUnreadable"), tone: "danger" });
      return;
    }
    const setup = await createSetupApiV1OnboardingSetupsPost({
      body: {
        document_id: upload.data.id,
        profile_id: profileId,
        subject: "other_person",
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["coach-profiles", ws.currentId] });
    await qc.invalidateQueries({ queryKey: ["profiles", ws.currentId] });
    if (setup.data?.id) await navigateTo(`/start?setup=${setup.data.id}`);
  } catch (e) {
    if (createdProfile) {
      await client
        .delete({ url: `/api/v1/profiles/${createdProfile}`, throwOnError: true })
        .catch(() => undefined);
      await qc.invalidateQueries({ queryKey: ["profiles", ws.currentId] });
    }
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    resumeStarting.value = false;
    if (fileInput.value) fileInput.value.value = "";
  }
}

async function addProfile() {
  const name = newName.value.trim();
  if (!name) return;
  creating.value = true;
  try {
    const { data } = await client.post({
      url: "/api/v1/profiles",
      body: { display_name: name },
      throwOnError: true,
    });
    selectProfile((data as { id: string }).id);
    newName.value = "";
    await qc.invalidateQueries({ queryKey: ["coach-profiles", ws.currentId] });
    await qc.invalidateQueries({ queryKey: ["profiles", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    creating.value = false;
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-8">
    <PageHeader :title="t('coach.title')" :lede="t('coach.lede')" />

    <FnSkeletonGroup v-if="coach.isPending.value" :label="t('common.loading')">
      <ul
        class="divide-y divide-rule overflow-hidden rounded-xl border border-rule bg-paper-1 shadow-[var(--shadow-card)]"
      >
        <li
          v-for="n in 3"
          :key="n"
          class="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
        >
          <div class="flex min-w-0 flex-1 flex-col gap-2">
            <FnSkeleton class="h-4 w-2/5" />
            <FnSkeleton class="h-3.5 w-3/5" />
          </div>
          <FnSkeleton class="h-4 w-20" />
          <FnSkeleton class="h-11 w-20 rounded-md" />
        </li>
      </ul>
    </FnSkeletonGroup>
    <FnEmptyState
      v-else-if="!(coach.data.value ?? []).length"
      :title="t('coach.empty')"
      :body="t('coach.emptyBody')"
    />
    <ul
      v-else
      class="divide-y divide-rule overflow-hidden rounded-xl border border-rule bg-paper-1 shadow-[var(--shadow-card)]"
    >
      <li
        v-for="row in coach.data.value ?? []"
        :key="row.id"
        class="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
      >
        <button
          type="button"
          class="min-w-0 flex-1 rounded-md px-2 py-1 text-left hover:bg-paper-2"
          @click="openProfile(row.id)"
        >
          <span class="font-medium text-ink-900">{{ row.display_name }}</span>
          <span v-if="row.headline" class="mt-0.5 block text-sm text-ink-600">{{
            row.headline
          }}</span>
        </button>
        <span class="text-sm tabular-nums text-ink-600"
          >{{ row.application_count }} {{ t("coach.apps") }}</span
        >
        <FnButton size="sm" tone="quiet" @click="openProfile(row.id)">{{
          t("coach.open")
        }}</FnButton>
      </li>
    </ul>

    <FnSectionCard :title="t('coach.add')" :intro="t('setup.coachHint')">
      <div class="mb-3 flex flex-wrap gap-2">
        <input
          ref="fileInput"
          type="file"
          accept=".pdf,.docx,.txt,.md"
          class="sr-only"
          @change="startFromResume"
        />
        <FnButton tone="quiet" :loading="resumeStarting" @click="fileInput?.click()">{{
          t("coach.startFromResume")
        }}</FnButton>
      </div>
      <form class="flex flex-col gap-3 sm:flex-row" @submit.prevent="addProfile">
        <FnInput
          v-model="newName"
          type="text"
          class="flex-1"
          :placeholder="t('coach.namePlaceholder')"
          :aria-label="t('coach.namePlaceholder')"
        />
        <FnButton type="submit" tone="primary" :disabled="creating || !newName.trim()">{{
          t("coach.add")
        }}</FnButton>
      </form>
    </FnSectionCard>
  </div>
</template>
