<script setup lang="ts">
import { useActiveProfile } from "~/composables/useActiveProfile";
import {
  listAnswersApiV1ProfilesProfileIdAnswersGet,
  listAnswerKeysApiV1ProfilesProfileIdAnswersKeysGet,
  setupAnswersApiV1ProfilesProfileIdAnswersSetupPost,
  updateAnswerApiV1ProfilesProfileIdAnswersAnswerIdPatch,
  type AnswerRead,
  type CanonicalKeyRead,
} from "@kame/api-client";
import { FnButton, FnChip, FnInput, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const qc = useQueryClient();
const { profileId, ensureProfile, loading: profileLoading } = useActiveProfile();
const q = ref("");
const busy = ref(false);

onMounted(() => ensureProfile().catch((e) => toast.push({ title: apiError(e), tone: "danger" })));

const answers = useQuery({
  queryKey: computed(() => ["answers", profileId.value, q.value]),
  queryFn: async () => {
    const { data } = await listAnswersApiV1ProfilesProfileIdAnswersGet({
      path: { profile_id: profileId.value! },
      query: q.value ? { q: q.value } : {},
      throwOnError: true,
    });
    return data ?? [];
  },
  enabled: computed(() => Boolean(profileId.value)),
});

const keys = useQuery({
  queryKey: computed(() => ["answer-keys", profileId.value]),
  queryFn: async () => {
    const { data } = await listAnswerKeysApiV1ProfilesProfileIdAnswersKeysGet({
      path: { profile_id: profileId.value! },
      throwOnError: true,
    });
    return data ?? [];
  },
  enabled: computed(() => Boolean(profileId.value)),
});

const answerRows = computed(() => answers.data.value ?? []);
const keyCatalog = computed(() => keys.data.value ?? []);
const answersLoading = computed(
  () =>
    profileLoading.value ||
    answers.isPending.value ||
    (answers.isFetching.value && !answers.data.value),
);
const byGroup = computed(() => {
  const catalog = new Map(keyCatalog.value.map((k) => [k.key, k]));
  const groups = new Map<string, AnswerRead[]>();
  for (const row of answerRows.value) {
    const meta = catalog.get(row.key);
    const g = meta?.group ?? "custom";
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g)!.push(row);
  }
  return [...groups.entries()];
});

function labelFor(key: string, catalog: CanonicalKeyRead[]) {
  return catalog.find((k) => k.key === key)?.label ?? key;
}

async function runSetup() {
  if (!profileId.value) return;
  busy.value = true;
  try {
    await setupAnswersApiV1ProfilesProfileIdAnswersSetupPost({
      path: { profile_id: profileId.value },
      body: { countries: ["US", "PH", "SG"], include_links: true },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["answers", profileId.value] });
    toast.push({ title: t("career.setupDone"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}

async function saveAnswer(row: AnswerRead, text: string, approved: boolean) {
  if (!profileId.value) return;
  try {
    await updateAnswerApiV1ProfilesProfileIdAnswersAnswerIdPatch({
      path: { profile_id: profileId.value, answer_id: row.id },
      body: { answer: text, approved },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["answers", profileId.value] });
    toast.push({ title: t("common.saved"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center gap-2">
      <FnInput
        v-model="q"
        class="max-w-xs"
        :aria-label="t('career.search')"
        :placeholder="t('career.search')"
      />
      <FnButton tone="primary" :loading="busy" @click="runSetup">{{
        t("career.quickSetup")
      }}</FnButton>
    </div>
    <div v-if="answersLoading" class="flex flex-col gap-2">
      <FnSkeleton class="h-16 w-full" />
      <FnSkeleton class="h-16 w-full" />
    </div>
    <p v-else-if="!answerRows.length" class="text-sm text-ink-600">
      {{ t("career.emptyAnswers") }}
    </p>
    <section v-for="[group, rows] in byGroup" :key="group" class="flex flex-col gap-3">
      <h3 class="text-sm font-medium tracking-wide text-ink-600 uppercase">{{ group }}</h3>
      <article
        v-for="row in rows"
        :key="row.id"
        class="flex flex-col gap-2 border-t border-rule py-3"
      >
        <div class="flex flex-wrap items-center gap-2">
          <h4 class="font-medium text-ink-900">
            {{ labelFor(row.key, keyCatalog) }}
            <span v-if="row.country" class="font-mono text-xs text-ink-600">{{ row.country }}</span>
          </h4>
          <FnChip v-if="row.approved" tone="accent">{{ t("career.approved") }}</FnChip>
        </div>
        <AnswerRow :row="row" @save="saveAnswer" />
      </article>
    </section>
  </div>
</template>
