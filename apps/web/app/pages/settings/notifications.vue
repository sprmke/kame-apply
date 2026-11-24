<script setup lang="ts">
import {
  getPrefsApiV1NotificationPrefsGet,
  putPrefsApiV1NotificationPrefsPut,
  resetPrefsApiV1NotificationPrefsResetPost,
  unsubscribeEmailApiV1NotificationPrefsUnsubscribeEmailPost,
  type PrefCell,
} from "@kame/api-client";
import {
  FnButton,
  FnCheckbox,
  FnDialog,
  FnEmptyState,
  FnSectionCard,
  FnSkeleton,
  FnSkeletonGroup,
  FnSummaryLine,
  useToast,
} from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const saving = ref(false);
const unsubOpen = ref(false);
const resetOpen = ref(false);

const prefs = useQuery({
  queryKey: computed(() => ["notification-prefs", ws.currentId]),
  queryFn: async () => {
    const { data } = await getPrefsApiV1NotificationPrefsGet({ throwOnError: true });
    return (data?.cells ?? []) as PrefCell[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const cells = ref<PrefCell[]>([]);
const saved = ref("[]");
watch(
  () => prefs.data.value,
  (v) => {
    if (!v) return;
    cells.value = v.map((c) => ({ ...c }));
    saved.value = JSON.stringify(cells.value);
  },
  { immediate: true },
);

const events = [
  "strong_match",
  "needs_review",
  "risk_flag",
  "run_failed",
  "budget_reached",
  "digest",
];

function cell(channel: "in_app" | "email", event: string) {
  return cells.value.find((c) => c.channel === channel && c.event === event);
}
function toggle(channel: "in_app" | "email", event: string, on: boolean) {
  const c = cell(channel, event);
  if (c) c.enabled = on;
}
function labelFor(channel: "in_app" | "email", event: string) {
  return `${t(`notifications.events.${event}`)}, ${t(`notifications.${channel === "in_app" ? "inApp" : "email"}`)}`;
}

const dirty = computed(() => JSON.stringify(cells.value) !== saved.value);
const emailOn = computed(
  () => cells.value.filter((c) => c.channel === "email" && c.enabled).length,
);

async function save() {
  saving.value = true;
  try {
    await putPrefsApiV1NotificationPrefsPut({
      body: { cells: cells.value },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["notification-prefs", ws.currentId] });
    toast.push({ title: t("common.saved"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    saving.value = false;
  }
}

async function useRecommended() {
  saving.value = true;
  try {
    await resetPrefsApiV1NotificationPrefsResetPost({ throwOnError: true });
    await qc.invalidateQueries({ queryKey: ["notification-prefs", ws.currentId] });
    toast.push({ title: t("notifications.resetDone"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    saving.value = false;
  }
}

async function unsub() {
  try {
    await unsubscribeEmailApiV1NotificationPrefsUnsubscribeEmailPost({ throwOnError: true });
    unsubOpen.value = false;
    await qc.invalidateQueries({ queryKey: ["notification-prefs", ws.currentId] });
    toast.push({ title: t("notifications.unsubscribed"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}
</script>

<template>
  <section class="flex max-w-2xl flex-col gap-6">
    <PageHeader :title="t('settings.notifications')" :lede="t('settings.notificationsLede')" />

    <FnSkeletonGroup v-if="prefs.isPending.value" :label="t('common.loading')">
      <SkeletonSectionCard>
        <div class="flex flex-col gap-2">
          <div class="flex items-center gap-4 border-b border-rule pb-2">
            <FnSkeleton class="h-3 flex-1" />
            <FnSkeleton class="h-3 w-10" />
            <FnSkeleton class="h-3 w-10" />
          </div>
          <div v-for="n in 6" :key="n" class="flex items-center gap-4 border-b border-rule py-3">
            <FnSkeleton class="h-4 flex-1" />
            <FnSkeleton class="size-5 shrink-0 rounded" />
            <FnSkeleton class="size-5 shrink-0 rounded" />
          </div>
          <FnSkeleton class="mt-2 h-9 w-full rounded-lg" />
          <div class="flex flex-wrap items-center gap-2 border-t border-rule pt-4">
            <FnSkeleton class="h-12 w-24 rounded-md" />
            <FnSkeleton class="h-12 w-40 rounded-md" />
            <FnSkeleton class="ml-auto h-11 w-28 rounded-md" />
          </div>
        </div>
      </SkeletonSectionCard>
    </FnSkeletonGroup>

    <FnEmptyState
      v-else-if="prefs.isError.value"
      :title="t('notifications.loadError')"
      :body="apiError(prefs.error.value)"
      tone="danger"
    >
      <FnButton size="sm" @click="prefs.refetch()">{{ t("common.retry") }}</FnButton>
    </FnEmptyState>

    <FnSectionCard
      v-else
      :title="t('notifications.matrixTitle')"
      :intro="t('notifications.matrixIntro')"
    >
      <table class="w-full border-collapse text-left text-sm">
        <caption class="sr-only">
          {{
            t("settings.notifications")
          }}
        </caption>
        <thead>
          <tr
            class="border-b border-rule text-xs font-semibold tracking-wide text-ink-600 uppercase"
          >
            <th scope="col" class="py-2 pr-4 font-semibold">{{ t("notifications.event") }}</th>
            <th scope="col" class="w-16 py-2 text-center font-semibold">
              {{ t("notifications.inApp") }}
            </th>
            <th scope="col" class="w-16 py-2 text-center font-semibold">
              {{ t("notifications.email") }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ev in events" :key="ev" class="border-b border-rule last:border-0">
            <th scope="row" class="py-1 pr-4 font-medium text-ink-900">
              {{ t(`notifications.events.${ev}`) }}
            </th>
            <td class="py-1 text-center">
              <span class="inline-flex">
                <FnCheckbox
                  hide-label
                  :label="labelFor('in_app', ev)"
                  :model-value="cell('in_app', ev)?.enabled ?? false"
                  @update:model-value="(v) => toggle('in_app', ev, v)"
                />
              </span>
            </td>
            <td class="py-1 text-center">
              <span class="inline-flex">
                <FnCheckbox
                  hide-label
                  :label="labelFor('email', ev)"
                  :model-value="cell('email', ev)?.enabled ?? false"
                  @update:model-value="(v) => toggle('email', ev, v)"
                />
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <FnSummaryLine
        :text="t('notifications.summary', { on: emailOn, total: events.length })"
        class="mt-2"
      />

      <template #footer>
        <div class="flex flex-wrap items-center gap-2 border-t border-rule pt-4">
          <FnButton tone="primary" :disabled="!dirty || saving" :loading="saving" @click="save">
            {{ t("common.save") }}
          </FnButton>
          <FnButton tone="quiet" :disabled="saving" @click="resetOpen = true">
            {{ t("notifications.useRecommended") }}
          </FnButton>
          <FnButton tone="ghost" class="ml-auto" @click="unsubOpen = true">
            {{ t("notifications.unsubscribe") }}
          </FnButton>
        </div>
      </template>
    </FnSectionCard>

    <FnDialog
      v-model:open="resetOpen"
      :title="t('notifications.resetTitle')"
      :description="t('notifications.resetBody')"
      :close-label="t('common.close')"
    >
      <div class="flex justify-end gap-2">
        <FnButton @click="resetOpen = false">{{ t("common.cancel") }}</FnButton>
        <FnButton
          :loading="saving"
          @click="
            useRecommended();
            resetOpen = false;
          "
        >
          {{ t("notifications.useRecommended") }}
        </FnButton>
      </div>
    </FnDialog>

    <FnDialog
      v-model:open="unsubOpen"
      :title="t('notifications.unsubscribeTitle')"
      :description="t('notifications.unsubscribeBody')"
      :close-label="t('common.close')"
    >
      <div class="flex justify-end gap-2">
        <FnButton @click="unsubOpen = false">{{ t("common.cancel") }}</FnButton>
        <FnButton tone="danger" @click="unsub">{{ t("notifications.unsubscribe") }}</FnButton>
      </div>
    </FnDialog>
  </section>
</template>
