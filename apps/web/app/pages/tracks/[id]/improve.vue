<script setup lang="ts">
import {
  listGapPlanApiV1TracksTrackIdGapPlanGet,
  patchGapItemApiV1GapPlanItemIdPatch,
  refreshGapPlanApiV1TracksTrackIdGapPlanRefreshPost,
  type GapPlanItemRead,
} from "@kame/api-client";
import { FnButton, FnSectionCard, FnSkeleton, useToast } from "@kame/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const route = useRoute();
const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();

const trackId = computed(() => String(route.params.id));

const gaps = useQuery({
  queryKey: computed(() => ["gap-plan", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await listGapPlanApiV1TracksTrackIdGapPlanGet({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    return (data ?? []) as GapPlanItemRead[];
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});

const suggest = useMutation({
  mutationFn: async () => {
    const { data } = await refreshGapPlanApiV1TracksTrackIdGapPlanRefreshPost({
      path: { track_id: trackId.value },
      throwOnError: true,
    });
    return (data ?? []) as GapPlanItemRead[];
  },
  onSuccess: (rows) => {
    qc.setQueryData(["gap-plan", ws.currentId, trackId.value], rows);
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

// Fill the gap plan the first time the page opens, so it is never an empty screen.
watch(
  () => [gaps.isSuccess.value, gaps.data.value?.length] as const,
  ([ok, n]) => {
    if (ok && !n && !suggest.isPending.value) suggest.mutate();
  },
  { immediate: true },
);

async function setStatus(item: GapPlanItemRead, status: string) {
  try {
    await patchGapItemApiV1GapPlanItemIdPatch({
      path: { item_id: item.id },
      body: { status },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["gap-plan", ws.currentId, trackId.value] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

function statusLabel(status: string): string {
  if (status === "done") return t("gaps.done");
  if (status === "in_progress") return t("gaps.inProgress");
  if (status === "skipped") return t("gaps.skip");
  return t("gaps.todo");
}
</script>

<template>
  <TrackShell :track-id="trackId">
    <div class="flex flex-col gap-5">
      <FnSectionCard :title="t('gaps.title')" :intro="t('tracks.improveIntro')">
        <div v-if="gaps.isPending.value || suggest.isPending.value" class="flex flex-col gap-2">
          <FnSkeleton class="h-14 w-full" />
          <FnSkeleton class="h-14 w-full" />
        </div>
        <p v-else-if="!(gaps.data.value ?? []).length" class="text-sm text-ink-600">
          {{ t("gaps.empty") }}
        </p>
        <ul v-else class="divide-y divide-rule border-y border-rule">
          <li
            v-for="item in gaps.data.value"
            :key="item.id"
            class="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div class="min-w-0">
              <p class="font-medium text-ink-900">{{ item.skill }}</p>
              <p class="text-sm text-ink-600">
                <a
                  v-if="item.resource_url"
                  :href="item.resource_url"
                  target="_blank"
                  rel="noopener"
                  class="underline"
                  >{{ t("gaps.resource") }}</a
                >
                · {{ statusLabel(item.status) }}
              </p>
            </div>
            <div class="flex flex-wrap gap-2">
              <FnButton size="sm" tone="quiet" @click="setStatus(item, 'in_progress')">{{
                t("gaps.inProgress")
              }}</FnButton>
              <FnButton size="sm" tone="ghost" @click="setStatus(item, 'done')">{{
                t("gaps.done")
              }}</FnButton>
              <FnButton size="sm" tone="ghost" @click="setStatus(item, 'skipped')">{{
                t("gaps.skip")
              }}</FnButton>
            </div>
          </li>
        </ul>
      </FnSectionCard>

      <FnSectionCard :title="t('beFound.title')" :intro="t('tracks.beFoundIntro')">
        <FnButton as-child tone="quiet">
          <NuxtLink :to="`/tracks/${trackId}/be-found`">{{ t("beFound.title") }}</NuxtLink>
        </FnButton>
      </FnSectionCard>
    </div>
  </TrackShell>
</template>
