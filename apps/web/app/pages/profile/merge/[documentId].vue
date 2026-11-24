<script setup lang="ts">
import { useActiveProfile } from "~/composables/useActiveProfile";
import {
  mergePreviewApiV1ProfilesProfileIdDocumentsDocumentIdMergeGet,
  mergeResolveApiV1ProfilesProfileIdDocumentsDocumentIdMergePost,
} from "@kame/api-client";
import { FnButton, FnSkeleton, FnSkeletonGroup, useToast } from "@kame/ui";

const { t } = useI18n();
const route = useRoute();
const toast = useToast();
const apiError = useApiError();
const { ensureProfile, refresh } = useActiveProfile();
const preview = ref<Record<string, unknown> | null>(null);
const busy = ref(false);
const merged = ref(false);
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
    merged.value = true;
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-5">
    <PageHeader :title="t('career.mergeTitle')" />
    <FnSkeletonGroup v-if="!preview" :label="t('common.loading')" class="flex flex-col gap-5">
      <FnSkeleton class="h-4 w-3/4" />
      <ul class="divide-y divide-rule border-y border-rule">
        <li v-for="n in 4" :key="n" class="flex items-center py-3">
          <FnSkeleton class="h-4 w-2/5" />
        </li>
      </ul>
      <FnSkeleton class="h-12 w-40 rounded-md" />
    </FnSkeletonGroup>
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
      <FnButton v-if="!merged" tone="primary" :loading="busy" @click="resolveAllTakeIncoming">{{
        t("career.takeIncoming")
      }}</FnButton>
      <section
        v-else
        class="flex flex-col gap-3 rounded-xl border border-brand-200 bg-brand-50 p-4"
      >
        <p class="text-sm text-ink-900">{{ t("setup.mergePrompt") }}</p>
        <div class="flex flex-wrap gap-2">
          <FnButton
            tone="primary"
            @click="navigateTo(`/start?mode=update&document=${documentId}`)"
            >{{ t("setup.mergeReview") }}</FnButton
          >
          <FnButton tone="quiet" @click="navigateTo('/profile')">{{
            t("setup.mergeProfileOnly")
          }}</FnButton>
        </div>
      </section>
    </template>
  </div>
</template>
