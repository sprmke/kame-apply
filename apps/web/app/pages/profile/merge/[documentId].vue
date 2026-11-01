<script setup lang="ts">
import { useActiveProfile } from "~/composables/useActiveProfile";
import {
  mergePreviewApiV1ProfilesProfileIdDocumentsDocumentIdMergeGet,
  mergeResolveApiV1ProfilesProfileIdDocumentsDocumentIdMergePost,
} from "@kame/api-client";
import { FnButton, FnSkeleton, useToast } from "@kame/ui";

const { t } = useI18n();
const route = useRoute();
const toast = useToast();
const apiError = useApiError();
const { ensureProfile, refresh } = useActiveProfile();
const preview = ref<Record<string, unknown> | null>(null);
const busy = ref(false);
const documentId = computed(() => String(route.params.documentId));

onMounted(async () => {
  try {
    const pid = await ensureProfile();
    const { data } = await mergePreviewApiV1ProfilesProfileIdDocumentsDocumentIdMergeGet({
      path: { profile_id: pid, document_id: documentId.value },
      throwOnError: true,
    });
    preview.value = data as Record<string, unknown>;
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
});

async function resolveAllTakeIncoming() {
  if (!preview.value) return;
  busy.value = true;
  try {
    const pid = await ensureProfile();
    const conflicts = (preview.value.conflicts as { id: string }[]) ?? [];
    const additions = (preview.value.additions as { id: string }[]) ?? [];
    const header = (preview.value.header_conflicts as { field: string }[]) ?? [];
    await mergeResolveApiV1ProfilesProfileIdDocumentsDocumentIdMergePost({
      path: { profile_id: pid, document_id: documentId.value },
      body: {
        resolutions: conflicts.map((c) => ({ id: c.id, action: "take_incoming" as const })),
        additions: additions.map((a) => ({ id: a.id, action: "add" as const })),
        header: header.map((h) => ({ field: h.field, action: "take_incoming" as const })),
        bullet_actions: [],
      },
      throwOnError: true,
    });
    await refresh();
    toast.push({ title: t("career.merged"), tone: "success" });
    await navigateTo("/profile");
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6">
    <PageHeader :title="t('career.mergeTitle')" />
    <div v-if="!preview">
      <FnSkeleton class="h-32 w-full" />
    </div>
    <template v-else>
      <p class="text-sm text-ink-600">
        {{
          t("career.mergeSummary", {
            n: (preview.summary as { conflicts?: number })?.conflicts ?? 0,
          })
        }}
      </p>
      <ul class="divide-y divide-rule border-y border-rule text-sm">
        <li
          v-for="c in (preview.conflicts as { id: string; label?: string }[]) ?? []"
          :key="c.id"
          class="py-2"
        >
          {{ c.label || c.id }}
        </li>
      </ul>
      <FnButton tone="primary" :loading="busy" @click="resolveAllTakeIncoming">{{
        t("career.takeIncoming")
      }}</FnButton>
    </template>
  </div>
</template>
