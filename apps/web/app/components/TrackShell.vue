<script setup lang="ts">
import { getTrackApiV1TracksTrackIdGet, type TrackDetail } from "@kame/api-client";
import { FnSkeleton } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

/** Header and section nav shared by the search tabs. */
const props = defineProps<{ trackId: string }>();

const route = useRoute();
const { t } = useI18n();
const apiError = useApiError();
const ws = useWorkspaceStore();

const detail = useQuery({
  queryKey: computed(() => ["track", ws.currentId, props.trackId]),
  queryFn: async () => {
    const { data } = await getTrackApiV1TracksTrackIdGet({
      path: { track_id: props.trackId },
      throwOnError: true,
    });
    return data as TrackDetail;
  },
  enabled: computed(() => Boolean(ws.currentId && props.trackId)),
});

const track = computed(() => detail.data.value ?? null);
const loading = computed(
  () => !ws.loaded || detail.isPending.value || (detail.isFetching.value && !track.value),
);
const hue = computed(() => Math.min(8, Math.max(1, track.value?.color_hue || 1)));
const paused = computed(() => track.value?.status === "paused");

const tabs = computed(() => [
  { to: `/tracks/${props.trackId}`, label: t("tracks.tabMatches") },
  { to: `/tracks/${props.trackId}/look-for`, label: t("tracks.tabCriteria") },
  { to: `/tracks/${props.trackId}/settings`, label: t("tracks.tabAutomation") },
  { to: `/tracks/${props.trackId}/runs`, label: t("tracks.tabHistory") },
  { to: `/tracks/${props.trackId}/improve`, label: t("tracks.tabImprove") },
]);
const path = computed(() => route.path.replace(/\/+$/, "") || "/");
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-6">
    <div v-if="loading" class="flex flex-col gap-3">
      <FnSkeleton class="h-9 w-64" />
      <FnSkeleton class="h-11 w-full" />
    </div>
    <p v-else-if="detail.error.value" class="text-sm text-ink-600">
      {{ apiError(detail.error.value) }}
    </p>
    <template v-else-if="track">
      <header class="flex flex-col gap-4">
        <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-3">
          <div class="flex min-w-0 items-center gap-3 sm:flex-1">
            <span
              class="size-3 shrink-0 rounded-full"
              :style="{ background: `var(--track-${hue})` }"
              aria-hidden="true"
            />
            <h1
              class="min-w-0 text-2xl font-bold break-words tracking-[-0.03em] text-ink-900 md:text-3xl"
            >
              {{ track.name }}
            </h1>
          </div>
          <div class="flex items-center gap-2">
            <span
              class="inline-flex items-center gap-1.5 rounded-full border border-rule bg-paper-1 px-3 py-1 text-xs font-semibold text-ink-600"
            >
              <span
                class="size-1.5 rounded-full"
                :class="paused ? 'bg-saffron-600' : 'bg-fern-600'"
                aria-hidden="true"
              />
              {{ paused ? t("tracks.paused") : t("tracks.active") }}
            </span>
          </div>
        </div>
        <nav :aria-label="t('tracks.sections')">
          <ul class="flex gap-1 overflow-x-auto rounded-lg bg-paper-2 p-1">
            <li v-for="tab in tabs" :key="tab.to">
              <NuxtLink
                :to="tab.to"
                class="flex min-h-11 shrink-0 items-center rounded-md px-3 text-sm font-semibold whitespace-nowrap sm:px-4"
                :class="
                  path === tab.to
                    ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
                    : 'text-ink-600 hover:text-ink-900'
                "
                :aria-current="path === tab.to ? 'page' : undefined"
                >{{ tab.label }}</NuxtLink
              >
            </li>
          </ul>
        </nav>
      </header>
      <slot :track="track" />
    </template>
  </div>
</template>
