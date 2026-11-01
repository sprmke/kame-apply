<script setup lang="ts">
import { useActiveProfile } from "~/composables/useActiveProfile";
import {
  getVoiceApiV1ProfilesProfileIdVoiceGet,
  putVoiceSamplesApiV1ProfilesProfileIdVoiceSamplesPut,
  updateVoiceApiV1ProfilesProfileIdVoicePatch,
  type VoiceRead,
} from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton, FnTextarea, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const qc = useQueryClient();
const { profileId, ensureProfile } = useActiveProfile();
const sampleDraft = ref(["", "", ""]);
const bannedDraft = ref("");
const summaryDraft = ref("");
const busy = ref(false);

onMounted(() => ensureProfile().catch((e) => toast.push({ title: apiError(e), tone: "danger" })));

const voice = useQuery({
  queryKey: computed(() => ["voice", profileId.value]),
  queryFn: async () => {
    const { data } = await getVoiceApiV1ProfilesProfileIdVoiceGet({
      path: { profile_id: profileId.value! },
      throwOnError: true,
    });
    return data as VoiceRead;
  },
  enabled: computed(() => Boolean(profileId.value)),
});

const voiceData = computed(() => voice.data.value ?? null);
const voiceLoading = computed(
  () => Boolean(profileId.value) && voice.isFetching.value && !voiceData.value,
);

watch(
  voiceData,
  (v) => {
    if (!v) return;
    summaryDraft.value = v.style.summary ?? "";
    bannedDraft.value = (v.banned_phrases ?? []).join("\n");
    const texts = (v.samples ?? []).map((s) => s.text);
    sampleDraft.value = [texts[0] ?? "", texts[1] ?? "", texts[2] ?? ""];
  },
  { immediate: true },
);

async function saveSamples() {
  if (!profileId.value) return;
  const samples = sampleDraft.value
    .map((text) => text.trim())
    .filter((text) => text.length >= 20)
    .map((text) => ({ text }));
  if (samples.length < 1) {
    toast.push({ title: t("career.samplesNeeded"), tone: "danger" });
    return;
  }
  busy.value = true;
  try {
    await putVoiceSamplesApiV1ProfilesProfileIdVoiceSamplesPut({
      path: { profile_id: profileId.value },
      body: { samples, analyze: true },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["voice", profileId.value] });
    toast.push({ title: t("common.saved"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}

async function saveMeta() {
  if (!profileId.value) return;
  busy.value = true;
  try {
    await updateVoiceApiV1ProfilesProfileIdVoicePatch({
      path: { profile_id: profileId.value },
      body: {
        summary: summaryDraft.value.trim(),
        banned_phrases: bannedDraft.value
          .split("\n")
          .map((p) => p.trim())
          .filter(Boolean),
      },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["voice", profileId.value] });
    toast.push({ title: t("common.saved"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="flex max-w-2xl flex-col gap-6">
    <section class="flex flex-col gap-2">
      <h3 class="text-sm font-medium text-ink-900">{{ t("career.samples") }}</h3>
      <FnSkeleton v-if="voiceLoading" class="h-24 w-full" />
      <template v-else>
        <FnTextarea
          v-for="(_, i) in sampleDraft"
          :key="i"
          v-model="sampleDraft[i]"
          :rows="4"
          :aria-label="t('career.sampleN', { n: i + 1 })"
        />
        <FnButton tone="primary" :loading="busy" @click="saveSamples">{{
          t("career.analyze")
        }}</FnButton>
      </template>
    </section>

    <section v-if="voiceData?.style?.summary" class="flex flex-col gap-2">
      <h3 class="text-sm font-medium text-ink-900">{{ t("career.voiceSummary") }}</h3>
      <FnTextarea v-model="summaryDraft" :rows="2" :aria-label="t('career.voiceSummary')" />
      <div class="flex flex-wrap gap-2 text-xs text-ink-600">
        <FnChip>{{ voiceData.style.vocabulary_level }}</FnChip>
        <FnChip
          >{{ voiceData.style.avg_sentence_length }} {{ t("career.wordsPerSentence") }}</FnChip
        >
      </div>
    </section>

    <section class="flex flex-col gap-2">
      <h3 class="text-sm font-medium text-ink-900">{{ t("career.banned") }}</h3>
      <FnTextarea v-model="bannedDraft" :rows="8" :aria-label="t('career.banned')" />
      <FnButton tone="quiet" :loading="busy" @click="saveMeta">{{ t("common.save") }}</FnButton>
    </section>
  </div>
</template>
