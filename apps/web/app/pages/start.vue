<script setup lang="ts">
import {
  applySetupApiV1OnboardingSetupsDraftIdApplyPost,
  cancelSetupApiV1OnboardingSetupsDraftIdCancelPost,
  createSetupApiV1OnboardingSetupsPost,
  getSetupApiV1OnboardingSetupsDraftIdGet,
  listCredentialsApiV1AiCredentialsGet,
  openSetupApiV1OnboardingSetupsGet,
  patchDecisionsApiV1OnboardingSetupsDraftIdDecisionsPatch,
  retrySetupApiV1OnboardingSetupsDraftIdRetryPost,
  uploadDocumentApiV1ProfilesProfileIdDocumentsPost,
  validateSetupApiV1OnboardingSetupsDraftIdValidatePost,
  type SetupRead,
} from "@kame/api-client";
import {
  FnButton,
  FnCheckbox,
  FnChip,
  FnDialog,
  FnField,
  FnInput,
  FnPencilText,
  FnSectionCard,
  FnSelect,
  FnStepper,
  FnTextarea,
  useToast,
} from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { errorCode, toApiError } from "~/lib/errors";
import {
  answerCountry,
  answerLabelKey,
  criteriaSummary,
  decisionFor,
  fieldKey,
  groupItems,
  isKept,
  isSearchKept,
  itemValueText,
  parseAmount,
  salaryText,
  searchSkillText,
  searchTitleText,
  setKept,
  setSearchKept,
  setValue,
  summarySentence,
  withSkills,
  withTitles,
  type Decisions,
  type LowestPay,
  type ReviewItem,
  type ReviewSearch,
} from "~/lib/setup";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const qc = useQueryClient();
const route = useRoute();
const { ensureProfile } = useActiveProfile();
const { data: creds } = useQuery({
  queryKey: ["setup-ai-credentials"],
  queryFn: async () => (await listCredentialsApiV1AiCredentialsGet()).data ?? [],
});
const hasAi = computed(() => (creds.value?.length ?? 0) > 0);

type Step = "resume" | "reading" | "review" | "done";
const step = ref<Step>("resume");
const steps = computed(() => [
  { key: "resume", label: t("setup.stepResume") },
  { key: "reading", label: t("setup.stepReading") },
  { key: "review", label: t("setup.stepReview") },
]);
const stepIndex = computed(() =>
  Math.max(
    0,
    steps.value.findIndex((row) => row.key === step.value),
  ),
);

const timezone = computed(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
const RESUME_ACCEPT = ".txt,.md,.pdf,.doc,.docx";

const fileInput = ref<HTMLInputElement | null>(null);
const file = ref<File | null>(null);
const resumeText = ref("");
const roleText = ref("");
const starting = ref(false);
const startError = ref("");
const draft = ref<SetupRead | null>(null);
const decisions = ref<Decisions>({
  items: {},
  searches: {},
  lowest_pay: null,
  lowest_pay_set: false,
  seen_pages: [],
});
const lowestAmount = ref("");
const lowestCurrency = ref("USD");
const lowestPeriod = ref<LowestPay["period"]>("month");
const seeAllOpen = ref(false);
const editOpen = ref(false);
const localValues = ref<Record<string, string>>({});
const applying = ref(false);
const itemErrors = ref<Record<string, string>>({});
const showAll = ref(false);
const saving = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;
let saveTimer: ReturnType<typeof setTimeout> | null = null;
let hydrating = false;

const bundle = computed(() => draft.value?.bundle ?? null);
const items = computed<ReviewItem[]>(() => (bundle.value?.items ?? []) as ReviewItem[]);
const searches = computed<ReviewSearch[]>(() => (bundle.value?.searches ?? []) as ReviewSearch[]);
const grouped = computed(() => groupItems(items.value));
const needsYouCount = computed(
  () =>
    items.value.filter((item) => item.needs_you).length +
    searches.value.filter((row) => row.blocked !== "ok").length,
);
const keptCounts = computed(() => {
  const counts = { profile: 0, answers: 0, searches: 0 };
  for (const item of items.value) {
    if (hiddenSalaryTargets.has(item.target)) continue;
    if (item.group === "profile" && isKept(decisions.value, item)) counts.profile += 1;
    if (item.group === "answers" && isKept(decisions.value, item)) counts.answers += 1;
  }
  counts.searches = searches.value.filter((row) => isSearchKept(decisions.value, row)).length;
  return counts;
});
const keptSummary = computed(() => summarySentence(keptCounts.value));
const hiddenSalaryTargets = new Set(["profile.salary_prefs", "answers.salary_expectation"]);
const visibleItems = computed(() => {
  const out: ReviewItem[] = [];
  for (const group of ["profile", "answers"] as const) {
    const rows = grouped.value[group] ?? [];
    out.push(...(showAll.value ? rows : rows.slice(0, 12)));
  }
  return out;
});
const moreHidden = computed(() =>
  (["profile", "answers"] as const).some((group) => (grouped.value[group]?.length ?? 0) > 12),
);
const failed = computed(() => draft.value?.status === "failed");
const pollError = ref(false);

const stepRows = computed(() =>
  [
    "read_file",
    "check_document",
    "extract_profile",
    "stated_signals",
    "normalize",
    "plan_searches",
    "ground_and_build",
  ].map((key) => ({
    key,
    label: t(`setup.stepName.${key}`),
    status: String(
      (draft.value?.steps?.[key] as { status?: string } | undefined)?.status ?? "pending",
    ),
  })),
);

function openFile() {
  fileInput.value?.click();
}
function onFile(event: Event) {
  const picked = (event.target as HTMLInputElement).files?.[0] ?? null;
  file.value = picked;
  if (picked && /\.(txt|md|markdown)$/i.test(picked.name)) {
    void picked.text().then((text) => {
      resumeText.value = text;
      file.value = null;
    });
  }
  if (fileInput.value) fileInput.value.value = "";
}

function hydrate(data: SetupRead) {
  hydrating = true;
  draft.value = data;
  const saved = (data.decisions ?? {}) as Partial<Decisions>;
  decisions.value = {
    items: saved.items ?? {},
    searches: saved.searches ?? {},
    lowest_pay: saved.lowest_pay ?? null,
    lowest_pay_set: saved.lowest_pay_set ?? false,
    seen_pages: saved.seen_pages ?? [],
  };
  const detected =
    saved.lowest_pay ?? (data.bundle?.lowest_pay as LowestPay | null | undefined) ?? null;
  if (detected) {
    lowestAmount.value = String(detected.amount);
    lowestCurrency.value = detected.currency;
    lowestPeriod.value = detected.period;
  }
  const values: Record<string, string> = {};
  for (const item of (data.bundle?.items ?? []) as ReviewItem[]) {
    const decision = decisions.value.items[item.id];
    if (decision?.edited) {
      const value = decision.value;
      values[item.id] =
        typeof value === "string"
          ? value
          : String((value as { answer?: string } | undefined)?.answer ?? "");
    } else if (item.target.startsWith("answers.")) {
      values[item.id] = String((item.value as { answer?: string } | null)?.answer ?? "");
    } else if (
      [
        "profile.display_name",
        "profile.headline",
        "profile.summary",
        "profile.location",
        "profile.timezone",
        "account.name",
        "account.timezone",
      ].includes(item.target)
    ) {
      values[item.id] = itemValueText(item);
    }
  }
  localValues.value = values;
  hydrating = false;
  if (data.status === "ready") {
    stopPolling();
    step.value = "review";
  } else if (data.status === "applied") {
    stopPolling();
    step.value = "done";
  } else if (data.status === "failed") {
    step.value = "reading";
  } else {
    step.value = "reading";
    startPolling(data.id);
  }
}

function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
}
function startPolling(draftId: string) {
  stopPolling();
  pollTimer = setInterval(async () => {
    try {
      const { data } = await getSetupApiV1OnboardingSetupsDraftIdGet({
        path: { draft_id: draftId },
        throwOnError: true,
      });
      if (data) hydrate(data as SetupRead);
    } catch {
      stopPolling();
      pollError.value = true;
    }
  }, 1500);
}

async function start() {
  startError.value = "";
  if (!file.value && resumeText.value.trim().length < 200) {
    startError.value = t("setup.needMoreText");
    return;
  }
  starting.value = true;
  try {
    const profileId = await ensureProfile();
    let body: Record<string, unknown>;
    if (file.value) {
      const { data } = await uploadDocumentApiV1ProfilesProfileIdDocumentsPost({
        path: { profile_id: profileId },
        body: { file: file.value, kind: "resume_upload" },
        throwOnError: true,
      });
      if (!data?.id || !data.extracted_text) {
        startError.value = t("setup.fileUnreadable");
        return;
      }
      body = {
        document_id: data.id,
        role_text: roleText.value.trim() || null,
        timezone: timezone.value,
        with_ai: hasAi.value,
      };
    } else {
      body = {
        text: resumeText.value.trim(),
        role_text: roleText.value.trim() || null,
        timezone: timezone.value,
        with_ai: hasAi.value,
      };
    }
    const { data } = await createSetupApiV1OnboardingSetupsPost({
      body: body as never,
      throwOnError: true,
    });
    if (data) hydrate(data as SetupRead);
  } catch (error) {
    startError.value = apiError(error);
  } finally {
    starting.value = false;
  }
}

async function saveDecisions() {
  const current = draft.value;
  if (!current || current.status !== "ready") return;
  saving.value = true;
  try {
    const { data } = await patchDecisionsApiV1OnboardingSetupsDraftIdDecisionsPatch({
      path: { draft_id: current.id },
      body: {
        items: decisions.value.items,
        searches: decisions.value.searches,
        lowest_pay: decisions.value.lowest_pay,
        lowest_pay_set: decisions.value.lowest_pay_set,
        seen_pages: decisions.value.seen_pages,
      } as never,
      throwOnError: true,
    });
    if (data) draft.value = data as SetupRead;
  } catch {
    toast.push({ title: t("setup.saveChoicesFailed"), tone: "danger" });
  } finally {
    saving.value = false;
  }
}

function commitLowestPay() {
  const amount = parseAmount(lowestAmount.value);
  decisions.value = {
    ...decisions.value,
    lowest_pay: amount
      ? {
          amount,
          currency: (lowestCurrency.value || "USD").toUpperCase(),
          period: lowestPeriod.value,
        }
      : null,
    lowest_pay_set: true,
  };
}

watch([lowestAmount, lowestCurrency, lowestPeriod], () => {
  if (hydrating) return;
  commitLowestPay();
});

watch(
  decisions,
  () => {
    if (hydrating) return;
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => void saveDecisions(), 700);
  },
  { deep: true },
);

function toggleItem(item: ReviewItem, kept: boolean) {
  decisions.value = setKept(decisions.value, item, kept);
}
function commitValue(item: ReviewItem) {
  const value = localValues.value[item.id] ?? "";
  if (item.target.startsWith("answers.")) {
    decisions.value = setValue(decisions.value, item, { answer: value, approved: true });
  } else {
    decisions.value = setValue(decisions.value, item, value);
  }
}
function toggleSearch(search: ReviewSearch, kept: boolean) {
  decisions.value = setSearchKept(decisions.value, search, kept);
}

async function retry() {
  if (!draft.value) return;
  try {
    const { data } = await retrySetupApiV1OnboardingSetupsDraftIdRetryPost({
      path: { draft_id: draft.value.id },
      body: { with_ai: hasAi.value },
      throwOnError: true,
    });
    if (data) hydrate(data as SetupRead);
  } catch (error) {
    toast.push({ title: apiError(error), tone: "danger" });
  }
}

async function cancel() {
  if (!draft.value) return;
  try {
    await cancelSetupApiV1OnboardingSetupsDraftIdCancelPost({
      path: { draft_id: draft.value.id },
      throwOnError: true,
    });
    toast.push({ title: t("setup.cancelled") });
    step.value = "resume";
    stopPolling();
  } catch (error) {
    toast.push({ title: apiError(error), tone: "danger" });
  }
}

async function apply() {
  if (!draft.value) return;
  itemErrors.value = {};
  applying.value = true;
  try {
    // Flush the debounced autosave first: a typed answer must reach the server before apply.
    if (saveTimer) {
      clearTimeout(saveTimer);
      saveTimer = null;
    }
    await saveDecisions();
    const check = await validateSetupApiV1OnboardingSetupsDraftIdValidatePost({
      path: { draft_id: draft.value.id },
      throwOnError: true,
    });
    if (check.data && !check.data.ok) {
      itemErrors.value = check.data.errors ?? {};
      toast.push({ title: t("setup.fixMarked"), tone: "danger" });
      return;
    }
    const key =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `${draft.value.id}-${Date.now()}`;
    const { data } = await applySetupApiV1OnboardingSetupsDraftIdApplyPost({
      path: { draft_id: draft.value.id },
      body: { start_first_run: true },
      headers: { "Idempotency-Key": key },
      throwOnError: true,
    });
    await qc.invalidateQueries();
    const firstSearch = data?.created?.searches?.[0];
    toast.push({ title: t("setup.applied"), tone: "success" });
    await navigateTo(firstSearch ? `/tracks/${firstSearch}?setup_done=1` : "/profile?setup_done=1");
  } catch (error) {
    if (errorCode(error) === "setup_stale") {
      toast.push({ title: t("setup.changedSinceRead"), tone: "danger" });
      const { data } = await getSetupApiV1OnboardingSetupsDraftIdGet({
        path: { draft_id: draft.value.id },
        throwOnError: true,
      });
      if (data) hydrate(data as SetupRead);
    } else {
      toast.push({ title: apiError(error), tone: "danger" });
    }
  } finally {
    applying.value = false;
  }
}

type EditSearchState = {
  variant: string;
  name: string;
  titles: string;
  must: string;
  nice: string;
  place: string;
  workMode: string;
  autonomy: string;
  preset: string;
  dailyCap: number;
  base: EditBase;
};

type EditBase = {
  name?: string;
  autonomy?: string;
  summary?: string;
  schedule?: Record<string, unknown>;
  criteria: {
    titles: Array<{ title: string; synonyms: string[]; exclude: boolean }>;
    skills: { must: string[]; nice: string[]; exclude: string[] };
    locations?: Array<Record<string, unknown>>;
    work_modes?: string[];
  };
};

const editingSearch = ref<EditSearchState | null>(null);

function openSearchEdit(search: ReviewSearch) {
  const original =
    decisions.value.searches[search.variant] ??
    searches.value.find((row) => row.variant === search.variant);
  if (!original) return;
  const base = structuredClone(original) as unknown as EditBase;
  editingSearch.value = {
    variant: search.variant,
    name: String(base.name ?? ""),
    titles: searchTitleText(base),
    must: searchSkillText(base, "must"),
    nice: searchSkillText(base, "nice"),
    place: String(base.criteria?.locations?.[0]?.place ?? ""),
    workMode: String(base.criteria?.work_modes?.[0] ?? ""),
    autonomy: String(base.autonomy ?? "prepare"),
    preset: String(base.schedule?.preset ?? "every_4_hours"),
    dailyCap: Number(base.schedule?.daily_cap ?? 12),
    base,
  };
  editOpen.value = true;
}

function saveSearchEdit() {
  const edit = editingSearch.value;
  if (!edit) return;
  const base = edit.base;
  let next = withTitles({ ...base, criteria: base.criteria }, edit.titles);
  next = withSkills(next, "must", edit.must);
  next = withSkills(next, "nice", edit.nice);
  const firstLocation = base.criteria.locations?.[0] ?? { place: edit.place };
  const locations = edit.place.trim() ? [{ ...firstLocation, place: edit.place.trim() }] : [];
  const criteria = {
    ...next.criteria,
    locations,
    work_modes: edit.workMode ? [edit.workMode] : [],
  };
  const updated = {
    ...next,
    name: edit.name.trim() || String((next as { name?: string }).name ?? ""),
    summary: criteriaSummary(criteria),
    autonomy: edit.autonomy,
    schedule: {
      ...((next as { schedule?: Record<string, unknown> }).schedule ?? {}),
      preset: edit.preset,
      daily_cap: edit.dailyCap,
    },
    criteria,
  };
  decisions.value = {
    ...decisions.value,
    searches: { ...decisions.value.searches, [edit.variant]: updated },
  };
  editOpen.value = false;
}

function saveForLater() {
  toast.push({ title: t("setup.savedForLater") });
  void navigateTo("/");
}

function sourceLabel(source: string) {
  return t(
    source === "resume"
      ? "setup.source.resume"
      : source === "you_said"
        ? "setup.source.youSaid"
        : source === "suggested"
          ? "setup.source.suggested"
          : "setup.source.recommended",
  );
}

function isEditable(item: ReviewItem) {
  return (
    item.target.startsWith("answers.") ||
    [
      "profile.display_name",
      "profile.headline",
      "profile.summary",
      "profile.location",
      "profile.timezone",
      "account.name",
      "account.timezone",
    ].includes(item.target)
  );
}

onMounted(async () => {
  const setupId = typeof route.query.setup === "string" ? route.query.setup : null;
  const documentId = typeof route.query.document === "string" ? route.query.document : null;
  try {
    if (documentId) {
      try {
        const pid = await ensureProfile();
        const { data } = await createSetupApiV1OnboardingSetupsPost({
          body: {
            document_id: documentId,
            profile_id: pid,
            timezone: timezone.value,
            with_ai: hasAi.value,
          },
          throwOnError: true,
        });
        if (data) hydrate(data as SetupRead);
      } catch (error) {
        const details = toApiError(error).details as { draft_id?: string } | undefined;
        if (errorCode(error) === "setup_open_exists" && details?.draft_id) {
          const { data } = await getSetupApiV1OnboardingSetupsDraftIdGet({
            path: { draft_id: details.draft_id },
            throwOnError: true,
          });
          if (data) hydrate(data as SetupRead);
        } else {
          startError.value = apiError(error);
        }
      }
      return;
    }
    if (setupId) {
      const { data } = await getSetupApiV1OnboardingSetupsDraftIdGet({
        path: { draft_id: setupId },
        throwOnError: true,
      });
      if (data) hydrate(data as SetupRead);
      return;
    }
    const { data } = await openSetupApiV1OnboardingSetupsGet({ throwOnError: true });
    if (data) hydrate(data as SetupRead);
  } catch {
    // A missing or expired draft just leaves the upload step in place.
  }
});

onBeforeUnmount(() => {
  stopPolling();
  if (saveTimer) clearTimeout(saveTimer);
});
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-5 pb-24">
    <!-- eslint-disable vue/html-self-closing (prettier keeps the slash on void elements) -->
    <PageHeader :title="t('setup.title')" :lede="t('setup.intro')" />

    <FnStepper
      :model-value="step"
      :steps="steps"
      :label="t('setup.title')"
      :done-before="stepIndex"
      @update:model-value="(value) => (step = value as Step)"
    />
    <p class="text-sm text-ink-600">
      {{ t("setup.stepOf", { n: stepIndex + 1, total: steps.length }) }}
    </p>

    <FnSectionCard
      v-if="step === 'resume'"
      :title="t('setup.resumeTitle')"
      :intro="t('setup.resumeBody')"
    >
      <div class="flex flex-wrap gap-2">
        <FnButton tone="quiet" @click="openFile">{{ t("setup.upload") }}</FnButton>
        <input
          ref="fileInput"
          type="file"
          :accept="RESUME_ACCEPT"
          class="sr-only"
          @change="onFile"
        />
        <FnButton tone="ghost" as-child>
          <NuxtLink to="/tracks">{{ t("setup.startBlank") }}</NuxtLink>
        </FnButton>
      </div>
      <p v-if="file" class="text-sm text-ink-600">{{ file.name }}</p>

      <FnField v-slot="{ id }" :label="t('setup.pasteLabel')">
        <FnTextarea
          :id="id"
          v-model="resumeText"
          :rows="8"
          :placeholder="t('setup.pastePlaceholder')"
        />
      </FnField>

      <FnField v-slot="{ id }" :label="t('setup.roleLabel')" :hint="t('setup.roleHint')">
        <FnInput :id="id" v-model="roleText" :placeholder="t('setup.rolePlaceholder')" />
      </FnField>

      <p class="text-sm text-ink-600">
        {{ hasAi ? t("setup.aiOn") : t("setup.aiOff") }}
        <NuxtLink to="/settings/ai" class="text-brand-700 underline">{{
          t("setup.aiSettings")
        }}</NuxtLink>
      </p>
      <p v-if="startError" role="alert" class="text-sm text-oxblood-600">{{ startError }}</p>
      <div class="flex flex-wrap gap-2">
        <FnButton tone="primary" :loading="starting" @click="start">{{
          t("setup.readResume")
        }}</FnButton>
      </div>
    </FnSectionCard>

    <FnSectionCard
      v-else-if="step === 'reading'"
      :title="t('setup.readingTitle')"
      :intro="t('setup.readingBody')"
    >
      <ul class="flex flex-col gap-2" aria-live="polite">
        <li v-for="row in stepRows" :key="row.key" class="flex items-center gap-3 text-sm">
          <span
            aria-hidden="true"
            class="grid size-5 place-items-center rounded-full border text-xs"
            :class="
              row.status === 'done'
                ? 'border-fern-600 text-fern-600'
                : row.status === 'failed'
                  ? 'border-oxblood-600 text-oxblood-600'
                  : 'border-rule text-ink-400'
            "
          >
            {{ row.status === "done" ? "✓" : row.status === "failed" ? "!" : "•" }}
          </span>
          <span :class="row.status === 'pending' ? 'text-ink-400' : 'text-ink-900'">{{
            row.label
          }}</span>
        </li>
      </ul>

      <div v-if="pollError" class="flex flex-col gap-2">
        <p role="alert" class="text-sm text-oxblood-600">{{ t("setup.pollFailed") }}</p>
        <FnButton tone="primary" @click="retry">{{ t("setup.tryAgain") }}</FnButton>
      </div>
      <div v-else-if="failed" class="flex flex-col gap-2">
        <p role="alert" class="text-sm text-oxblood-600">
          {{ t(`setup.failure.${draft?.error_code ?? "setup_build_failed"}`) }}
        </p>
        <div class="flex flex-wrap gap-2">
          <FnButton tone="primary" @click="retry">{{ t("setup.tryAgain") }}</FnButton>
          <FnButton tone="quiet" @click="step = 'resume'">{{ t("setup.pasteInstead") }}</FnButton>
        </div>
      </div>
      <div v-else class="flex flex-wrap gap-2">
        <FnButton tone="quiet" @click="cancel">{{ t("setup.cancel") }}</FnButton>
      </div>
    </FnSectionCard>

    <template v-else-if="step === 'review' && bundle">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <p class="text-sm text-ink-600">{{ t("setup.reviewIntro") }}</p>
        <FnChip v-if="needsYouCount" tone="accent">{{
          t("setup.needYouCount", { n: needsYouCount })
        }}</FnChip>
      </div>

      <div v-for="notice in bundle.notices" :key="notice" class="text-sm text-ink-600">
        {{ t(`setup.notice.${notice}`) }}
      </div>

      <FnSectionCard
        v-if="(grouped.profile ?? []).length"
        :title="t('setup.group.profile')"
        :intro="t('setup.group.profileIntro')"
      >
        <div class="flex flex-col divide-y divide-rule">
          <div
            v-for="item in visibleItems.filter(
              (row) => row.group === 'profile' && !hiddenSalaryTargets.has(row.target),
            )"
            :key="item.id"
            class="flex flex-col gap-2 py-3"
          >
            <div class="flex flex-wrap items-center gap-2">
              <FnCheckbox
                :id="`keep-${item.id}`"
                :model-value="isKept(decisions, item)"
                :disabled="item.blocked !== 'ok'"
                :label="t('setup.keepField', { field: t(fieldKey(item.target)) })"
                @update:model-value="(value) => toggleItem(item, Boolean(value))"
              />
              <FnChip>{{ sourceLabel(item.source) }}</FnChip>
              <FnChip v-if="item.blocked === 'duplicate'" tone="neutral">{{
                t("setup.alreadyThere")
              }}</FnChip>
            </div>
            <div v-if="isEditable(item)" class="flex flex-col gap-1">
              <FnInput
                v-model="localValues[item.id]"
                :aria-label="t(fieldKey(item.target))"
                @blur="commitValue(item)"
              />
            </div>
            <FnPencilText
              v-else
              class="text-sm"
              :state="item.source === 'resume' ? 'draft' : 'ink'"
              draft-label=""
            >
              {{ itemValueText(item) }}
            </FnPencilText>
            <p v-if="item.current && typeof item.current === 'string'" class="text-xs text-ink-400">
              {{ t("setup.currentValue", { value: item.current }) }}
            </p>
            <details v-if="item.evidence?.length" class="text-xs text-ink-600">
              <summary class="flex min-h-11 cursor-pointer items-center">
                {{ t("setup.whereFrom") }}
              </summary>
              <p class="mt-1 border-l-2 border-rule pl-2 italic">"{{ item.evidence[0]?.quote }}"</p>
            </details>
            <p v-if="itemErrors[item.id]" role="alert" class="text-sm text-oxblood-600">
              {{ itemErrors[item.id] }}
            </p>
          </div>
        </div>
        <div class="flex flex-wrap gap-2">
          <FnButton v-if="moreHidden && !showAll" tone="quiet" @click="showAll = true">
            {{ t("setup.showAll") }}
          </FnButton>
          <FnButton tone="quiet" @click="seeAllOpen = true">{{ t("setup.seeAllDetail") }}</FnButton>
        </div>
      </FnSectionCard>

      <FnSectionCard
        v-if="(grouped.answers ?? []).length"
        :title="t('setup.group.answers')"
        :intro="t('setup.group.answersIntro')"
      >
        <div class="flex flex-col divide-y divide-rule">
          <div
            v-for="item in visibleItems.filter(
              (row) => row.group === 'answers' && !hiddenSalaryTargets.has(row.target),
            )"
            :key="item.id"
            class="flex flex-col gap-2 py-3"
          >
            <div class="flex flex-wrap items-center gap-2">
              <FnCheckbox
                :id="`keep-${item.id}`"
                :model-value="isKept(decisions, item)"
                :disabled="item.blocked !== 'ok'"
                :label="
                  t('setup.keepField', {
                    field: `${t(answerLabelKey(item.target))}${
                      answerCountry(item.target) ? ` (${answerCountry(item.target)})` : ''
                    }`,
                  })
                "
                @update:model-value="(value) => toggleItem(item, Boolean(value))"
              />
              <FnChip v-if="item.needs_you" tone="accent">{{ t("setup.onlyYou") }}</FnChip>
              <FnChip v-else>{{ sourceLabel(item.source) }}</FnChip>
            </div>
            <FnInput
              v-model="localValues[item.id]"
              :aria-label="t(answerLabelKey(item.target))"
              :placeholder="t('setup.onlyYouHint')"
              @blur="commitValue(item)"
            />
            <details v-if="item.evidence?.length" class="text-xs text-ink-600">
              <summary class="flex min-h-11 cursor-pointer items-center">
                {{ t("setup.whereFrom") }}
              </summary>
              <p class="mt-1 border-l-2 border-rule pl-2 italic">"{{ item.evidence[0]?.quote }}"</p>
            </details>
            <p v-if="itemErrors[item.id]" role="alert" class="text-sm text-oxblood-600">
              {{ itemErrors[item.id] }}
            </p>
          </div>
        </div>
      </FnSectionCard>

      <FnSectionCard :title="t('setup.lowestPayTitle')" :intro="t('setup.lowestPayIntro')">
        <div class="grid gap-2 sm:grid-cols-[1fr_90px_130px]">
          <FnField v-slot="{ id }" :label="t('setup.lowestPayAmount')">
            <FnInput
              :id="id"
              v-model="lowestAmount"
              inputmode="numeric"
              :placeholder="t('setup.lowestPayPlaceholder')"
              @blur="commitLowestPay"
            />
          </FnField>
          <FnField v-slot="{ id }" :label="t('setup.currency')">
            <FnInput :id="id" v-model="lowestCurrency" maxlength="3" @blur="commitLowestPay" />
          </FnField>
          <FnField v-slot="{ id }" :label="t('setup.period')">
            <FnSelect
              :id="id"
              v-model="lowestPeriod"
              :options="[
                { value: 'month', label: t('setup.periodMonth') },
                { value: 'year', label: t('setup.periodYear') },
                { value: 'hour', label: t('setup.periodHour') },
              ]"
              :aria-label="t('setup.period')"
            />
          </FnField>
        </div>
        <p class="text-sm text-ink-600">
          {{
            decisions.lowest_pay
              ? t("setup.lowestPaySummary", { value: salaryText(decisions.lowest_pay) })
              : t("setup.lowestPayEmpty")
          }}
        </p>
      </FnSectionCard>

      <FnSectionCard
        v-if="searches.length"
        :title="t('setup.group.searches')"
        :intro="t('setup.group.searchesIntro')"
      >
        <div class="flex flex-col gap-3">
          <div
            v-for="search in searches"
            :key="search.variant"
            class="flex flex-col gap-1 border-t border-rule py-3 first:border-t-0 first:pt-0"
          >
            <div class="flex flex-wrap items-center gap-2">
              <input
                :id="`keep-search-${search.variant}`"
                type="checkbox"
                class="size-5 rounded border-edge text-brand-600"
                :checked="isSearchKept(decisions, search)"
                :disabled="search.blocked !== 'ok'"
                @change="toggleSearch(search, ($event.target as HTMLInputElement).checked)"
              />
              <label
                :for="`keep-search-${search.variant}`"
                class="text-sm font-semibold text-ink-900"
              >
                {{
                  (decisions.searches[search.variant] as { name?: string } | undefined)?.name ??
                  search.name
                }}
              </label>
              <FnChip v-if="search.variant === 'step_up'" tone="accent">{{
                t("setup.oneStepUp")
              }}</FnChip>
              <FnChip v-if="search.duplicate_of" tone="neutral">{{
                t("setup.searchDuplicate")
              }}</FnChip>
              <FnChip v-if="search.blocked === 'limit'" tone="neutral">{{
                t("setup.searchLimit")
              }}</FnChip>
              <FnChip v-if="decisions.searches[search.variant]" tone="accent">{{
                t("setup.edited")
              }}</FnChip>
              <FnButton tone="ghost" class="ml-auto" @click="openSearchEdit(search)">
                {{ t("setup.editSearch") }}
              </FnButton>
            </div>
            <p class="text-sm text-ink-600">
              {{
                (decisions.searches[search.variant] as { summary?: string } | undefined)?.summary ||
                search.summary
              }}
            </p>
          </div>
        </div>
      </FnSectionCard>

      <div class="grid gap-5 sm:grid-cols-2">
        <FnSectionCard :title="t('setup.group.writing')">
          <div
            v-for="item in items.filter((row) => row.group === 'writing')"
            :key="item.id"
            class="flex flex-col gap-2"
          >
            <label class="text-sm font-semibold text-ink-900">{{
              t("setup.field.writingStyle")
            }}</label>
            <FnSelect
              :model-value="
                String((decisionFor(decisions, item).value as string) ?? item.value ?? 'plain')
              "
              :options="[
                { value: 'plain', label: t('setup.preset.plain') },
                { value: 'warm', label: t('setup.preset.warm') },
                { value: 'formal', label: t('setup.preset.formal') },
              ]"
              :aria-label="t('setup.field.writingStyle')"
              @update:model-value="(value) => (decisions = setValue(decisions, item, value))"
            />
            <FnChip>{{ sourceLabel(item.source) }}</FnChip>
          </div>
        </FnSectionCard>

        <FnSectionCard :title="t('setup.group.studio')">
          <div
            v-for="item in items.filter((row) => row.group === 'studio')"
            :key="item.id"
            class="flex flex-col gap-2"
          >
            <span class="text-sm text-ink-900">{{ itemValueText(item) }}</span>
            <FnChip>{{ sourceLabel(item.source) }}</FnChip>
          </div>
        </FnSectionCard>
      </div>

      <FnSectionCard v-if="(grouped.account ?? []).length" :title="t('setup.group.account')">
        <div v-for="item in grouped.account" :key="item.id" class="flex flex-col gap-1">
          <label class="text-sm text-ink-600" :for="`account-${item.id}`">{{
            t(fieldKey(item.target))
          }}</label>
          <FnInput
            :id="`account-${item.id}`"
            v-model="localValues[item.id]"
            @blur="commitValue(item)"
          />
        </div>
      </FnSectionCard>

      <div
        class="sticky bottom-20 z-20 -mx-1 flex flex-wrap items-center gap-3 rounded-xl border border-rule bg-paper-1 p-3 shadow-[var(--shadow-float)] md:bottom-0"
      >
        <p class="min-w-0 flex-1 text-sm text-ink-600">
          {{
            keptSummary
              ? t("setup.applySummary", { summary: keptSummary })
              : t("setup.applySummaryBare")
          }}
          <span v-if="saving" class="text-ink-400">{{ t("setup.savingChoices") }}</span>
        </p>
        <FnButton tone="quiet" @click="saveForLater">{{ t("setup.saveForLater") }}</FnButton>
        <FnButton tone="primary" :loading="applying" @click="apply">{{
          t("setup.applyAndSearch")
        }}</FnButton>
      </div>
    </template>

    <FnSectionCard
      v-else-if="step === 'done'"
      :title="t('setup.doneTitle')"
      :intro="t('setup.doneBody')"
    >
      <div class="flex flex-wrap gap-2">
        <FnButton tone="primary" as-child>
          <NuxtLink to="/profile">{{ t("setup.seeProfile") }}</NuxtLink>
        </FnButton>
        <FnButton tone="quiet" as-child>
          <NuxtLink to="/tracks">{{ t("setup.seeSearches") }}</NuxtLink>
        </FnButton>
      </div>
    </FnSectionCard>

    <FnDialog
      v-model:open="seeAllOpen"
      variant="sheet"
      :title="t('setup.seeAllTitle')"
      :description="t('setup.seeAllBody')"
      :close-label="t('setup.close')"
    >
      <div class="flex flex-col divide-y divide-rule">
        <div
          v-for="item in items.filter(
            (row) => row.group === 'profile' && !hiddenSalaryTargets.has(row.target),
          )"
          :key="item.id"
          class="flex flex-col gap-1 py-3"
        >
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-sm font-semibold text-ink-900">{{ t(fieldKey(item.target)) }}</span>
            <FnChip>{{ sourceLabel(item.source) }}</FnChip>
          </div>
          <span class="text-sm text-ink-900">{{ itemValueText(item) }}</span>
          <p
            v-if="item.evidence?.length"
            class="border-l-2 border-rule pl-2 text-xs text-ink-600 italic"
          >
            "{{ item.evidence[0]?.quote }}"
          </p>
        </div>
      </div>
    </FnDialog>

    <FnDialog
      v-model:open="editOpen"
      variant="sheet"
      :title="t('setup.editSearchTitle')"
      :description="t('setup.editSearchBody')"
      :close-label="t('setup.close')"
    >
      <div v-if="editingSearch" class="flex flex-col gap-4">
        <FnField v-slot="{ id }" :label="t('setup.searchName')">
          <FnInput :id="id" v-model="editingSearch.name" />
        </FnField>
        <FnField v-slot="{ id }" :label="t('setup.searchTitles')" :hint="t('setup.commaHint')">
          <FnInput :id="id" v-model="editingSearch.titles" />
        </FnField>
        <FnField v-slot="{ id }" :label="t('setup.searchMust')" :hint="t('setup.commaHint')">
          <FnInput :id="id" v-model="editingSearch.must" />
        </FnField>
        <FnField v-slot="{ id }" :label="t('setup.searchNice')" :hint="t('setup.commaHint')">
          <FnInput :id="id" v-model="editingSearch.nice" />
        </FnField>
        <FnField v-slot="{ id }" :label="t('setup.searchPlace')">
          <FnInput :id="id" v-model="editingSearch.place" />
        </FnField>
        <FnField v-slot="{ id }" :label="t('setup.searchMode')">
          <FnSelect
            :id="id"
            v-model="editingSearch.workMode"
            :options="[
              { value: '', label: t('setup.modeAny') },
              { value: 'remote', label: t('setup.modeRemote') },
              { value: 'hybrid', label: t('setup.modeHybrid') },
              { value: 'on_site', label: t('setup.modeOnsite') },
            ]"
            :aria-label="t('setup.searchMode')"
          />
        </FnField>
        <FnField v-slot="{ id }" :label="t('setup.howMuch')">
          <FnSelect
            :id="id"
            v-model="editingSearch.autonomy"
            :options="[
              { value: 'discover', label: t('tracks.autonomyDiscover') },
              { value: 'prepare', label: t('tracks.autonomyPrepare') },
              { value: 'assist', label: t('tracks.autonomyAssist') },
            ]"
            :aria-label="t('setup.howMuch')"
          />
        </FnField>
        <FnField v-slot="{ id }" :label="t('setup.searchFrequency')">
          <FnSelect
            :id="id"
            v-model="editingSearch.preset"
            :options="[
              { value: 'every_4_hours', label: t('setup.freq4') },
              { value: 'every_2_hours', label: t('setup.freq2') },
              { value: 'daily_morning', label: t('setup.freqDaily') },
            ]"
            :aria-label="t('setup.searchFrequency')"
          />
        </FnField>
        <FnField v-slot="{ id }" :label="t('setup.searchCap')">
          <FnInput
            :id="id"
            v-model.number="editingSearch.dailyCap"
            type="number"
            inputmode="numeric"
          />
        </FnField>
      </div>
      <template #footer>
        <FnButton tone="quiet" @click="editOpen = false">{{ t("setup.close") }}</FnButton>
        <FnButton tone="primary" @click="saveSearchEdit">{{ t("setup.saveSearch") }}</FnButton>
      </template>
    </FnDialog>
  </div>
</template>
