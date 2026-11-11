<script setup lang="ts">
import { useActiveProfile } from "~/composables/useActiveProfile";
import {
  deleteDocumentApiV1ProfilesProfileIdDocumentsDocumentIdDelete,
  listDocumentsApiV1ProfilesProfileIdDocumentsGet,
  type DocumentListItem,
} from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const qc = useQueryClient();
const { profileId, ensureProfile } = useActiveProfile();

onMounted(() => ensureProfile().catch((e) => toast.push({ title: apiError(e), tone: "danger" })));

const docs = useQuery({
  queryKey: computed(() => ["documents", profileId.value]),
  queryFn: async () => {
    const { data } = await listDocumentsApiV1ProfilesProfileIdDocumentsGet({
      path: { profile_id: profileId.value! },
      throwOnError: true,
    });
    return (data ?? []) as DocumentListItem[];
  },
  enabled: computed(() => Boolean(profileId.value)),
});
const docRows = computed(() => docs.data.value ?? []);
const docsLoading = computed(
  () => docs.isPending.value || (docs.isFetching.value && !docs.data.value),
);

function sizeLabel(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function statusLabel(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

async function remove(doc: DocumentListItem) {
  if (!profileId.value) return;
  if (!window.confirm(t("career.deleteDocConfirm"))) return;
  try {
    await deleteDocumentApiV1ProfilesProfileIdDocumentsDocumentIdDelete({
      path: { profile_id: profileId.value, document_id: doc.id },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["documents", profileId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-col gap-1">
      <h2 class="text-xl font-bold text-ink-900">{{ t("career.tabs.documents") }}</h2>
      <p class="max-w-2xl text-sm leading-6 text-ink-600">{{ t("career.documentsLede") }}</p>
    </div>
    <div>
      <FnButton tone="primary" @click="navigateTo('/profile/onboarding')">{{
        t("career.upload")
      }}</FnButton>
    </div>
    <div v-if="docsLoading" class="flex flex-col gap-2">
      <FnSkeleton class="h-12 w-full" />
    </div>
    <div
      v-else-if="!docRows.length"
      class="flex flex-col items-start gap-2 rounded-xl border border-dashed border-rule bg-paper-0 p-6"
    >
      <p class="font-semibold text-ink-900">{{ t("career.emptyDocs") }}</p>
      <p class="max-w-lg text-sm leading-6 text-ink-600">{{ t("career.emptyDocsHint") }}</p>
    </div>
    <ul v-else class="divide-y divide-rule border-y border-rule">
      <li
        v-for="doc in docRows"
        :key="doc.id"
        class="flex min-h-14 flex-wrap items-center gap-3 py-3"
      >
        <div class="min-w-0 flex-1">
          <p class="truncate font-medium text-ink-900">{{ doc.filename }}</p>
          <p class="text-xs text-ink-600">{{ sizeLabel(doc.size_bytes) }}</p>
        </div>
        <FnChip>{{ statusLabel(doc.status) }}</FnChip>
        <FnButton v-if="doc.status === 'ready'" as-child size="sm" tone="quiet">
          <NuxtLink :to="`/profile/review/${doc.id}`">{{ t("career.review") }}</NuxtLink>
        </FnButton>
        <FnButton size="sm" tone="danger" @click="remove(doc)">{{ t("common.delete") }}</FnButton>
      </li>
    </ul>
  </div>
</template>
