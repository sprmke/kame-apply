<script setup lang="ts">
import { useActiveProfile } from "~/composables/useActiveProfile";
import {
  confirmDocumentApiV1ProfilesProfileIdDocumentsDocumentIdConfirmPost,
  getDocumentApiV1ProfilesProfileIdDocumentsDocumentIdGet,
  mergePreviewApiV1ProfilesProfileIdDocumentsDocumentIdMergeGet,
  parseDocumentApiV1ProfilesProfileIdDocumentsDocumentIdParsePost,
  type DocumentRead,
} from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton, FnPencilText, useToast } from "@kame/ui";
import { errorCode } from "~/lib/errors";

const { t } = useI18n();
const route = useRoute();
const toast = useToast();
const apiError = useApiError();
const { profileId, ensureProfile, refresh } = useActiveProfile();
const doc = ref<DocumentRead | null>(null);
const busy = ref(false);
const mergeNeeded = ref(false);
const parseError = ref<{ code?: string; message: string } | null>(null);
const lowPaths = computed(
  () => (doc.value?.parse_quality?.low_confidence_paths as string[] | undefined) ?? [],
);
type ParsedDraft = {
  display_name?: { value?: string };
  headline?: { value?: string };
  experiences?: Array<{
    title?: string;
    company?: string;
    bullets?: Array<{ text?: string }>;
  }>;
};
const parsed = computed(() => (doc.value?.parsed ?? null) as ParsedDraft | null);

const documentId = computed(() => String(route.params.documentId));

async function load() {
  const pid = await ensureProfile();
  const { data } = await getDocumentApiV1ProfilesProfileIdDocumentsDocumentIdGet({
    path: { profile_id: pid, document_id: documentId.value },
    throwOnError: true,
  });
  doc.value = data!;
}

onMounted(async () => {
  try {
    await load();
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
});

async function runParse() {
  if (!profileId.value || !doc.value) return;
  busy.value = true;
  parseError.value = null;
  try {
    const { data } = await parseDocumentApiV1ProfilesProfileIdDocumentsDocumentIdParsePost({
      path: { profile_id: profileId.value, document_id: doc.value.id },
      throwOnError: true,
    });
    doc.value = data!;
  } catch (e) {
    parseError.value = { code: errorCode(e), message: apiError(e) };
  } finally {
    busy.value = false;
  }
}

async function confirm() {
  if (!profileId.value || !doc.value) return;
  busy.value = true;
  try {
    await confirmDocumentApiV1ProfilesProfileIdDocumentsDocumentIdConfirmPost({
      path: { profile_id: profileId.value, document_id: doc.value.id },
      body: { apply_header: true },
      throwOnError: true,
    });
    await refresh();
    toast.push({ title: t("career.confirmed"), tone: "success" });
    await navigateTo("/profile");
  } catch (e: unknown) {
    const code = errorCode(e);
    if (code === "merge_required" || apiError(e).includes("merge")) {
      mergeNeeded.value = true;
      try {
        await mergePreviewApiV1ProfilesProfileIdDocumentsDocumentIdMergeGet({
          path: { profile_id: profileId.value, document_id: doc.value.id },
          throwOnError: true,
        });
      } catch {
        /* preview optional */
      }
      toast.push({ title: t("career.mergeRequired"), tone: "danger" });
    } else {
      toast.push({ title: apiError(e), tone: "danger" });
    }
  } finally {
    busy.value = false;
  }
}

function isLow(path: string) {
  return lowPaths.value.some((p) => p === path || p.startsWith(path));
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-4 px-4 py-6 md:px-6">
    <PageHeader :title="t('career.reviewTitle')" />
    <div v-if="!doc" class="flex flex-col gap-2">
      <FnSkeleton class="h-40 w-full" />
    </div>
    <template v-else>
      <div class="flex flex-wrap gap-2">
        <FnButton v-if="!doc.parsed" tone="primary" :loading="busy" @click="runParse">{{
          t("career.parse")
        }}</FnButton>
        <FnButton
          v-if="doc.parsed && !mergeNeeded"
          tone="primary"
          :loading="busy"
          @click="confirm"
          >{{ t("career.confirm") }}</FnButton
        >
        <FnButton
          v-if="mergeNeeded"
          tone="primary"
          @click="navigateTo(`/profile/merge/${doc.id}`)"
          >{{ t("career.openMerge") }}</FnButton
        >
      </div>
      <div
        v-if="parseError"
        role="alert"
        class="flex flex-wrap items-center gap-2 border border-saffron-600 bg-paper-1 p-3 text-sm"
      >
        <span class="text-ink-900">{{ parseError.message }}</span>
        <NuxtLink
          v-if="parseError.code === 'ai_not_configured'"
          to="/settings/ai"
          class="text-persimmon-700 underline"
          >{{ t("settings.ai") }}</NuxtLink
        >
      </div>
      <div class="grid gap-6 lg:grid-cols-2">
        <section class="flex flex-col gap-2">
          <h2 class="text-sm font-medium text-ink-600 uppercase">{{ t("career.original") }}</h2>
          <pre
            class="max-h-[70vh] overflow-auto rounded-sm border border-rule bg-paper-0 p-3 font-mono text-xs whitespace-pre-wrap text-ink-900"
            >{{ doc.extracted_text }}</pre>
        </section>
        <section class="flex flex-col gap-3">
          <h2 class="text-sm font-medium text-ink-600 uppercase">{{ t("career.parsed") }}</h2>
          <p v-if="!parsed" class="text-sm text-ink-600">{{ t("career.parseFirst") }}</p>
          <template v-else>
            <div class="flex flex-col gap-1">
              <p class="font-serif text-xl font-semibold">
                <FnPencilText :state="isLow('display_name') ? 'draft' : 'ink'">{{
                  parsed.display_name?.value
                }}</FnPencilText>
              </p>
              <p class="text-ink-600">
                <FnPencilText :state="isLow('headline') ? 'draft' : 'ink'">{{
                  parsed.headline?.value
                }}</FnPencilText>
              </p>
            </div>
            <div
              v-for="(exp, i) in parsed.experiences ?? []"
              :key="i"
              class="border-t border-rule py-3"
            >
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="font-medium">
                  <FnPencilText :state="isLow(`experiences.${i}`) ? 'draft' : 'ink'"
                    >{{ exp.title }} · {{ exp.company }}</FnPencilText
                  >
                </h3>
                <FnChip v-if="isLow(`experiences.${i}`)" tone="pencil">{{
                  t("career.lowConfidence")
                }}</FnChip>
              </div>
              <ul class="mt-2 list-disc space-y-1 pl-5 text-sm">
                <li v-for="(b, j) in exp.bullets ?? []" :key="j">
                  <FnPencilText :state="isLow(`experiences.${i}.bullets.${j}`) ? 'draft' : 'ink'">{{
                    b.text
                  }}</FnPencilText>
                </li>
              </ul>
            </div>
          </template>
        </section>
      </div>
    </template>
  </div>
</template>
