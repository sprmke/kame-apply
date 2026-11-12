<script setup lang="ts">
import {
  archiveApiV1TracksTrackIdArchivePost,
  createTrackApiV1TracksPost,
  duplicateApiV1TracksTrackIdDuplicatePost,
  listTemplatesApiV1TracksTemplatesGet,
  listTracksApiV1TracksGet,
  planSearchApiV1TracksPlanPost,
  type CriteriaV1,
  type TrackRead,
  type TrackTemplateRead,
} from "@kame/api-client";
import { FnButton, FnChip, FnFolderTab, FnInput, FnSkeleton, FnTextarea, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const { ensureProfile, profileId } = useActiveProfile();

const creating = ref(false);
const showNew = ref(false);
const showTemplates = ref(false);
const nlDraft = ref("");
const nameDraft = ref("");
const planning = ref(false);
const plan = ref<CriteriaV1 | null>(null);
const planName = ref("");

const tracks = useQuery({
  queryKey: computed(() => ["tracks", ws.currentId]),
  queryFn: async () => {
    const { data } = await listTracksApiV1TracksGet({ throwOnError: true });
    return (data ?? []) as TrackRead[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const templates = useQuery({
  queryKey: computed(() => ["track-templates", ws.currentId]),
  queryFn: async () => {
    const { data } = await listTemplatesApiV1TracksTemplatesGet({ throwOnError: true });
    return (data ?? []) as TrackTemplateRead[];
  },
  enabled: computed(() => Boolean(ws.currentId) && showNew.value),
});

async function refresh() {
  await qc.invalidateQueries({ queryKey: ["tracks", ws.currentId] });
}

async function createFromTemplate(slug: string) {
  creating.value = true;
  try {
    const pid = await ensureProfile();
    const { data } = await createTrackApiV1TracksPost({
      body: { profile_id: pid, template_slug: slug },
      throwOnError: true,
    });
    showNew.value = false;
    await refresh();
    if (data?.id) await navigateTo(`/tracks/${data.id}`);
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    creating.value = false;
  }
}

watch(nlDraft, () => {
  if (plan.value) plan.value = null;
});

async function checkSettings() {
  if (!nlDraft.value.trim()) return;
  planning.value = true;
  try {
    const { data } = await planSearchApiV1TracksPlanPost({
      body: { text: nlDraft.value.trim() },
      throwOnError: true,
    });
    if (!data) return;
    plan.value = data.criteria as CriteriaV1;
    planName.value = data.name || "";
    if (!nameDraft.value.trim() && data.name) nameDraft.value = data.name;
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    planning.value = false;
  }
}

function removePlanSkill(skill: string) {
  if (!plan.value) return;
  plan.value = {
    ...plan.value,
    skills: {
      must: (plan.value.skills?.must ?? []).filter((s) => s !== skill),
      nice: (plan.value.skills?.nice ?? []).filter((s) => s !== skill),
      exclude: plan.value.skills?.exclude ?? [],
    },
  };
}

function togglePlanAgencies() {
  if (!plan.value) return;
  const companies = plan.value.companies;
  plan.value = {
    ...plan.value,
    companies: {
      include: companies?.include ?? [],
      exclude: companies?.exclude ?? [],
      sizes: companies?.sizes ?? [],
      industries: companies?.industries ?? [],
      stages: companies?.stages ?? [],
      exclude_agencies: !companies?.exclude_agencies,
    },
  };
}

async function createFromText() {
  if (!nameDraft.value.trim() && !nlDraft.value.trim()) return;
  creating.value = true;
  try {
    const pid = profileId.value ?? (await ensureProfile());
    const body = plan.value
      ? {
          profile_id: pid,
          name: nameDraft.value.trim() || planName.value || undefined,
          nl_text: nlDraft.value.trim(),
          criteria: plan.value,
        }
      : {
          profile_id: pid,
          name: nameDraft.value.trim() || planName.value || undefined,
          nl_text: nlDraft.value.trim(),
          suggest: true,
        };
    const { data } = await createTrackApiV1TracksPost({ body, throwOnError: true });
    showNew.value = false;
    nlDraft.value = "";
    nameDraft.value = "";
    plan.value = null;
    await refresh();
    if (data?.id) await navigateTo(`/tracks/${data.id}`);
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    creating.value = false;
  }
}

async function duplicate(id: string) {
  try {
    await duplicateApiV1TracksTrackIdDuplicatePost({ path: { track_id: id }, throwOnError: true });
    await refresh();
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function archive(id: string) {
  try {
    await archiveApiV1TracksTrackIdArchivePost({ path: { track_id: id }, throwOnError: true });
    await refresh();
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

const trackRows = computed(() => tracks.data.value ?? []);
const templateRows = computed(() => templates.data.value ?? []);
const tracksLoading = computed(
  () => !ws.loaded || tracks.isPending.value || (tracks.isFetching.value && !tracks.data.value),
);
const templatesLoading = computed(() => templates.isPending.value);

function hue(n: number): 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 {
  const v = Math.min(8, Math.max(1, n || 1));
  return v as 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-8 md:px-6">
    <PageHeader :title="t('tracks.title')" :lede="t('tracks.lede')">
      <template #actions>
        <FnButton :tone="trackRows.length ? 'primary' : 'quiet'" @click="showNew = !showNew">{{
          t("tracks.new")
        }}</FnButton>
      </template>
    </PageHeader>

    <section
      v-if="showNew"
      class="flex flex-col gap-5 rounded-2xl border border-rule bg-paper-1 p-6 shadow-[var(--shadow-card)]"
      :aria-label="t('tracks.new')"
    >
      <label class="flex flex-col gap-2 text-sm">
        <span class="font-semibold text-ink-900">{{ t("tracks.describe") }}</span>
        <FnTextarea
          v-model="nlDraft"
          :rows="4"
          maxlength="8000"
          :placeholder="t('tracks.describePlaceholder')"
        />
      </label>
      <label class="flex flex-col gap-2 text-sm">
        <span class="font-semibold text-ink-900">{{ t("tracks.name") }}</span>
        <FnInput v-model="nameDraft" maxlength="200" :placeholder="t('tracks.namePlaceholder')" />
        <span class="text-xs text-ink-600">{{ t("tracks.nameHint") }}</span>
      </label>
      <div
        v-if="plan"
        class="flex flex-col gap-3 rounded-lg border border-dashed border-pencil bg-paper-0 p-4"
      >
        <p class="text-sm font-semibold text-ink-900">{{ t("tracks.settingsTitle") }}</p>
        <div class="flex flex-wrap gap-2">
          <FnChip
            v-for="title in plan.titles?.filter((x) => !x.exclude) ?? []"
            :key="title.title"
            tone="accent"
            >{{ title.title }}</FnChip
          >
          <FnChip
            v-for="s in plan.skills?.must ?? []"
            :key="`m-${s}`"
            tone="neutral"
            removable
            :remove-label="t('tracks.removeChip')"
            @remove="removePlanSkill(s)"
            >{{ s }}</FnChip
          >
          <FnChip
            v-for="s in plan.skills?.nice ?? []"
            :key="`n-${s}`"
            tone="pencil"
            removable
            :remove-label="t('tracks.removeChip')"
            @remove="removePlanSkill(s)"
            >{{ s }}</FnChip
          >
          <button
            type="button"
            class="inline-flex min-h-11 items-center gap-1.5 rounded-full border px-4 text-xs font-semibold transition-colors"
            :class="
              plan.companies?.exclude_agencies
                ? 'border-rule bg-paper-2 text-ink-900'
                : 'border-dashed border-edge bg-paper-1 text-ink-600 hover:bg-paper-2'
            "
            :aria-pressed="Boolean(plan.companies?.exclude_agencies)"
            @click="togglePlanAgencies"
          >
            <span aria-hidden="true">{{ plan.companies?.exclude_agencies ? "✓" : "+" }}</span>
            {{ t("tracks.noAgencies") }}
          </button>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <FnButton tone="quiet" :disabled="planning || !nlDraft.trim()" @click="checkSettings">{{
          planning ? t("tracks.checkingSettings") : t("tracks.checkSettings")
        }}</FnButton>
        <FnButton tone="primary" :disabled="creating" @click="createFromText">{{
          t("common.create")
        }}</FnButton>
        <FnButton tone="ghost" @click="showNew = false">{{ t("common.cancel") }}</FnButton>
        <FnButton
          tone="ghost"
          :aria-expanded="showTemplates"
          @click="showTemplates = !showTemplates"
          >{{ t("tracks.browseTemplates") }}</FnButton
        >
      </div>
      <div v-if="showTemplates" class="flex flex-col gap-2">
        <div v-if="templatesLoading" class="flex flex-col gap-2">
          <FnSkeleton class="h-10 w-full" />
          <FnSkeleton class="h-10 w-full" />
        </div>
        <ul v-else class="grid gap-2 sm:grid-cols-2">
          <li v-for="tmpl in templateRows" :key="tmpl.slug">
            <button
              type="button"
              class="flex min-h-11 w-full items-center gap-2 rounded-lg border border-rule bg-paper-0 px-3 text-left text-sm transition-colors hover:border-brand-200 hover:bg-brand-50"
              :disabled="creating"
              @click="createFromTemplate(tmpl.slug)"
            >
              <FnFolderTab :hue="hue(tmpl.color_hue)" class="pointer-events-none">{{
                tmpl.name
              }}</FnFolderTab>
            </button>
          </li>
        </ul>
      </div>
    </section>

    <div v-if="tracksLoading" class="flex flex-col gap-3">
      <FnSkeleton class="h-14 w-full" />
      <FnSkeleton class="h-14 w-full" />
    </div>
    <div
      v-else-if="!trackRows.length"
      class="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-rule bg-paper-1 p-10 text-center"
    >
      <p class="text-ink-600">{{ t("tracks.empty") }}</p>
      <FnButton tone="primary" @click="showNew = true">{{ t("tracks.start") }}</FnButton>
    </div>
    <ul v-else class="flex flex-col gap-3">
      <li
        v-for="tr in trackRows"
        :key="tr.id"
        class="flex flex-wrap items-center gap-4 rounded-xl border border-rule bg-paper-1 p-5 shadow-[var(--shadow-card)] transition-colors hover:border-brand-200"
      >
        <NuxtLink :to="`/tracks/${tr.id}`" class="min-w-0 flex-1">
          <FnFolderTab :hue="hue(tr.color_hue)" active>{{ tr.name }}</FnFolderTab>
          <p
            v-if="tr.summary && tr.summary !== tr.name && tr.summary !== tr.name + '.'"
            class="mt-1 text-sm text-ink-600"
          >
            {{ tr.summary }}
          </p>
        </NuxtLink>
        <div class="flex flex-wrap items-center gap-2">
          <FnButton as-child size="sm" tone="quiet">
            <NuxtLink :to="`/jobs?track=${tr.id}`">{{ t("tracks.viewMatches") }}</NuxtLink>
          </FnButton>
          <FnButton tone="ghost" @click="duplicate(tr.id)">{{ t("tracks.duplicate") }}</FnButton>
          <FnButton tone="ghost" @click="archive(tr.id)">{{ t("tracks.archive") }}</FnButton>
        </div>
      </li>
    </ul>
  </div>
</template>
