<script setup lang="ts">
import {
  listNotificationsApiV1NotificationsGet,
  markAllReadApiV1NotificationsReadAllPost,
  markReadApiV1NotificationsNotificationIdReadPost,
  needsYouApiV1NeedsYouGet,
  type NeedsYouItem,
  type NotificationRead,
} from "@kame/api-client";
import { FnButton, FnEmptyState, FnSkeleton, FnSkeletonGroup, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const fmt = useFormat();

const notes = useQuery({
  queryKey: computed(() => ["notifications", ws.currentId]),
  queryFn: async () => {
    const { data } = await listNotificationsApiV1NotificationsGet({ throwOnError: true });
    return (data ?? []) as NotificationRead[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
  refetchInterval: 15_000,
});

const needs = useQuery({
  queryKey: computed(() => ["needs-you", ws.currentId]),
  queryFn: async () => {
    const { data } = await needsYouApiV1NeedsYouGet({ throwOnError: true });
    return data;
  },
  enabled: computed(() => Boolean(ws.currentId)),
  refetchInterval: 15_000,
});

const rows = computed(() => notes.data.value ?? []);
const needItems = computed(() => {
  const seen = new Set<string>();
  return ((needs.data.value?.items ?? []) as NeedsYouItem[]).filter((item) => {
    const key = `${item.kind}:${item.href}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
});

async function markOne(id: string) {
  try {
    await markReadApiV1NotificationsNotificationIdReadPost({
      path: { notification_id: id },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["notifications", ws.currentId] });
    await qc.invalidateQueries({ queryKey: ["needs-you-count", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function markAll() {
  try {
    await markAllReadApiV1NotificationsReadAllPost({ throwOnError: true });
    await qc.invalidateQueries({ queryKey: ["notifications", ws.currentId] });
    await qc.invalidateQueries({ queryKey: ["needs-you-count", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-6">
    <PageHeader :title="t('notifications.title')">
      <template #actions>
        <FnButton tone="quiet" size="sm" @click="markAll">{{
          t("notifications.markAll")
        }}</FnButton>
      </template>
    </PageHeader>

    <FnSkeletonGroup
      v-if="needs.isPending.value"
      :label="t('common.loading')"
      class="flex flex-col gap-2"
    >
      <div class="flex items-center justify-between gap-2">
        <FnSkeleton class="h-4 w-24" />
        <FnSkeleton class="h-3.5 w-16" />
      </div>
      <ul class="divide-y divide-rule border-y border-rule">
        <li v-for="n in 2" :key="n" class="flex min-h-11 flex-col gap-2 py-3">
          <FnSkeleton class="h-4 w-3/5" />
          <FnSkeleton class="h-3.5 w-4/5" />
        </li>
      </ul>
    </FnSkeletonGroup>

    <section v-else-if="needItems.length" class="flex flex-col gap-2">
      <div class="flex items-center justify-between gap-2">
        <h2 class="text-sm font-semibold tracking-wide text-ink-600 uppercase">
          {{ t("shell.needsYou") }}
        </h2>
        <NuxtLink to="/needs-you" class="text-sm font-semibold text-brand-700 underline">{{
          t("today.viewAll")
        }}</NuxtLink>
      </div>
      <ul class="divide-y divide-rule border-y border-rule">
        <li v-for="(item, i) in needItems" :key="`${item.kind}-${i}`">
          <NuxtLink
            :to="item.href"
            class="flex min-h-11 flex-col gap-0.5 py-3 text-sm hover:bg-paper-1"
          >
            <span class="font-medium text-ink-900">{{ item.title }}</span>
            <span class="text-ink-600">{{ item.detail }}</span>
          </NuxtLink>
        </li>
      </ul>
    </section>

    <section class="flex flex-col gap-2">
      <h2 class="text-sm font-semibold tracking-wide text-ink-600 uppercase">
        {{ t("notifications.inbox") }}
      </h2>
      <FnSkeletonGroup v-if="notes.isPending.value" :label="t('common.loading')">
        <ul class="divide-y divide-rule border-y border-rule">
          <li v-for="n in 5" :key="n" class="flex min-h-11 items-start justify-between gap-3 py-3">
            <div class="flex min-w-0 flex-1 flex-col gap-2">
              <FnSkeleton class="h-4 w-3/5" />
              <FnSkeleton class="h-3.5 w-4/5" />
              <FnSkeleton class="h-3 w-24" />
            </div>
            <FnSkeleton class="h-11 w-24 shrink-0 rounded-md" />
          </li>
        </ul>
      </FnSkeletonGroup>
      <FnEmptyState v-else-if="!rows.length" :title="t('notifications.empty')" />
      <ul v-else class="divide-y divide-rule border-y border-rule">
        <li
          v-for="n in rows"
          :key="n.id"
          class="flex min-h-11 items-start justify-between gap-3 py-3 text-sm"
          :class="n.read_at ? 'opacity-60' : ''"
        >
          <div class="flex min-w-0 flex-col gap-0.5">
            <span class="font-medium text-ink-900">{{ n.title }}</span>
            <span v-if="n.body" class="text-ink-600">{{ n.body }}</span>
            <span class="text-xs text-ink-600">{{ fmt.dateTime(n.created_at) }}</span>
          </div>
          <FnButton v-if="!n.read_at" tone="quiet" size="sm" @click="markOne(String(n.id))">{{
            t("notifications.markRead")
          }}</FnButton>
        </li>
      </ul>
    </section>
  </div>
</template>
