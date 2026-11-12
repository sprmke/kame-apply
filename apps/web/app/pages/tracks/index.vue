<script setup lang="ts">
import {
  archiveApiV1TracksTrackIdArchivePost,
  createScheduleApiV1TracksTrackIdSchedulesPost,
  createTrackApiV1TracksPost,
  duplicateApiV1TracksTrackIdDuplicatePost,
  listTemplatesApiV1TracksTemplatesGet,
  listTracksApiV1TracksGet,
  planSearchApiV1TracksPlanPost,
  type CriteriaV1,
  type TrackRead,
  type TrackTemplateRead,
} from "@kame/api-client";
import {
  FnButton,
  FnChip,
  FnDialog,
  FnEmptyState,
  FnField,
  FnFolderTab,
  FnInput,
  FnSkeleton,
  FnTextarea,
  useToast,
} from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const { ensureProfile, profileId } = useActiveProfile();

type Mode = "describe" | "template" | "copy";
const open = ref(false);
const mode = ref<Mode>("describe");
const creating = ref(false);
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
  enabled: computed(() => Boolean(ws.currentId) && open.value),
});

async function refresh() {
  await qc.invalidateQueries({ queryKey: ["tracks", ws.currentId] });
}

/** A new search starts with recommended defaults so it works without another screen. */
async function addDefaultSchedule(trackId: string) {
  try {
    await createScheduleApiV1TracksTrackIdSchedulesPost({
      path: { track_id: trackId },
      body: {
        preset: "every_4_hours",
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
        quiet_hours: { start: "22:00", end: "07:00" },
        daily_cap: 12,
      },
      throwOnError: true,
    });
  } catch {
    // The search works without a schedule; the automation tab offers another try.
  }
}

function reset() {
  nlDraft.value = "";
  nameDraft.value = "";
  plan.value = null;
  planName.value = "";
  mode.value = "describe";
}

function openNew() {
  reset();
  open.value = true;
}

async function createFromTemplate(slug: string) {
  creating.value = true;
  try {
    const pid = await ensureProfile();
    const { data } = await createTrackApiV1TracksPost({
      body: { profile_id: pid, template_slug: slug },
      throwOnError: true,
    });
    open.value = false;
    await refresh();
    if (data?.id) {
      await addDefaultSchedule(String(data.id));
      await navigateTo(`/tracks/${data.id}`);
    }
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
    open.value = false;
    reset();
    await refresh();
    if (data?.id) {
      await addDefaultSchedule(String(data.id));
      await navigateTo(`/tracks/${data.id}`);
    }
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    creating.value = false;
  }
}

async function duplicate(id: string) {
  try {
    const { data } = await duplicateApiV1TracksTrackIdDuplicatePost({
      path: { track_id: id },
      throwOnError: true,
    });
    await refresh();
    open.value = false;
    if (data?.id) await navigateTo(`/tracks/${data.id}`);
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

const autonomyLabel = computed<Record<string, string>>(() => ({
  discover: t("tracks.autonomyDiscover"),
  prepare: t("tracks.autonomyPrepare"),
  assist: t("tracks.autonomyAssist"),
  auto_submit: t("tracks.autonomyAuto"),
}));

function hue(n: number): 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 {
  const v = Math.min(8, Math.max(1, n || 1));
  return v as 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-6">
    <PageHeader :title="t('tracks.title')" :lede="t('tracks.lede')">
      <template #actions>
        <FnButton tone="primary" @click="openNew">{{ t("tracks.new") }}</FnButton>
      </template>
    </PageHeader>

    <div v-if="tracksLoading" class="flex flex-col gap-3">
      <FnSkeleton class="h-24 w-full" />
      <FnSkeleton class="h-24 w-full" />
    </div>

    <FnEmptyState
      v-else-if="!trackRows.length"
      :title="t('tracks.emptyTitle')"
      :body="t('tracks.emptyBody')"
    >
      <FnButton tone="primary" @click="openNew">{{ t("tracks.start") }}</FnButton>
    </FnEmptyState>

    <ul v-else class="flex flex-col gap-3">
      <li
        v-for="tr in trackRows"
        :key="tr.id"
        class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)] transition-colors hover:border-brand-200 sm:p-5"
      >
        <div class="flex items-start justify-between gap-3">
          <NuxtLink :to="`/tracks/${tr.id}`" class="min-w-0 flex-1">
            <FnFolderTab :hue="hue(tr.color_hue)" active>{{ tr.name }}</FnFolderTab>
            <p class="mt-2 line-clamp-2 text-sm leading-6 text-ink-600">
              {{ tr.summary && tr.summary !== tr.name ? tr.summary : t("tracks.summaryFallback") }}
            </p>
          </NuxtLink>
          <span
            class="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-rule bg-paper-1 px-2.5 py-1 text-xs font-semibold text-ink-600"
          >
            <span
              class="size-1.5 rounded-full"
              :class="tr.status === 'paused' ? 'bg-saffron-600' : 'bg-fern-600'"
              aria-hidden="true"
            />
            {{ tr.status === "paused" ? t("tracks.paused") : t("tracks.active") }}
          </span>
        </div>

        <p class="text-xs text-ink-600">
          {{ t("tracks.howMuchLabel") }}:
          <span class="font-semibold text-ink-900">{{
            autonomyLabel[tr.autonomy] ?? tr.autonomy
          }}</span>
        </p>

        <div class="flex flex-wrap items-center gap-2 border-t border-rule pt-3">
          <FnButton as-child size="sm" tone="quiet">
            <NuxtLink :to="`/jobs?track=${tr.id}`">{{ t("tracks.viewMatches") }}</NuxtLink>
          </FnButton>
          <FnButton as-child size="sm" tone="ghost">
            <NuxtLink :to="`/tracks/${tr.id}/settings`">{{ t("tracks.tabAutomation") }}</NuxtLink>
          </FnButton>
          <div class="flex items-center gap-1 sm:ml-auto">
            <FnButton size="sm" tone="ghost" @click="duplicate(tr.id)">{{
              t("tracks.duplicate")
            }}</FnButton>
            <FnButton size="sm" tone="ghost" @click="archive(tr.id)">{{
              t("tracks.archive")
            }}</FnButton>
          </div>
        </div>
      </li>
    </ul>

    <FnDialog
      v-model:open="open"
      variant="sheet"
      :title="t('searches.newTitle')"
      :description="t('searches.newIntro')"
      :close-label="t('common.close')"
    >
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-3 gap-1 rounded-lg bg-paper-2 p-1" role="tablist">
          <button
            v-for="item in [
              ['describe', t('searches.tabDescribe')],
              ['template', t('searches.tabTemplate')],
              ['copy', t('searches.tabCopy')],
            ] as const"
            :key="item[0]"
            type="button"
            role="tab"
            class="min-h-11 rounded-md px-2 text-sm font-semibold"
            :class="
              mode === item[0]
                ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
                : 'text-ink-600'
            "
            :aria-selected="mode === item[0]"
            @click="mode = item[0]"
          >
            {{ item[1] }}
          </button>
        </div>

        <template v-if="mode === 'describe'">
          <FnField v-slot="{ id }" :label="t('searches.describeLabel')">
            <FnTextarea
              :id="id"
              v-model="nlDraft"
              :rows="3"
              maxlength="8000"
              :placeholder="t('searches.describePlaceholder')"
              autofocus
            />
          </FnField>

          <div
            v-if="plan"
            class="flex flex-col gap-3 rounded-lg border border-dashed border-pencil bg-paper-0 p-3"
          >
            <p class="text-sm font-semibold text-ink-900">{{ t("searches.preview") }}</p>
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

          <FnField v-slot="{ id }" :label="t('searches.nameLabel')" :hint="t('searches.nameHint')">
            <FnInput
              :id="id"
              v-model="nameDraft"
              maxlength="200"
              :placeholder="t('searches.namePlaceholder')"
            />
          </FnField>

          <div class="flex flex-wrap gap-2">
            <FnButton tone="primary" :disabled="creating" @click="createFromText">
              {{ creating ? t("searches.creating") : t("searches.create") }}
            </FnButton>
            <FnButton tone="quiet" :disabled="planning || !nlDraft.trim()" @click="checkSettings">
              {{ planning ? t("tracks.checkingSettings") : t("tracks.checkSettings") }}
            </FnButton>
          </div>
        </template>

        <template v-else-if="mode === 'template'">
          <div v-if="templatesLoading" class="flex flex-col gap-2">
            <FnSkeleton class="h-14 w-full" />
            <FnSkeleton class="h-14 w-full" />
          </div>
          <ul v-else class="grid gap-2 sm:grid-cols-2">
            <li v-for="tmpl in templateRows" :key="tmpl.slug">
              <button
                type="button"
                class="flex min-h-14 w-full items-center gap-2 rounded-lg border border-rule bg-paper-0 px-3 text-left text-sm transition-colors hover:border-brand-200 hover:bg-brand-50"
                :disabled="creating"
                @click="createFromTemplate(tmpl.slug)"
              >
                <FnFolderTab :hue="hue(tmpl.color_hue)" class="pointer-events-none">{{
                  tmpl.name
                }}</FnFolderTab>
              </button>
            </li>
          </ul>
        </template>

        <template v-else>
          <FnEmptyState
            v-if="!trackRows.length"
            :title="t('searches.copyNone')"
            :body="t('searches.newIntro')"
          />
          <ul v-else class="flex flex-col divide-y divide-rule">
            <li v-for="tr in trackRows" :key="tr.id" class="flex min-h-14 items-center gap-3 py-2">
              <span class="min-w-0 flex-1 truncate text-sm text-ink-900">{{ tr.name }}</span>
              <FnButton size="sm" tone="quiet" :disabled="creating" @click="duplicate(tr.id)">
                {{ t("tracks.duplicate") }}
              </FnButton>
            </li>
          </ul>
        </template>
      </div>
    </FnDialog>
  </div>
</template>
