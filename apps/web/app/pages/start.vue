<script setup lang="ts">
import {
  createAnswerApiV1ProfilesProfileIdAnswersPost,
  planApiV1OnboardingPlanPost,
  createScheduleApiV1TracksTrackIdSchedulesPost,
  createTrackApiV1TracksPost,
  listAnswersApiV1ProfilesProfileIdAnswersGet,
  planSearchApiV1TracksPlanPost,
  setupAnswersApiV1ProfilesProfileIdAnswersSetupPost,
  updateAnswerApiV1ProfilesProfileIdAnswersAnswerIdPatch,
  updateProfileApiV1ProfilesProfileIdPatch,
  type AnswerDraftRead,
  type AnswerRead,
  type CriteriaV1,
} from "@kame/api-client";
import {
  FnButton,
  FnChoiceCards,
  FnField,
  FnInput,
  FnSectionCard,
  FnStepper,
  FnTextarea,
  useToast,
} from "@kame/ui";
import { useQueryClient } from "@tanstack/vue-query";
import { useActiveProfile } from "~/composables/useActiveProfile";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const qc = useQueryClient();
const { ensureProfile, profileId } = useActiveProfile();

const step = ref("resume");
const steps = computed(() => [
  { key: "resume", label: t("start.stepResume") },
  { key: "basics", label: t("start.stepBasics") },
  { key: "answers", label: t("start.stepAnswers") },
  { key: "search", label: t("start.stepSearch") },
  { key: "help", label: t("start.stepHelp") },
  { key: "ai", label: t("start.stepAi") },
]);
const stepIndex = computed(() =>
  Math.max(
    0,
    steps.value.findIndex((s) => s.key === step.value),
  ),
);
const isLast = computed(() => stepIndex.value === steps.value.length - 1);

function next() {
  const target = steps.value[Math.min(steps.value.length - 1, stepIndex.value + 1)];
  if (target) step.value = target.key;
}
function back() {
  const target = steps.value[Math.max(0, stepIndex.value - 1)];
  if (target) step.value = target.key;
}

// Step 1: resume text, read in the browser so AI is optional.
const resumeText = ref("");
const resumeError = ref("");
const fileInput = ref<HTMLInputElement | null>(null);
const reading = ref(false);

const name = ref("");
const title = ref("");
const location = ref("");
const skills = ref("");

const timezone = computed(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");

const WORK_AUTH = "work_authorization";
const NOTICE = "notice_period";
const SALARY = "salary_expectation";
const RELOCATION = "relocation";

const workAuth = ref(t("start.workAuthDefault"));
const notice = ref(t("start.noticeDefault"));
const salary = ref(t("start.salaryDefault"));
const relocation = ref(t("start.relocationDefault"));

const searchText = ref("");
const searchName = ref("");
const plan = ref<CriteriaV1 | null>(null);
const planning = ref(false);
const autonomy = ref("prepare");
const helpOptions = computed(() => [
  { value: "discover", title: t("tracks.autonomyDiscover"), effect: t("tracks.stepDiscover") },
  {
    value: "prepare",
    title: t("tracks.autonomyPrepare"),
    effect: t("tracks.stepPrepare"),
    badge: t("tracks.recommended"),
  },
  { value: "assist", title: t("tracks.autonomyAssist"), effect: t("tracks.stepAssist") },
]);

const finishing = ref(false);

async function planFromResume(text: string) {
  const { data } = await planApiV1OnboardingPlanPost({
    body: {
      resume_text: text,
      profile_id: profileId.value ?? null,
      timezone: timezone.value,
    },
    throwOnError: true,
  });
  if (!data) return;
  name.value = data.basics.name || name.value;
  title.value = data.basics.headline || title.value;
  location.value = data.basics.location || location.value;
  skills.value = (data.basics.skills ?? []).join(", ");
  applyAnswerDrafts((data.answers ?? []) as AnswerDraftRead[]);
}

function applyAnswerDrafts(items: AnswerDraftRead[]) {
  for (const item of items) {
    if (!item.draft) continue;
    if (item.key === WORK_AUTH && item.draft) workAuth.value = item.draft;
    if (item.key === NOTICE) notice.value = item.draft;
    if (item.key === SALARY) salary.value = item.draft;
    if (item.key === RELOCATION) relocation.value = item.draft;
  }
}

async function onFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  reading.value = true;
  resumeError.value = "";
  try {
    if (/\.(txt|md|markdown)$/i.test(file.name) || file.type.startsWith("text/")) {
      resumeText.value = await file.text();
      await planFromResume(resumeText.value);
    } else {
      resumeError.value = t("start.pdfNeedsAi");
    }
  } finally {
    reading.value = false;
  }
}

async function readPasted() {
  resumeError.value = "";
  if (resumeText.value.trim().length < 20) {
    resumeError.value = t("start.resumeNeeded");
    return;
  }
  reading.value = true;
  try {
    await planFromResume(resumeText.value);
    next();
  } catch (e) {
    resumeError.value = apiError(e);
  } finally {
    reading.value = false;
  }
}

async function checkSearch() {
  if (!searchText.value.trim()) {
    next();
    return;
  }
  planning.value = true;
  try {
    const { data } = await planSearchApiV1TracksPlanPost({
      body: { text: searchText.value.trim() },
      throwOnError: true,
    });
    plan.value = (data?.criteria as CriteriaV1) ?? null;
    if (!searchName.value.trim() && data?.name) searchName.value = data.name;
    next();
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    planning.value = false;
  }
}

async function saveAnswer(pid: string, key: string, answer: string) {
  const existing = (
    (
      await listAnswersApiV1ProfilesProfileIdAnswersGet({
        path: { profile_id: pid },
        throwOnError: true,
      })
    ).data ?? []
  ).find((row: AnswerRead) => row.key === key);
  if (existing) {
    await updateAnswerApiV1ProfilesProfileIdAnswersAnswerIdPatch({
      path: { profile_id: pid, answer_id: String(existing.id) },
      body: { answer },
      throwOnError: true,
    });
    return;
  }
  await createAnswerApiV1ProfilesProfileIdAnswersPost({
    path: { profile_id: pid },
    body: { key, answer, approved: true },
    throwOnError: true,
  });
}

async function finish() {
  finishing.value = true;
  try {
    const pid = profileId.value ?? (await ensureProfile(name.value.trim() || "My profile"));
    await updateProfileApiV1ProfilesProfileIdPatch({
      path: { profile_id: pid },
      body: {
        display_name: name.value.trim() || undefined,
        headline: title.value.trim() || undefined,
        location: location.value.trim() || undefined,
        timezone: timezone.value,
      },
      throwOnError: true,
    });

    try {
      await setupAnswersApiV1ProfilesProfileIdAnswersSetupPost({
        path: { profile_id: pid },
        body: { countries: [], include_links: true },
        throwOnError: true,
      });
      await saveAnswer(pid, WORK_AUTH, workAuth.value);
      await saveAnswer(pid, NOTICE, notice.value);
      await saveAnswer(pid, SALARY, salary.value);
      await saveAnswer(pid, RELOCATION, relocation.value);
    } catch {
      // Answers are optional; the search still starts.
    }

    let trackId = "";
    if (searchText.value.trim()) {
      const { data } = await createTrackApiV1TracksPost({
        body: {
          profile_id: pid,
          name: searchName.value.trim() || undefined,
          nl_text: searchText.value.trim(),
          criteria: plan.value ?? undefined,
          suggest: !plan.value,
          autonomy: autonomy.value as "discover" | "prepare" | "assist",
        },
        throwOnError: true,
      });
      trackId = String(data?.id ?? "");
    }

    if (trackId) {
      try {
        await createScheduleApiV1TracksTrackIdSchedulesPost({
          path: { track_id: trackId },
          body: {
            preset: "every_4_hours",
            timezone: timezone.value,
            quiet_hours: { start: "22:00", end: "07:00" },
            daily_cap: 12,
          },
          throwOnError: true,
        });
      } catch {
        // The automation tab offers another try.
      }
    }

    await qc.invalidateQueries();
    await navigateTo(trackId ? `/tracks/${trackId}` : "/jobs");
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    finishing.value = false;
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-2xl flex-col gap-5">
    <PageHeader :title="t('start.title')" :lede="t('start.introLine')" />

    <FnStepper
      v-model="step"
      :steps="steps"
      :label="t('start.title')"
      clickable
      :done-before="stepIndex"
    />
    <p class="text-sm text-ink-600">
      {{ t("start.stepOf", { n: stepIndex + 1, total: steps.length }) }}
    </p>

    <FnSectionCard
      v-if="step === 'resume'"
      :title="t('start.resumeTitle')"
      :intro="t('start.resumeBody')"
    >
      <div class="flex flex-wrap gap-2">
        <FnButton tone="primary" @click="fileInput?.click()">{{ t("start.upload") }}</FnButton>
        <input
          ref="fileInput"
          type="file"
          accept=".txt,.md,.pdf,.doc,.docx"
          class="sr-only"
          @change="onFile"
        >
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/profile/onboarding">{{ t("start.readPdf") }}</NuxtLink>
        </FnButton>
        <FnButton
          tone="ghost"
          @click="
            name = '';
            title = '';
            location = '';
            next();
          "
          >{{ t("start.blank") }}</FnButton
        >
      </div>
      <FnField v-slot="{ id }" :label="t('start.pasteLabel')">
        <FnTextarea
          :id="id"
          v-model="resumeText"
          :rows="7"
          :placeholder="t('start.pastePlaceholder')"
        />
      </FnField>
      <p v-if="reading" class="text-sm text-ink-600">{{ t("start.reading") }}</p>
      <p v-if="resumeError" role="alert" class="text-sm text-oxblood-600">{{ resumeError }}</p>
      <p class="text-sm text-ink-600">{{ t("start.aiNeeded") }}</p>
      <div class="flex flex-wrap gap-2">
        <FnButton tone="primary" :disabled="!resumeText.trim()" @click="readPasted">{{
          t("start.parseWithAi")
        }}</FnButton>
        <FnButton tone="ghost" as-child>
          <a href="/settings/ai" target="_blank" rel="noopener">{{ t("start.turnOnAi") }}</a>
        </FnButton>
      </div>
    </FnSectionCard>

    <FnSectionCard
      v-else-if="step === 'basics'"
      :title="t('start.basicsTitle')"
      :intro="t('start.basicsBody')"
    >
      <FnField v-slot="{ id }" :label="t('start.name')">
        <FnInput :id="id" v-model="name" autocomplete="name" />
      </FnField>
      <FnField v-slot="{ id }" :label="t('start.currentTitle')">
        <FnInput :id="id" v-model="title" autocomplete="organization-title" />
      </FnField>
      <FnField v-slot="{ id }" :label="t('start.location')">
        <FnInput :id="id" v-model="location" :placeholder="t('start.locationPlaceholder')" />
      </FnField>
      <FnField v-slot="{ id }" :label="t('start.skills')" :hint="t('start.skillsHint')">
        <FnInput :id="id" v-model="skills" />
      </FnField>
    </FnSectionCard>

    <FnSectionCard
      v-else-if="step === 'answers'"
      :title="t('start.answersTitle')"
      :intro="t('start.answersBody')"
    >
      <FnField v-slot="{ id }" :label="t('start.workAuth')">
        <FnInput :id="id" v-model="workAuth" />
      </FnField>
      <FnField v-slot="{ id }" :label="t('start.notice')">
        <FnInput :id="id" v-model="notice" />
      </FnField>
      <FnField v-slot="{ id }" :label="t('start.salary')">
        <FnInput :id="id" v-model="salary" />
      </FnField>
      <FnField v-slot="{ id }" :label="t('start.relocation')">
        <FnInput :id="id" v-model="relocation" />
      </FnField>
      <p class="text-sm text-ink-600">{{ t("start.answersNote") }}</p>
    </FnSectionCard>

    <FnSectionCard
      v-else-if="step === 'search'"
      :title="t('start.searchTitle')"
      :intro="t('start.searchBody')"
    >
      <FnField v-slot="{ id }" :label="t('start.searchLabel')">
        <FnTextarea
          :id="id"
          v-model="searchText"
          :rows="3"
          :placeholder="t('start.searchPlaceholder')"
        />
      </FnField>
      <FnField v-slot="{ id }" :label="t('start.searchName')">
        <FnInput :id="id" v-model="searchName" />
      </FnField>
    </FnSectionCard>

    <FnSectionCard
      v-else-if="step === 'help'"
      :title="t('start.helpTitle')"
      :intro="t('start.helpBody')"
    >
      <FnChoiceCards v-model="autonomy" :options="helpOptions" :label="t('start.helpTitle')" />
    </FnSectionCard>

    <FnSectionCard v-else :title="t('start.aiTitle')" :intro="t('start.aiBody')">
      <div class="flex flex-wrap gap-2">
        <FnButton tone="primary" as-child>
          <a href="/settings/ai" target="_blank" rel="noopener">{{ t("start.aiFree") }}</a>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <a href="/settings/ai" target="_blank" rel="noopener">{{ t("start.aiOwn") }}</a>
        </FnButton>
      </div>
      <p class="text-sm text-ink-600">{{ t("start.aiNote") }}</p>
    </FnSectionCard>

    <div class="flex flex-wrap items-center gap-2">
      <FnButton v-if="stepIndex > 0" tone="ghost" @click="back">{{ t("start.back") }}</FnButton>
      <FnButton v-if="step === 'resume'" tone="ghost" class="ml-auto" @click="next">{{
        t("start.skip")
      }}</FnButton>
      <FnButton
        v-if="step === 'basics' || step === 'answers'"
        tone="primary"
        class="ml-auto"
        @click="next"
        >{{ t("start.next") }}</FnButton
      >
      <FnButton
        v-else-if="step === 'search'"
        tone="primary"
        class="ml-auto"
        :loading="planning"
        @click="checkSearch"
        >{{ t("start.next") }}</FnButton
      >
      <FnButton v-else-if="step === 'help'" tone="primary" class="ml-auto" @click="next">{{
        t("start.next")
      }}</FnButton>
      <FnButton
        v-else-if="isLast"
        tone="primary"
        class="ml-auto"
        :loading="finishing"
        @click="finish"
        >{{ finishing ? t("start.finishing") : t("start.finish") }}</FnButton
      >
    </div>
  </div>
</template>
