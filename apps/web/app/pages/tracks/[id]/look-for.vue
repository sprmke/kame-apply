<script setup lang="ts">
import {
  getTrackApiV1TracksTrackIdGet,
  putCriteriaApiV1TracksTrackIdCriteriaPut,
  relaxationsApiV1TracksTrackIdRelaxationsGet,
  suggestCriteriaApiV1TracksTrackIdCriteriaSuggestPost,
  type CriteriaV1,
  type TrackDetail,
} from "@kame/api-client";
import {
  FnButton,
  FnChip,
  FnField,
  FnInput,
  FnSectionCard,
  FnSelect,
  FnSummaryLine,
  FnTextarea,
  useToast,
  type SelectOption,
} from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const route = useRoute();
const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();

const trackId = computed(() => String(route.params.id));
const nl = ref("");
const saving = ref(false);
const compiling = ref(false);
const diff = ref<{ label?: string; op?: string }[]>([]);
const preview = ref<CriteriaV1 | null>(null);

const relaxations = useQuery({
  queryKey: computed(() => ["track-relaxations", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await relaxationsApiV1TracksTrackIdRelaxationsGet({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    return data ?? [];
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});

const place = ref("");
const radiusKm = ref(25);
const REGION_ANY = "any";
const regionPreset = ref(REGION_ANY);
const visa = ref(false);
const salaryMin = ref<number | null>(null);
const salaryCurrency = ref("USD");
const salaryPeriod = ref<"hour" | "day" | "month" | "year">("month");
const includeExpr = ref("");
const excludeExpr = ref("");
const companiesInclude = ref("");
const companiesExclude = ref("");
const tzOverlap = ref(4);
const workModes = ref<string[]>([]);
const employmentTypes = ref<string[]>([]);
const postingAge = ref(0);

const detail = useQuery({
  queryKey: computed(() => ["track", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await getTrackApiV1TracksTrackIdGet({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    return data as TrackDetail;
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});

const track = computed(() => detail.data.value ?? null);
const criteria = computed(() => track.value?.criteria.structured as CriteriaV1 | undefined);
const shown = computed(() => preview.value ?? criteria.value);

function hydrateFilters(c: CriteriaV1) {
  place.value = c.locations?.[0]?.place ?? "";
  radiusKm.value = c.locations?.[0]?.radius_km ?? 25;
  regionPreset.value = c.remote_eligibility?.regions?.[0] ?? REGION_ANY;
  visa.value = c.visa_sponsorship === true;
  salaryMin.value = c.salary?.min ?? null;
  salaryCurrency.value = c.salary?.currency ?? "USD";
  salaryPeriod.value = (c.salary?.period as typeof salaryPeriod.value) ?? "month";
  includeExpr.value = c.keywords?.include_expr ?? "";
  excludeExpr.value = c.keywords?.exclude_expr ?? "";
  companiesInclude.value = (c.companies?.include ?? []).join(", ");
  companiesExclude.value = (c.companies?.exclude ?? []).join(", ");
  tzOverlap.value = c.remote_eligibility?.timezone_overlap_hours ?? 4;
  workModes.value = [...(c.work_modes ?? [])];
  employmentTypes.value = [...(c.employment_types ?? [])];
  postingAge.value = c.posting_max_age_days ?? 0;
}

function hydrate(d: TrackDetail | null | undefined) {
  if (!d) return;
  nl.value = d.criteria.nl_text || "";
  hydrateFilters(d.criteria.structured as CriteriaV1);
}

watch(() => detail.data.value, hydrate, { immediate: true });

watch(nl, () => {
  preview.value = null;
  diff.value = [];
});

function splitCsv(raw: string): string[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

const radiusText = computed({
  get: () => String(radiusKm.value ?? ""),
  set: (value: string | number) => {
    const text = String(value ?? "");
    radiusKm.value = text.trim() === "" ? 0 : Number(text);
  },
});
const salaryText = computed({
  get: () => (salaryMin.value == null ? "" : String(salaryMin.value)),
  set: (value: string | number) => {
    const text = String(value ?? "");
    salaryMin.value = text.trim() === "" ? null : Number(text);
  },
});

const savedText = computed(() => track.value?.criteria.nl_text ?? "");
const briefDirty = computed(
  () => nl.value.trim() !== savedText.value.trim() && Boolean(nl.value.trim()),
);

const periodOptions: SelectOption[] = [
  { value: "hour", label: t("tracks.perHour") },
  { value: "day", label: t("tracks.perDay") },
  { value: "month", label: t("tracks.perMonth") },
  { value: "year", label: t("tracks.perYear") },
];
const regionOptions = computed<SelectOption[]>(() => [
  { value: REGION_ANY, label: t("tracks.regionAny") },
  ...["APAC", "EU", "LATAM", "MENA", "NA", "AFRICA"].map((r) => ({ value: r, label: r })),
]);
const postingAgeText = computed({
  get: () => String(postingAge.value || 0),
  set: (value: string) => {
    postingAge.value = Number(value) || 0;
  },
});
const postingOptions = computed<SelectOption[]>(() => [
  { value: "0", label: t("tracks.postedAny") },
  ...[7, 14, 21, 30].map((n) => ({ value: String(n), label: t("tracks.postedDays", { n }) })),
]);

const modeValues = ["remote", "hybrid", "on_site"];
const employmentValues = [
  "full_time",
  "part_time",
  "contract",
  "freelance",
  "internship",
  "temporary",
];

const activeFilterCount = computed(() => {
  let n = 0;
  n += workModes.value.length;
  n += employmentTypes.value.length;
  if (postingAge.value > 0) n += 1;
  if (place.value.trim()) n += 1;
  if (salaryMin.value != null) n += 1;
  if (visa.value) n += 1;
  if (regionPreset.value !== REGION_ANY) n += 1;
  if (includeExpr.value.trim()) n += 1;
  if (excludeExpr.value.trim()) n += 1;
  if (companiesInclude.value.trim()) n += 1;
  if (companiesExclude.value.trim()) n += 1;
  return n;
});

const summaryLine = computed(() => {
  const c = shown.value;
  if (!c) return "";
  const titles = c.titles?.filter((x) => !x.exclude).length ?? 0;
  const skills = (c.skills?.must?.length ?? 0) + (c.skills?.nice?.length ?? 0);
  const days = c.posting_max_age_days ?? 21;
  return t("tracks.describeSummary", { n: titles, m: skills, days });
});

async function invalidate() {
  await qc.invalidateQueries({ queryKey: ["track", ws.currentId, trackId.value] });
  await qc.invalidateQueries({ queryKey: ["tracks", ws.currentId] });
}

async function saveCriteria(next: CriteriaV1) {
  saving.value = true;
  try {
    await putCriteriaApiV1TracksTrackIdCriteriaPut({
      path: { track_id: trackId.value },
      body: { criteria: next, nl_text: nl.value },
      throwOnError: true,
    });
    await invalidate();
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    saving.value = false;
  }
}

async function review() {
  if (!nl.value.trim()) return;
  compiling.value = true;
  try {
    const { data } = await suggestCriteriaApiV1TracksTrackIdCriteriaSuggestPost({
      path: { track_id: trackId.value },
      body: { text: nl.value, apply: false },
      throwOnError: true,
    });
    if (!data) return;
    const next = data.diff ?? [];
    if (!next.length) {
      preview.value = null;
      diff.value = [];
      toast.push({ title: t("tracks.noChanges"), tone: "neutral" });
      return;
    }
    preview.value = data.criteria as CriteriaV1;
    hydrateFilters(data.criteria as CriteriaV1);
    diff.value = next;
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    compiling.value = false;
  }
}

async function applyPreview() {
  if (!preview.value) return;
  compiling.value = true;
  try {
    await putCriteriaApiV1TracksTrackIdCriteriaPut({
      path: { track_id: trackId.value },
      body: { criteria: preview.value, nl_text: nl.value },
      throwOnError: true,
    });
    preview.value = null;
    diff.value = [];
    await invalidate();
    toast.push({ title: t("common.saved"), tone: "neutral" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    compiling.value = false;
  }
}

function dismissPreview() {
  preview.value = null;
  diff.value = [];
  if (criteria.value) hydrateFilters(criteria.value);
}

function updateSkills(patch: { must?: string[]; nice?: string[]; exclude?: string[] }) {
  const c = preview.value ?? criteria.value;
  if (!c) return;
  const skills = {
    must: patch.must ?? c.skills?.must ?? [],
    nice: patch.nice ?? c.skills?.nice ?? [],
    exclude: patch.exclude ?? c.skills?.exclude ?? [],
  };
  if (preview.value) {
    preview.value = { ...c, skills };
    return;
  }
  void saveCriteria({ ...c, skills });
}

function removeMustSkill(skill: string) {
  const c = preview.value ?? criteria.value;
  if (!c) return;
  updateSkills({ must: (c.skills?.must ?? []).filter((s) => s !== skill) });
}

function removeNiceSkill(skill: string) {
  const c = preview.value ?? criteria.value;
  if (!c) return;
  updateSkills({ nice: (c.skills?.nice ?? []).filter((s) => s !== skill) });
}

function toggleAgencies() {
  const c = preview.value ?? criteria.value;
  if (!c) return;
  const companies = {
    include: c.companies?.include ?? [],
    exclude: c.companies?.exclude ?? [],
    sizes: c.companies?.sizes ?? [],
    industries: c.companies?.industries ?? [],
    stages: c.companies?.stages ?? [],
    exclude_agencies: !c.companies?.exclude_agencies,
  };
  if (preview.value) {
    preview.value = { ...c, companies };
    return;
  }
  void saveCriteria({ ...c, companies });
}

function toggleMode(mode: string) {
  workModes.value = workModes.value.includes(mode)
    ? workModes.value.filter((m) => m !== mode)
    : [...workModes.value, mode];
}

function toggleEmployment(type: string) {
  employmentTypes.value = employmentTypes.value.includes(type)
    ? employmentTypes.value.filter((x) => x !== type)
    : [...employmentTypes.value, type];
}

async function saveMore() {
  const c = preview.value ?? criteria.value;
  if (!c) return;
  const regions =
    regionPreset.value === REGION_ANY
      ? (c.remote_eligibility?.regions ?? [])
      : [regionPreset.value];
  const locations = place.value.trim()
    ? [{ place: place.value.trim(), radius_km: radiusKm.value || null }]
    : [];
  await saveCriteria({
    ...c,
    work_modes: workModes.value as CriteriaV1["work_modes"],
    employment_types: employmentTypes.value as CriteriaV1["employment_types"],
    posting_max_age_days: postingAge.value > 0 ? postingAge.value : null,
    visa_sponsorship: visa.value ? true : null,
    locations,
    remote_eligibility: {
      anywhere: c.remote_eligibility?.anywhere ?? false,
      regions,
      countries: c.remote_eligibility?.countries ?? [],
      timezone_overlap_hours: tzOverlap.value,
      base_tz: c.remote_eligibility?.base_tz ?? null,
    },
    salary:
      salaryMin.value != null
        ? {
            min: salaryMin.value,
            max: null,
            currency: salaryCurrency.value,
            period: salaryPeriod.value,
            hide_unspecified: c.salary?.hide_unspecified ?? false,
          }
        : null,
    keywords: {
      include_expr: includeExpr.value.trim() || null,
      exclude_expr: excludeExpr.value.trim() || null,
    },
    companies: {
      include: splitCsv(companiesInclude.value),
      exclude: splitCsv(companiesExclude.value),
      sizes: c.companies?.sizes ?? [],
      industries: c.companies?.industries ?? [],
      stages: c.companies?.stages ?? [],
      exclude_agencies: c.companies?.exclude_agencies ?? false,
    },
  });
  preview.value = null;
  diff.value = [];
  toast.push({ title: t("common.saved"), tone: "neutral" });
}
</script>

<template>
  <TrackShell :track-id="trackId">
    <div v-if="track" class="flex flex-col gap-5">
      <FilledFromResume page="searches" :control="t('setup.control.searches')" />
      <FnSectionCard :title="t('tracks.whatToLookFor')" :intro="t('tracks.whatToLookForIntro')">
        <FnField v-slot="{ id }" :label="t('tracks.describe')">
          <FnTextarea :id="id" v-model="nl" :rows="4" />
        </FnField>
        <div class="flex flex-wrap items-center gap-2">
          <FnButton tone="quiet" :disabled="!nl.trim() || compiling" @click="review">
            {{ compiling ? t("tracks.suggesting") : t("tracks.checkSettings") }}
          </FnButton>
          <span v-if="briefDirty" class="text-sm text-ink-600">{{ t("common.unsaved") }}</span>
        </div>

        <div
          v-if="preview"
          class="flex flex-col gap-3 rounded-lg border border-dashed border-pencil bg-paper-0 p-4"
        >
          <p class="text-sm font-semibold text-ink-900">{{ t("tracks.changesTitle") }}</p>
          <ul class="flex flex-col gap-1 text-sm text-pencil">
            <li v-for="(d, i) in diff" :key="i">{{ d.label || d.op }}</li>
          </ul>
          <div class="flex flex-wrap gap-2">
            <FnButton tone="primary" :disabled="compiling" @click="applyPreview">
              {{ t("tracks.useSuggestions") }}
            </FnButton>
            <FnButton tone="ghost" @click="dismissPreview">
              {{ t("tracks.discardSuggestions") }}
            </FnButton>
          </div>
        </div>

        <FnSummaryLine v-if="summaryLine" :text="summaryLine" />
        <div v-if="relaxations.data.value?.length" class="flex flex-col gap-1 text-sm text-ink-600">
          <p class="font-semibold text-ink-900">{{ t("tracks.relaxTitle") }}</p>
          <ul class="flex flex-wrap gap-2">
            <li
              v-for="row in relaxations.data.value.slice(0, 4)"
              :key="row.label"
              class="rounded-full bg-paper-2 px-3 py-1"
            >
              {{ row.label }}: +{{ row.gained }}
            </li>
          </ul>
        </div>
      </FnSectionCard>

      <FnSectionCard :title="t('tracks.matchesOn')" :intro="t('tracks.matchesOnIntro')">
        <div class="grid gap-4 sm:grid-cols-2">
          <div v-if="shown?.titles?.filter((x) => !x.exclude).length" class="flex flex-col gap-2">
            <h3 class="text-xs font-semibold tracking-wide text-ink-600 uppercase">
              {{ t("tracks.groupRoles") }}
            </h3>
            <div class="flex flex-wrap gap-2">
              <FnChip
                v-for="title in shown?.titles?.filter((x) => !x.exclude) ?? []"
                :key="title.title"
                tone="accent"
                >{{ title.title }}</FnChip
              >
            </div>
          </div>
          <div v-if="shown?.skills?.must?.length" class="flex flex-col gap-2">
            <h3 class="text-xs font-semibold tracking-wide text-ink-600 uppercase">
              {{ t("tracks.groupSkills") }}
            </h3>
            <div class="flex flex-wrap gap-2">
              <FnChip
                v-for="s in shown?.skills?.must ?? []"
                :key="`m-${s}`"
                tone="neutral"
                removable
                :remove-label="t('tracks.removeChip')"
                @remove="removeMustSkill(s)"
                >{{ s }}</FnChip
              >
            </div>
          </div>
          <div v-if="shown?.skills?.nice?.length" class="flex flex-col gap-2">
            <h3 class="text-xs font-semibold tracking-wide text-ink-600 uppercase">
              {{ t("tracks.groupNice") }}
            </h3>
            <div class="flex flex-wrap gap-2">
              <FnChip
                v-for="s in shown?.skills?.nice ?? []"
                :key="`n-${s}`"
                tone="pencil"
                removable
                :remove-label="t('tracks.removeChip')"
                @remove="removeNiceSkill(s)"
                >{{ s }}</FnChip
              >
            </div>
          </div>
          <div class="flex flex-col gap-2">
            <h3 class="text-xs font-semibold tracking-wide text-ink-600 uppercase">
              {{ t("tracks.groupRules") }}
            </h3>
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                class="inline-flex min-h-11 items-center gap-1.5 rounded-full border px-4 text-xs font-semibold transition-colors"
                :class="
                  shown?.companies?.exclude_agencies
                    ? 'border-rule bg-paper-2 text-ink-900'
                    : 'border-dashed border-edge bg-paper-1 text-ink-600 hover:bg-paper-2'
                "
                :aria-pressed="Boolean(shown?.companies?.exclude_agencies)"
                @click="toggleAgencies"
              >
                <span aria-hidden="true">{{ shown?.companies?.exclude_agencies ? "✓" : "+" }}</span>
                {{ t("tracks.noAgencies") }}
              </button>
              <FnChip v-for="s in shown?.skills?.exclude ?? []" :key="`x-${s}`" tone="neutral"
                >-{{ s }}</FnChip
              >
            </div>
          </div>
        </div>
      </FnSectionCard>

      <FnSectionCard
        :title="t('tracks.filters')"
        :intro="t('tracks.filtersIntro')"
        :summary="
          activeFilterCount
            ? t('tracks.filtersOn', { n: activeFilterCount }, activeFilterCount)
            : t('tracks.filtersNone')
        "
      >
        <div class="grid gap-4 sm:grid-cols-2">
          <fieldset class="flex flex-col gap-1">
            <legend class="text-sm font-semibold text-ink-900">{{ t("tracks.workModes") }}</legend>
            <label
              v-for="m in modeValues"
              :key="m"
              class="flex min-h-11 items-center gap-3 text-sm text-ink-900"
            >
              <input
                type="checkbox"
                class="size-5 rounded border-rule accent-brand-600"
                :checked="workModes.includes(m)"
                @change="toggleMode(m)"
              />
              {{ t(`tracks.mode_${m}`) }}
            </label>
          </fieldset>
          <fieldset class="flex flex-col gap-1">
            <legend class="text-sm font-semibold text-ink-900">
              {{ t("tracks.employment") }}
            </legend>
            <label
              v-for="e in employmentValues"
              :key="e"
              class="flex min-h-11 items-center gap-3 text-sm text-ink-900"
            >
              <input
                type="checkbox"
                class="size-5 rounded border-rule accent-brand-600"
                :checked="employmentTypes.includes(e)"
                @change="toggleEmployment(e)"
              />
              {{ t(`tracks.emp_${e}`) }}
            </label>
          </fieldset>
          <FnField v-slot="{ id }" :label="t('tracks.postedWithin')" :help="t('tracks.postedHelp')">
            <FnSelect :id="id" v-model="postingAgeText" :options="postingOptions" />
          </FnField>
          <FnField v-slot="{ id }" :label="t('tracks.location')" :help="t('tracks.locationHelp')">
            <FnInput :id="id" v-model="place" :placeholder="t('tracks.locationPlaceholder')" />
          </FnField>
          <FnField v-slot="{ id }" :label="t('tracks.radius')">
            <FnInput :id="id" v-model="radiusText" type="number" />
          </FnField>
          <FnField v-slot="{ id }" :label="t('tracks.region')">
            <FnSelect :id="id" v-model="regionPreset" :options="regionOptions" />
          </FnField>
          <label class="flex flex-col gap-2 text-sm">
            <span class="font-semibold text-ink-900">{{ t("tracks.tzOverlap") }}</span>
            <input
              v-model.number="tzOverlap"
              type="range"
              min="0"
              max="12"
              class="min-h-11 w-full accent-brand-600"
            />
            <span class="text-sm tabular-nums text-ink-600">{{ tzOverlap }}h</span>
          </label>
          <label class="flex min-h-11 items-center gap-3 text-sm text-ink-900">
            <input
              v-model="visa"
              type="checkbox"
              class="size-5 rounded border-rule accent-brand-600"
            />
            {{ t("tracks.visa") }}
          </label>
          <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:gap-2">
            <FnField :label="t('tracks.salaryMin')" class="flex-1">
              <template #default="{ id }">
                <FnInput :id="id" v-model="salaryText" type="number" inputmode="numeric" />
              </template>
            </FnField>
            <FnField :label="t('tracks.currency')" class="sm:w-24">
              <template #default="{ id }">
                <FnInput :id="id" v-model="salaryCurrency" maxlength="3" />
              </template>
            </FnField>
            <FnField :label="t('tracks.period')" class="sm:w-32">
              <template #default="{ id }">
                <FnSelect :id="id" v-model="salaryPeriod" :options="periodOptions" />
              </template>
            </FnField>
          </div>
          <FnField :label="t('tracks.keywordsInclude')" :help="t('tracks.keywordsIncludeHelp')">
            <template #default="{ id }">
              <FnInput :id="id" v-model="includeExpr" placeholder="support, onboarding" />
            </template>
          </FnField>
          <FnField :label="t('tracks.keywordsExclude')">
            <template #default="{ id }">
              <FnInput :id="id" v-model="excludeExpr" placeholder="unpaid, commission only" />
            </template>
          </FnField>
          <FnField :label="t('tracks.companiesInclude')">
            <template #default="{ id }">
              <FnInput :id="id" v-model="companiesInclude" />
            </template>
          </FnField>
          <FnField :label="t('tracks.companiesExclude')">
            <template #default="{ id }">
              <FnInput :id="id" v-model="companiesExclude" />
            </template>
          </FnField>
        </div>
        <div class="flex flex-wrap gap-2">
          <FnButton tone="primary" :disabled="saving" @click="saveMore">
            {{ saving ? t("common.saving") : t("tracks.saveFilters") }}
          </FnButton>
          <FnButton as-child tone="quiet">
            <NuxtLink :to="`/jobs?track=${trackId}`">{{ t("tracks.viewMatches") }}</NuxtLink>
          </FnButton>
        </div>
      </FnSectionCard>
    </div>
  </TrackShell>
</template>
