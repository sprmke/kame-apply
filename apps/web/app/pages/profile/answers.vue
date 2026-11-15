<script setup lang="ts">
import { useActiveProfile } from "~/composables/useActiveProfile";
import {
  createAnswerApiV1ProfilesProfileIdAnswersPost,
  draftAnswersApiV1ProfilesProfileIdAnswersDraftPost,
  listAnswersApiV1ProfilesProfileIdAnswersGet,
  listAnswerKeysApiV1ProfilesProfileIdAnswersKeysGet,
  setupAnswersApiV1ProfilesProfileIdAnswersSetupPost,
  updateAnswerApiV1ProfilesProfileIdAnswersAnswerIdPatch,
  type AnswerDraftRead,
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
const drafting = ref(false);
const drafts = ref<AnswerDraftRead[]>([]);

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

function groupLabel(group: string): string {
  return group.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
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

function sourceLabel(item: AnswerDraftRead): string {
  if (item.source === "profile") return t("career.draftFromProfile");
  if (item.source === "default") return t("career.draftDefault");
  return item.message || t("career.draftNeedsYou");
}

async function draftFromProfile() {
  if (!profileId.value) return;
  drafting.value = true;
  try {
    const { data } = await draftAnswersApiV1ProfilesProfileIdAnswersDraftPost({
      path: { profile_id: profileId.value },
      body: {},
      throwOnError: true,
    });
    drafts.value = (data?.items ?? []) as AnswerDraftRead[];
    if (!drafts.value.length) toast.push({ title: t("career.draftNone"), tone: "neutral" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    drafting.value = false;
  }
}

async function useDraft(item: AnswerDraftRead) {
  if (!profileId.value || !item.draft) return;
  try {
    await createAnswerApiV1ProfilesProfileIdAnswersPost({
      path: { profile_id: profileId.value },
      body: {
        key: item.key,
        country: item.country ?? null,
        answer: item.draft,
        approved: true,
      },
      throwOnError: true,
    });
    drafts.value = drafts.value.filter((row) => row !== item);
    await qc.invalidateQueries({ queryKey: ["answers", profileId.value] });
    toast.push({ title: t("common.saved"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
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
  <div class="flex flex-col gap-6">
    <div class="flex flex-col gap-1">
      <h2 class="text-xl font-bold text-ink-900">{{ t("career.tabs.answers") }}</h2>
      <p class="max-w-2xl text-sm leading-6 text-ink-600">{{ t("career.answersLede") }}</p>
    </div>
    <FilledFromResume page="answers" :control="t('setup.control.answers')" />
    <div class="flex flex-wrap items-center gap-2">
      <FnInput
        v-model="q"
        class="max-w-sm"
        :aria-label="t('career.search')"
        :placeholder="t('career.searchAnswers')"
      />
      <FnButton tone="primary" :loading="busy" @click="runSetup">{{
        t("career.quickSetup")
      }}</FnButton>
      <FnButton tone="quiet" :loading="drafting" @click="draftFromProfile">{{
        t("career.draftAnswers")
      }}</FnButton>
    </div>
    <p class="-mt-3 text-sm text-ink-600">{{ t("career.quickSetupHint") }}</p>

    <section v-if="drafts.length" class="flex flex-col gap-2">
      <h3 class="text-sm font-semibold tracking-wide text-ink-600 uppercase">
        {{ t("career.draftTitle") }}
      </h3>
      <ul class="flex flex-col gap-2">
        <li
          v-for="item in drafts"
          :key="`${item.key}-${item.country}`"
          class="flex flex-col gap-2 rounded-lg border border-dashed border-pencil bg-paper-0 p-3"
        >
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-medium text-ink-900">{{ item.label }}</span>
            <span v-if="item.country" class="text-xs text-ink-600">{{ item.country }}</span>
          </div>
          <p v-if="item.draft" class="text-sm text-pencil">{{ item.draft }}</p>
          <p class="text-xs text-ink-600">{{ sourceLabel(item) }}</p>
          <div class="flex flex-wrap gap-2">
            <FnButton v-if="item.draft" size="sm" tone="primary" @click="useDraft(item)">{{
              t("career.useDraft")
            }}</FnButton>
            <FnButton
              size="sm"
              tone="ghost"
              @click="drafts = drafts.filter((row) => row !== item)"
              >{{ t("common.dismiss") }}</FnButton
            >
          </div>
        </li>
      </ul>
    </section>

    <p v-if="drafting" class="text-sm text-ink-600">{{ t("career.drafting") }}</p>
    <div v-if="answersLoading" class="flex flex-col gap-2">
      <FnSkeleton class="h-16 w-full" />
      <FnSkeleton class="h-16 w-full" />
    </div>
    <div
      v-else-if="!answerRows.length"
      class="flex flex-col items-start gap-2 rounded-xl border border-dashed border-rule bg-paper-0 p-6"
    >
      <p class="font-semibold text-ink-900">{{ t("career.emptyAnswersTitle") }}</p>
      <p class="max-w-lg text-sm leading-6 text-ink-600">{{ t("career.answersEmptyHint") }}</p>
    </div>
    <section v-for="[group, rows] in byGroup" :key="group" class="flex flex-col gap-3">
      <h3 class="text-sm font-semibold tracking-wide text-ink-400 uppercase">
        {{ groupLabel(group) }}
      </h3>
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
