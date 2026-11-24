<script setup lang="ts">
import {
  applyChangesApiV1ResumesVersionIdApplyPost,
  bulkDecideApiV1ResumesVersionIdChangesBulkPost,
  computeInsightsApiV1TracksTrackIdInsightsPost,
  createResumeApiV1ResumesPost,
  critiqueResumeApiV1ResumesVersionIdCritiquePost,
  decideChangeApiV1ResumeChangesChangeIdPost,
  getInsightsApiV1TracksTrackIdInsightsGet,
  parseViewApiV1ResumesVersionIdParseViewGet,
  improveResumeApiV1ResumesVersionIdImprovePost,
  listChangesApiV1ResumesVersionIdChangesGet,
  listProfilesApiV1ProfilesGet,
  listResumesApiV1ResumesGet,
  listTracksApiV1TracksGet,
  renderResumeApiV1ResumesVersionIdRenderPost,
  type ChangeRead,
  type CritiqueRead,
  type InsightsRead,
  type ParseViewRead,
  type ResumeVersionRead,
} from "@kame/api-client";
import {
  FnButton,
  FnChip,
  FnSectionCard,
  FnSelect,
  FnSkeleton,
  FnSkeletonGroup,
  useToast,
} from "@kame/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const route = useRoute();
const router = useRouter();

type Tab = "critique" | "diff" | "insights" | "skim" | "parse";

const tab = ref<Tab>("critique");
const trackId = computed(() => (route.query.track as string) || "");
const selectedId = ref<string | null>(null);
const template = ref("classic");
const pageSize = ref<"letter" | "a4">("letter");
const templateOptions = computed(() => [
  { value: "classic", label: t("studio.templateClassic") },
  { value: "compact", label: t("studio.templateCompact") },
  { value: "modern", label: t("studio.templateModern") },
  { value: "serif", label: t("studio.templateSerif") },
]);
const pageOptions = computed(() => [
  { value: "letter", label: t("studio.pageLetter") },
  { value: "a4", label: t("studio.pageA4") },
]);
const pageValue = computed({
  get: () => pageSize.value,
  set: (value: string) => {
    pageSize.value = value as typeof pageSize.value;
  },
});
const renderUrls = ref<{ pdf?: string | null; docx?: string | null; txt?: string | null }>({});
const parseGate = ref<Record<string, unknown> | null>(null);

const tracks = useQuery({
  queryKey: computed(() => ["tracks", ws.currentId]),
  queryFn: async () => {
    const { data } = await listTracksApiV1TracksGet({ throwOnError: true });
    return data ?? [];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});
const ALL_TRACKS = "__all__";
const trackOptions = computed(() => [
  { value: ALL_TRACKS, label: t("studio.allSearches") },
  ...(tracks.data.value ?? []).map((tr) => ({ value: String(tr.id), label: tr.name })),
]);
/** Insights need a search. Fall back to the newest one so the tab is never empty. */
const activeTrackId = computed(() => trackId.value || String(tracks.data.value?.[0]?.id ?? ""));
const trackValue = computed({
  get: () => trackId.value || ALL_TRACKS,
  set: (value: string) => setTrack(value === ALL_TRACKS ? "" : value),
});

const profiles = useQuery({
  queryKey: computed(() => ["profiles", ws.currentId]),
  queryFn: async () => {
    const { data } = await listProfilesApiV1ProfilesGet({ throwOnError: true });
    return data ?? [];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const resumes = useQuery({
  queryKey: computed(() => ["resumes", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await listResumesApiV1ResumesGet({
      query: trackId.value ? { track_id: trackId.value } : {},
      throwOnError: true,
    });
    return (data ?? []) as ResumeVersionRead[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

watch(
  () => resumes.data.value,
  (rows) => {
    if (!rows?.length) {
      selectedId.value = null;
      return;
    }
    const first = rows[0];
    if (first && (!selectedId.value || !rows.some((r) => String(r.id) === selectedId.value))) {
      selectedId.value = String(first.id);
    }
  },
  { immediate: true },
);

const selected = computed(
  () => resumes.data.value?.find((r) => String(r.id) === selectedId.value) ?? null,
);

const critiqueQ = useQuery({
  queryKey: computed(() => ["resume-critique", selectedId.value]),
  queryFn: async () => {
    const c = selected.value?.critique as CritiqueRead | undefined;
    return c && Object.keys(c).length ? c : null;
  },
  enabled: computed(() => Boolean(selectedId.value)),
});

const changesQ = useQuery({
  queryKey: computed(() => ["resume-changes", selectedId.value]),
  queryFn: async () => {
    const { data } = await listChangesApiV1ResumesVersionIdChangesGet({
      path: { version_id: selectedId.value! },
      throwOnError: true,
    });
    return (data ?? []) as ChangeRead[];
  },
  enabled: computed(() => Boolean(selectedId.value)),
});

const insightsQ = useQuery({
  queryKey: computed(() => ["track-insights", activeTrackId.value]),
  queryFn: async () => {
    const { data } = await getInsightsApiV1TracksTrackIdInsightsGet({
      path: { track_id: activeTrackId.value },
      query: { window_days: 30 },
      throwOnError: true,
    });
    return data as InsightsRead;
  },
  enabled: computed(() => Boolean(activeTrackId.value) && tab.value === "insights"),
});

const parseQ = useQuery({
  queryKey: computed(() => ["resume-parse", selectedId.value]),
  queryFn: async () => {
    const { data } = await parseViewApiV1ResumesVersionIdParseViewGet({
      path: { version_id: selectedId.value! },
      throwOnError: true,
    });
    return data as ParseViewRead;
  },
  enabled: computed(() => Boolean(selectedId.value) && tab.value === "parse"),
});

function setTrack(id: string) {
  router.replace({ query: { ...route.query, track: id || undefined } });
}

const createMut = useMutation({
  mutationFn: async () => {
    const tid = trackId.value;
    const track = tracks.data.value?.find((tr) => String(tr.id) === tid);
    const profileId = track?.profile_id || profiles.data.value?.[0]?.id;
    if (!profileId) throw new Error("No profile");
    const { data } = await createResumeApiV1ResumesPost({
      body: {
        profile_id: String(profileId),
        track_id: tid || null,
        label: track?.name || t("studio.baseResume"),
        template: template.value,
        page_size: pageSize.value,
      },
      throwOnError: true,
    });
    return data as ResumeVersionRead;
  },
  onSuccess: async (data) => {
    selectedId.value = String(data.id);
    await qc.invalidateQueries({ queryKey: ["resumes"] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const critiqueMut = useMutation({
  mutationFn: async () => {
    const { data } = await critiqueResumeApiV1ResumesVersionIdCritiquePost({
      path: { version_id: selectedId.value! },
      throwOnError: true,
    });
    return data as CritiqueRead;
  },
  onSuccess: async () => {
    tab.value = "critique";
    await qc.invalidateQueries({ queryKey: ["resumes"] });
    await qc.invalidateQueries({ queryKey: ["resume-critique"] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const improveMut = useMutation({
  mutationFn: async () => {
    const { data } = await improveResumeApiV1ResumesVersionIdImprovePost({
      path: { version_id: selectedId.value! },
      body: { window_days: 30 },
      throwOnError: true,
    });
    return data;
  },
  onSuccess: async () => {
    tab.value = "diff";
    await qc.invalidateQueries({ queryKey: ["resume-changes"] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const insightsMut = useMutation({
  mutationFn: async () => {
    const { data } = await computeInsightsApiV1TracksTrackIdInsightsPost({
      path: { track_id: activeTrackId.value },
      query: { window_days: 30 },
      throwOnError: true,
    });
    return data;
  },
  onSuccess: async () => {
    tab.value = "insights";
    await qc.invalidateQueries({ queryKey: ["track-insights"] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const renderMut = useMutation({
  mutationFn: async () => {
    const { data } = await renderResumeApiV1ResumesVersionIdRenderPost({
      path: { version_id: selectedId.value! },
      body: { template: template.value, page_size: pageSize.value },
      throwOnError: true,
    });
    return data;
  },
  onSuccess: async (data) => {
    renderUrls.value = {
      pdf: data?.pdf_url,
      docx: data?.docx_url,
      txt: data?.txt_url,
    };
    parseGate.value = (data?.parse_gate as Record<string, unknown>) || null;
    await qc.invalidateQueries({ queryKey: ["resumes"] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

async function decide(changeId: string, status: "accepted" | "rejected") {
  try {
    await decideChangeApiV1ResumeChangesChangeIdPost({
      path: { change_id: changeId },
      body: { status },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["resume-changes"] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function bulk(status: "accepted" | "rejected") {
  try {
    await bulkDecideApiV1ResumesVersionIdChangesBulkPost({
      path: { version_id: selectedId.value! },
      body: { status },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["resume-changes"] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function applyAccepted() {
  try {
    await applyChangesApiV1ResumesVersionIdApplyPost({
      path: { version_id: selectedId.value! },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["resumes", "resume-changes"] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

// The check is deterministic and cheap; run it once when a resume has none.
const autoChecked = new Set<string>();
watch(
  [selected, () => critiqueMut.isPending.value],
  ([row, busy]) => {
    if (!row || busy) return;
    const id = String(row.id);
    if (autoChecked.has(id)) return;
    const hasCritique = row.critique && Object.keys(row.critique).length > 0;
    if (hasCritique) return;
    autoChecked.add(id);
    critiqueMut.mutate();
  },
  { immediate: true },
);

const critique = computed(() => {
  const live = critiqueMut.data.value;
  if (live) return live;
  return (selected.value?.critique as CritiqueRead | undefined) || critiqueQ.data.value;
});

const skim = computed(() => {
  const c = critique.value as CritiqueRead | null | undefined;
  return (c?.skim_zone as { summary?: string; first_role?: string } | undefined) || null;
});

const activeInsights = computed(
  () => (insightsMut.data.value || insightsQ.data.value || null) as InsightsRead | null,
);

const insightSkills = computed(() => {
  const raw = (activeInsights.value?.skills || []) as Array<{
    name: string;
    frequency: number;
    status: string;
  }>;
  return raw;
});

const insightTitles = computed(() => {
  const raw = (activeInsights.value?.titles || []) as Array<{ title?: string; count?: number }>;
  return raw.slice(0, 8).map((ti) => ({ title: ti.title || "", count: ti.count || 0 }));
});

function skillTone(status: string): "neutral" | "accent" | "pencil" {
  if (status === "have_shown") return "accent";
  if (status === "have_not_shown") return "pencil";
  return "neutral";
}

const tabs = computed(() => [
  { value: "critique" as Tab, label: t("studio.tabs.critique") },
  { value: "diff" as Tab, label: t("studio.tabs.diff") },
  { value: "insights" as Tab, label: t("studio.tabs.insights") },
  { value: "skim" as Tab, label: t("studio.tabs.skim") },
  { value: "parse" as Tab, label: t("studio.tabs.parse") },
]);

function categoryLabel(key: string): string {
  const known = [
    "parseability",
    "targeting",
    "evidence",
    "market_fit",
    "clarity",
    "authenticity",
    "consistency",
    "skim",
  ];
  return known.includes(key) ? t(`studio.categories.${key}`) : key;
}

function insightStatusLabel(status: string): string {
  if (status === "have_shown") return t("studio.statusHaveShown");
  if (status === "have_not_shown") return t("studio.statusHaveNotShown");
  return t("studio.statusMissing");
}

const resumeOptions = computed(() =>
  (resumes.data.value ?? []).map((r) => ({
    value: String(r.id),
    label: r.label || t("studio.resumeLabel"),
  })),
);
const resumeValue = computed({
  get: () => selectedId.value ?? "",
  set: (value: string) => {
    selectedId.value = value || null;
  },
});

const contentPreview = computed(() => {
  const c = selected.value?.content as Record<string, unknown> | undefined;
  if (!c) return "";
  const contact = (c.contact || {}) as { full_name?: string; email?: string; location?: string };
  const summary = (c.summary as { text?: string } | undefined)?.text || "";
  const sections =
    (c.sections as Array<{
      heading?: string;
      lines?: { text: string }[];
      items?: { title?: string; subtitle?: string; lines?: { text: string }[] }[];
    }>) || [];
  const parts = [
    contact.full_name || "",
    [contact.email, contact.location].filter(Boolean).join(" · "),
  ];
  if (summary) parts.push("", summary);
  for (const sec of sections) {
    parts.push("", (sec.heading || "").toUpperCase());
    for (const line of sec.lines || []) parts.push(`• ${line.text}`);
    for (const item of sec.items || []) {
      parts.push([item.title, item.subtitle].filter(Boolean).join(", "));
      for (const line of item.lines || []) parts.push(`• ${line.text}`);
    }
  }
  return parts.filter((p) => p !== undefined).join("\n");
});
</script>

<template>
  <div class="mx-auto flex w-full max-w-6xl flex-col gap-5">
    <PageHeader :title="t('nav.studio')" :lede="t('studio.lede')">
      <template #actions>
        <FnButton
          v-if="resumes.data.value?.length"
          size="sm"
          tone="primary"
          :disabled="!selectedId || renderMut.isPending.value"
          :loading="renderMut.isPending.value"
          @click="renderMut.mutate()"
        >
          {{ t("studio.download") }}
        </FnButton>
      </template>
    </PageHeader>

    <FnSkeletonGroup
      v-if="resumes.isPending.value"
      :label="t('common.loading')"
      class="flex flex-col gap-5"
    >
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <FnSkeleton class="h-12 w-full rounded-md lg:max-w-xs" />
        <div class="flex flex-wrap items-center gap-2">
          <FnSkeleton class="h-12 w-36 rounded-md" />
          <FnSkeleton class="h-11 w-28 rounded-md" />
        </div>
      </div>

      <div class="flex flex-col gap-2">
        <div class="flex gap-1 rounded-lg bg-paper-2 p-1">
          <FnSkeleton v-for="n in 5" :key="n" class="h-11 w-24 rounded-md bg-paper-1" />
        </div>
        <FnSkeleton class="h-4 w-3/5" />
      </div>

      <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-start">
        <section
          class="min-w-0 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)] sm:p-5"
        >
          <div class="flex flex-col gap-4">
            <div class="grid gap-2 sm:grid-cols-2">
              <div
                v-for="n in 6"
                :key="n"
                class="flex items-center justify-between gap-2 rounded-lg border border-rule bg-paper-0 px-3 py-2"
              >
                <FnSkeleton class="h-4 w-24" />
                <FnSkeleton class="h-4 w-8" />
              </div>
            </div>
            <FnSkeleton class="h-5 w-32" />
            <div v-for="n in 3" :key="n" class="flex gap-2">
              <FnSkeleton class="size-5 shrink-0 rounded-full" />
              <FnSkeleton class="h-4 flex-1" />
            </div>
            <FnSkeleton class="h-11 w-36 rounded-md" />
          </div>
        </section>

        <aside
          class="flex flex-col gap-4 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
        >
          <div v-for="n in 2" :key="n" class="flex flex-col gap-2">
            <FnSkeleton class="h-4 w-24" />
            <FnSkeleton class="h-12 w-full rounded-md" />
          </div>
          <FnSkeleton class="h-4 w-4/5" />
          <FnSkeleton class="h-11 w-32 rounded-md" />
        </aside>
      </div>
    </FnSkeletonGroup>

    <FnSectionCard
      v-else-if="!(resumes.data.value || []).length"
      :title="t('studio.emptyTitle')"
      :intro="t('studio.emptyBody')"
    >
      <FnButton tone="primary" :disabled="createMut.isPending.value" @click="createMut.mutate()">
        {{ t("studio.createResume") }}
      </FnButton>
    </FnSectionCard>

    <template v-else>
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div class="w-full lg:max-w-xs">
          <FnSelect
            v-model="resumeValue"
            :options="resumeOptions"
            :aria-label="t('studio.chooseResume')"
          />
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <div class="w-36">
            <FnSelect
              v-model="trackValue"
              :options="trackOptions"
              :aria-label="t('studio.chooseSearch')"
            />
          </div>
          <FnButton
            size="sm"
            tone="quiet"
            :disabled="!selectedId || critiqueMut.isPending.value"
            @click="critiqueMut.mutate()"
          >
            {{ critiqueMut.isPending.value ? t("studio.checking") : t("studio.checkAgain") }}
          </FnButton>
        </div>
      </div>

      <div class="flex flex-col gap-2">
        <div class="flex gap-1 overflow-x-auto rounded-lg bg-paper-2 p-1" role="tablist">
          <button
            v-for="item in tabs"
            :key="item.value"
            type="button"
            role="tab"
            class="min-h-11 shrink-0 rounded-md px-3 text-sm font-semibold whitespace-nowrap transition-colors sm:px-4"
            :class="
              tab === item.value
                ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
                : 'text-ink-600 hover:text-ink-900'
            "
            :aria-selected="tab === item.value"
            @click="tab = item.value"
          >
            {{ item.label }}
          </button>
        </div>
        <p class="text-sm leading-6 text-ink-600">{{ t(`studio.help.${tab}`) }}</p>
      </div>

      <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-start">
        <section
          class="min-w-0 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)] sm:p-5"
        >
          <div v-if="!selected" class="text-sm text-ink-600">{{ t("studio.emptySelect") }}</div>

          <div v-else-if="tab === 'critique'" class="flex flex-col gap-4">
            <div v-if="critiqueMut.isPending.value" class="text-sm text-ink-600">
              {{ t("studio.checking") }}
            </div>
            <div
              v-else-if="!critique || !Object.keys(critique.categories || {}).length"
              class="flex flex-col items-start gap-3"
            >
              <p class="text-sm text-ink-600">{{ t("studio.noChanges") }}</p>
              <FnButton size="sm" tone="primary" @click="critiqueMut.mutate()">
                {{ t("studio.runCheck") }}
              </FnButton>
            </div>
            <template v-else>
              <ul class="grid gap-2 sm:grid-cols-2">
                <li
                  v-for="(cat, key) in critique.categories"
                  :key="String(key)"
                  class="flex items-center justify-between gap-2 rounded-lg border border-rule bg-paper-0 px-3 py-2 text-sm"
                >
                  <span class="font-medium text-ink-900">{{ categoryLabel(String(key)) }}</span>
                  <span class="tabular-nums text-ink-600">
                    {{ (cat as { score?: number }).score }}/{{ (cat as { max?: number }).max }}
                  </span>
                </li>
              </ul>
              <div v-if="critique.top_fixes?.length" class="flex flex-col gap-2">
                <h3 class="text-sm font-semibold text-ink-900">{{ t("studio.topFixes") }}</h3>
                <ol class="flex flex-col gap-2">
                  <li
                    v-for="(fix, i) in critique.top_fixes || []"
                    :key="i"
                    class="flex gap-2 text-sm leading-6 text-ink-900"
                  >
                    <span
                      class="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-brand-100 text-[0.6875rem] font-bold text-brand-700"
                      >{{ i + 1 }}</span
                    >
                    {{ (fix as { message?: string }).message }}
                  </li>
                </ol>
                <FnButton
                  size="sm"
                  tone="quiet"
                  class="self-start"
                  :disabled="improveMut.isPending.value"
                  @click="improveMut.mutate()"
                >
                  {{ t("studio.applyTopFixes") }}
                </FnButton>
              </div>
            </template>
          </div>

          <div v-else-if="tab === 'diff'" class="flex flex-col gap-3">
            <div class="flex flex-wrap gap-2">
              <FnButton size="sm" tone="ghost" @click="bulk('accepted')">{{
                t("studio.acceptAll")
              }}</FnButton>
              <FnButton size="sm" tone="ghost" @click="bulk('rejected')">{{
                t("studio.rejectAll")
              }}</FnButton>
              <FnButton size="sm" @click="applyAccepted">{{ t("studio.applyAccepted") }}</FnButton>
            </div>
            <FnSkeletonGroup v-if="changesQ.isPending.value" :label="t('common.loading')">
              <ul class="flex flex-col divide-y divide-rule">
                <li v-for="n in 3" :key="n" class="flex flex-col gap-2 py-3 sm:flex-row">
                  <div class="flex min-w-0 flex-1 flex-col gap-2">
                    <FnSkeleton class="h-3.5 w-2/5" />
                    <FnSkeleton class="h-4 w-3/4" />
                    <FnSkeleton class="h-4 w-2/3" />
                  </div>
                  <div class="flex shrink-0 gap-1">
                    <FnSkeleton class="h-11 w-24 rounded-md" />
                    <FnSkeleton class="h-11 w-20 rounded-md" />
                  </div>
                </li>
              </ul>
            </FnSkeletonGroup>
            <p v-else-if="!(changesQ.data.value || []).length" class="text-sm text-ink-600">
              {{ t("studio.noChanges") }}
            </p>
            <ul v-else class="flex flex-col divide-y divide-rule">
              <li
                v-for="ch in changesQ.data.value"
                :key="String(ch.id)"
                class="flex flex-col gap-2 py-3 text-sm sm:flex-row"
              >
                <div class="min-w-0 flex-1">
                  <p class="text-ink-600">{{ ch.reason }}</p>
                  <p v-if="ch.before" class="mt-1 text-ink-400 line-through">{{ ch.before }}</p>
                  <p v-if="ch.after" class="text-ink-900">{{ ch.after }}</p>
                  <p v-if="ch.ask" class="mt-1 text-brand-800">{{ ch.ask }}</p>
                </div>
                <div v-if="ch.status === 'proposed'" class="flex shrink-0 gap-1">
                  <FnButton size="sm" @click="decide(String(ch.id), 'accepted')">{{
                    t("common.confirm")
                  }}</FnButton>
                  <FnButton size="sm" tone="ghost" @click="decide(String(ch.id), 'rejected')">{{
                    t("common.delete")
                  }}</FnButton>
                </div>
              </li>
            </ul>
          </div>

          <div v-else-if="tab === 'insights'" class="flex flex-col gap-3">
            <div v-if="!activeTrackId" class="text-sm text-ink-600">
              {{ t("studio.noInsights") }}
            </div>
            <FnSkeletonGroup
              v-else-if="insightsQ.isPending.value || insightsMut.isPending.value"
              :label="t('common.loading')"
              class="flex flex-col gap-3"
            >
              <FnSkeleton class="h-4 w-3/5" />
              <div class="flex flex-col gap-2">
                <FnSkeleton class="h-4 w-full" />
                <div v-for="n in 4" :key="n" class="grid grid-cols-3 gap-2">
                  <FnSkeleton class="h-4" />
                  <FnSkeleton class="h-4 w-12" />
                  <FnSkeleton class="h-6 w-20 rounded-full" />
                </div>
              </div>
            </FnSkeletonGroup>
            <div v-else-if="activeInsights" class="flex flex-col gap-3">
              <p class="text-sm text-ink-600">
                {{ t("studio.sampleSize", { n: activeInsights.sample_size }) }}
                <span v-if="activeInsights.low_confidence"> · {{ t("studio.lowConfidence") }}</span>
              </p>
              <div class="overflow-x-auto">
                <table class="w-full min-w-[28rem] border-collapse text-left text-sm">
                  <thead>
                    <tr class="border-b border-rule text-ink-600">
                      <th class="py-1 pr-2 font-medium">{{ t("studio.colSkill") }}</th>
                      <th class="py-1 pr-2 font-medium">{{ t("studio.colFrequency") }}</th>
                      <th class="py-1 font-medium">{{ t("studio.colStatus") }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(sk, i) in insightSkills" :key="i" class="border-b border-rule">
                      <td class="py-2 pr-2">{{ sk.name }}</td>
                      <td class="py-2 pr-2 tabular-nums">{{ sk.frequency }}</td>
                      <td class="py-2">
                        <FnChip :tone="skillTone(sk.status)">{{
                          insightStatusLabel(sk.status)
                        }}</FnChip>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <ul v-if="insightTitles.length" class="text-sm text-ink-600">
                <li v-for="(ti, i) in insightTitles" :key="i">{{ ti.title }} ({{ ti.count }})</li>
              </ul>
            </div>
            <div v-else class="flex flex-col items-start gap-3">
              <p class="text-sm text-ink-600">{{ t("studio.noInsights") }}</p>
              <FnButton
                size="sm"
                tone="primary"
                :disabled="!activeTrackId"
                @click="insightsMut.mutate()"
              >
                {{ t("studio.runInsights") }}
              </FnButton>
            </div>
          </div>

          <div v-else-if="tab === 'skim'" class="flex flex-col gap-3">
            <div class="border border-brand-200 bg-brand-50/40 p-3 text-sm">
              <p class="font-medium text-ink-900">{{ t("studio.skimTitle") }}</p>
              <p class="mt-2 whitespace-pre-wrap text-ink-900">
                {{ skim?.summary || contentPreview.slice(0, 280) }}
              </p>
              <p v-if="skim?.first_role" class="mt-2 text-ink-600">{{ skim.first_role }}</p>
            </div>
            <pre
              class="overflow-x-auto whitespace-pre-wrap rounded-lg border border-rule bg-paper-0 p-3 text-xs text-ink-900"
              >{{ contentPreview }}</pre>
          </div>

          <div v-else-if="tab === 'parse'" class="flex flex-col gap-2 text-sm">
            <FnSkeletonGroup v-if="parseQ.isPending.value" :label="t('common.loading')">
              <dl class="grid gap-2 sm:grid-cols-2">
                <div
                  v-for="n in 5"
                  :key="n"
                  class="flex flex-col gap-2"
                  :class="n > 2 ? 'sm:col-span-2' : ''"
                >
                  <FnSkeleton class="h-3 w-20" />
                  <FnSkeleton class="h-4 w-3/5" />
                </div>
              </dl>
            </FnSkeletonGroup>
            <template v-else-if="parseQ.data.value">
              <dl class="grid gap-2 sm:grid-cols-2">
                <div>
                  <dt class="text-ink-600">{{ t("studio.parseName") }}</dt>
                  <dd class="text-ink-900">{{ parseQ.data.value.name || "-" }}</dd>
                </div>
                <div>
                  <dt class="text-ink-600">{{ t("studio.parseEmail") }}</dt>
                  <dd class="text-ink-900">{{ parseQ.data.value.email || "-" }}</dd>
                </div>
                <div class="sm:col-span-2">
                  <dt class="text-ink-600">{{ t("studio.parseSections") }}</dt>
                  <dd class="text-ink-900">{{ (parseQ.data.value.sections || []).join(", ") }}</dd>
                </div>
                <div class="sm:col-span-2">
                  <dt class="text-ink-600">{{ t("studio.parseEmployers") }}</dt>
                  <dd class="text-ink-900">
                    <span
                      v-for="(emp, i) in parseQ.data.value.employers || []"
                      :key="i"
                      class="block"
                    >
                      {{ (emp as { title?: string }).title }} ·
                      {{ (emp as { company?: string }).company }}
                    </span>
                  </dd>
                </div>
                <div class="sm:col-span-2">
                  <dt class="text-ink-600">{{ t("studio.parseSkills") }}</dt>
                  <dd class="text-ink-900">{{ (parseQ.data.value.skills || []).join(", ") }}</dd>
                </div>
              </dl>
            </template>
          </div>
        </section>

        <aside
          class="flex flex-col gap-4 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
        >
          <div class="flex flex-col gap-2">
            <span class="text-sm font-semibold text-ink-900">{{ t("studio.template") }}</span>
            <FnSelect
              v-model="template"
              :options="templateOptions"
              :aria-label="t('studio.template')"
            />
          </div>
          <div class="flex flex-col gap-2">
            <span class="text-sm font-semibold text-ink-900">{{ t("studio.pageSize") }}</span>
            <FnSelect
              v-model="pageValue"
              :options="pageOptions"
              :aria-label="t('studio.pageSize')"
            />
          </div>
          <p class="text-sm leading-6 text-ink-600">{{ t("studio.usedWhenRendered") }}</p>
          <div v-if="parseGate" class="text-xs text-ink-600">
            {{ t("studio.exportCheck") }}:
            {{ parseGate.ok ? t("studio.exportPassed") : t("studio.exportFailed") }}
          </div>
          <div
            v-if="renderUrls.pdf || renderUrls.docx || renderUrls.txt"
            class="flex flex-col gap-1"
          >
            <span class="text-sm font-semibold text-ink-900">{{ t("studio.downloads") }}</span>
            <a
              v-if="renderUrls.pdf"
              class="text-brand-700 underline"
              :href="renderUrls.pdf"
              target="_blank"
              rel="noopener"
              >PDF</a
            >
            <a
              v-if="renderUrls.docx"
              class="text-brand-700 underline"
              :href="renderUrls.docx"
              target="_blank"
              rel="noopener"
              >DOCX</a
            >
            <a
              v-if="renderUrls.txt"
              class="text-brand-700 underline"
              :href="renderUrls.txt"
              target="_blank"
              rel="noopener"
              >Text</a
            >
          </div>
          <FnButton
            size="sm"
            tone="quiet"
            :disabled="createMut.isPending.value"
            @click="createMut.mutate()"
          >
            {{ t("studio.newResume") }}
          </FnButton>
        </aside>
      </div>
    </template>
  </div>
</template>
