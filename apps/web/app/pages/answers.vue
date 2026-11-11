<script setup lang="ts">
import {
  parseDeskApiV1AnswerDeskParsePost,
  patchItemApiV1AnswerDeskItemsItemIdPatch,
  saveBankApiV1AnswerDeskItemsItemIdSaveToBankPost,
  toneItemApiV1AnswerDeskItemsItemIdTonePost,
  type AppAnswersSchemasSessionRead,
  type ItemRead,
} from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton, useToast } from "@kame/ui";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const route = useRoute();
const { profileId, ensureProfile } = useActiveProfile();
const { waiting: inboxWaiting } = useAgentInboxStatus();

const paste = ref("");
const busy = ref(false);
const session = ref<AppAnswersSchemasSessionRead | null>(null);
const focused = ref(0);
const applicationId = computed(() => (route.query.application as string) || undefined);

onMounted(() => ensureProfile().catch((e) => toast.push({ title: apiError(e), tone: "danger" })));

const items = computed(() => (session.value?.items ?? []) as ItemRead[]);

async function runParse() {
  if (!profileId.value || !paste.value.trim()) return;
  busy.value = true;
  try {
    const { data } = await parseDeskApiV1AnswerDeskParsePost({
      body: {
        text: paste.value,
        profile_id: profileId.value,
        application_id: applicationId.value,
      },
      throwOnError: true,
    });
    session.value = data as AppAnswersSchemasSessionRead;
    focused.value = 0;
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}

async function applyTone(
  id: string,
  tone: "shorter" | "more_specific" | "more_casual" | "more_formal",
) {
  try {
    const { data } = await toneItemApiV1AnswerDeskItemsItemIdTonePost({
      path: { item_id: id },
      body: { tone },
      throwOnError: true,
    });
    const list = session.value?.items ?? [];
    const idx = list.findIndex((i) => i.id === id);
    if (idx >= 0 && data) list[idx] = data as ItemRead;
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function saveDraft(item: ItemRead, text: string) {
  try {
    const { data } = await patchItemApiV1AnswerDeskItemsItemIdPatch({
      path: { item_id: item.id },
      body: { draft: text },
      throwOnError: true,
    });
    const list = session.value?.items ?? [];
    const idx = list.findIndex((i) => i.id === item.id);
    if (idx >= 0 && data) list[idx] = data as ItemRead;
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function saveBank(id: string) {
  try {
    const { data } = await saveBankApiV1AnswerDeskItemsItemIdSaveToBankPost({
      path: { item_id: id },
      body: { approve: true },
      throwOnError: true,
    });
    const list = session.value?.items ?? [];
    const idx = list.findIndex((i) => i.id === id);
    if (idx >= 0 && data) list[idx] = data as ItemRead;
    toast.push({ title: t("answers.savedBank") });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function copyDraft(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.push({ title: t("answers.copied") });
  } catch {
    toast.push({ title: t("answers.copyFailed"), tone: "danger" });
  }
}

function onKey(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "c" && !getSelection()?.toString()) {
    const item = items.value[focused.value];
    if (item?.draft) {
      e.preventDefault();
      void copyDraft(item.draft);
    }
  }
  if (e.key === "Tab" && items.value.length) {
    e.preventDefault();
    const dir = e.shiftKey ? -1 : 1;
    focused.value = (focused.value + dir + items.value.length) % items.value.length;
  }
}

function charCount(item: ItemRead) {
  const n = (item.draft || "").length;
  return item.char_limit ? `${n}/${item.char_limit}` : String(n);
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-6" @keydown="onKey">
    <PageHeader :title="t('nav.answers')" :lede="t('answers.lede')" />
    <WaitingForClaude v-if="inboxWaiting > 0" :waiting="inboxWaiting" />

    <section class="flex flex-col gap-2">
      <label class="text-xs tracking-wide text-ink-600 uppercase" for="desk-paste">{{
        t("answers.paste")
      }}</label>
      <textarea
        id="desk-paste"
        v-model="paste"
        rows="8"
        class="min-h-32 w-full border border-rule bg-paper-0 p-3 text-sm"
        :placeholder="t('answers.placeholder')"
        :disabled="!ws.currentId || busy"
      />
      <div class="flex justify-end gap-2">
        <FnButton
          size="sm"
          tone="primary"
          :disabled="busy || !paste.trim() || !profileId"
          @click="runParse"
          >{{ t("answers.draft") }}</FnButton
        >
      </div>
    </section>

    <div v-if="busy"><FnSkeleton class="h-40 w-full" /></div>

    <ul v-else-if="items.length" class="flex flex-col gap-4">
      <li
        v-for="(item, idx) in items"
        :key="item.id"
        class="border border-rule p-3"
        :class="idx === focused ? 'border-persimmon-700' : ''"
        tabindex="0"
        @focus="focused = idx"
        @click="focused = idx"
      >
        <div class="flex flex-wrap items-start justify-between gap-2">
          <p class="font-medium text-ink-900">{{ item.question }}</p>
          <div class="flex flex-wrap gap-1">
            <FnChip v-if="item.ai_restricted">{{ t("answers.writeYourself") }}</FnChip>
            <FnChip v-else-if="item.from_answer_bank">{{ t("answers.fromBank") }}</FnChip>
            <FnChip v-if="item.legal_flag">{{ t("answers.legalFlag") }}</FnChip>
            <FnChip class="font-mono">{{ charCount(item) }}</FnChip>
          </div>
        </div>

        <ul
          v-if="item.ai_restricted && (item.fact_notes ?? []).length"
          class="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-700"
        >
          <li v-for="(n, ni) in item.fact_notes" :key="ni">
            {{ typeof n === "object" && n && "text" in n ? String(n.text) : String(n) }}
          </li>
        </ul>

        <textarea
          v-if="item.ai_restricted || item.source === 'needs_story' || item.source === 'manual'"
          class="mt-2 min-h-24 w-full border border-rule bg-paper-1 p-2 text-sm"
          :value="item.draft"
          @change="saveDraft(item, ($event.target as HTMLTextAreaElement).value)"
        />
        <div v-else class="mt-2 space-y-2">
          <p
            class="whitespace-pre-wrap border border-rule bg-paper-1 p-2 font-serif text-sm text-ink-900"
            :title="
              (item.evidence_refs ?? [])
                .map((r) => String((r as { label?: string }).label || ''))
                .join(' · ')
            "
          >
            {{ item.draft }}
          </p>
          <div class="flex flex-wrap gap-1">
            <FnButton size="sm" tone="quiet" @click="copyDraft(item.draft || '')">{{
              t("answers.copy")
            }}</FnButton>
            <FnButton size="sm" tone="quiet" @click="applyTone(item.id, 'shorter')">{{
              t("answers.shorter")
            }}</FnButton>
            <FnButton size="sm" tone="quiet" @click="applyTone(item.id, 'more_specific')">{{
              t("answers.specific")
            }}</FnButton>
            <FnButton size="sm" tone="quiet" @click="applyTone(item.id, 'more_casual')">{{
              t("answers.casual")
            }}</FnButton>
            <FnButton size="sm" tone="quiet" @click="applyTone(item.id, 'more_formal')">{{
              t("answers.formal")
            }}</FnButton>
            <FnButton size="sm" tone="quiet" @click="saveBank(item.id)">{{
              t("answers.saveBank")
            }}</FnButton>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>
