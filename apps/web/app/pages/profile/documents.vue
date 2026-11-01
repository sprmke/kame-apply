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
  <div class="flex flex-col gap-4">
    <div>
      <FnButton tone="primary" @click="navigateTo('/profile/onboarding')">{{
        t("career.upload")
      }}</FnButton>
    </div>
    <div v-if="docsLoading" class="flex flex-col gap-2">
      <FnSkeleton class="h-12 w-full" />
    </div>
    <p v-else-if="!docRows.length" class="text-sm text-ink-600">
      {{ t("career.emptyDocs") }}
    </p>
    <ul v-else class="divide-y divide-rule border-y border-rule">
      <li
        v-for="doc in docRows"
        :key="doc.id"
        class="flex min-h-14 flex-wrap items-center gap-3 py-2"
      >
        <div class="min-w-0 flex-1">
          <p class="truncate font-medium text-ink-900">{{ doc.filename }}</p>
          <p class="font-mono text-xs text-ink-600">{{ doc.mime }} · {{ doc.size_bytes }} B</p>
        </div>
        <FnChip>{{ doc.status }}</FnChip>
        <NuxtLink
          v-if="doc.status === 'ready'"
          :to="`/profile/review/${doc.id}`"
          class="text-sm text-ink-900 underline-offset-2 hover:underline"
          >{{ t("career.review") }}</NuxtLink
        >
        <FnButton size="sm" tone="danger" @click="remove(doc)">{{ t("common.delete") }}</FnButton>
      </li>
    </ul>
  </div>
</template>
