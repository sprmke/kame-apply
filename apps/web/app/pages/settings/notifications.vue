<script setup lang="ts">
import {
  getPrefsApiV1NotificationPrefsGet,
  putPrefsApiV1NotificationPrefsPut,
  unsubscribeEmailApiV1NotificationPrefsUnsubscribeEmailPost,
  type PrefCell,
} from "@kame/api-client";
import { FnButton, FnSkeleton, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const saving = ref(false);

const prefs = useQuery({
  queryKey: computed(() => ["notification-prefs", ws.currentId]),
  queryFn: async () => {
    const { data } = await getPrefsApiV1NotificationPrefsGet({ throwOnError: true });
    return (data?.cells ?? []) as PrefCell[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const cells = ref<PrefCell[]>([]);
watch(
  () => prefs.data.value,
  (v) => {
    if (v) cells.value = v.map((c) => ({ ...c }));
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

function toggle(channel: "in_app" | "email", event: string) {
  const c = cell(channel, event);
  if (c) c.enabled = !c.enabled;
}

async function save() {
  saving.value = true;
  try {
    await putPrefsApiV1NotificationPrefsPut({
      body: { cells: cells.value },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["notification-prefs", ws.currentId] });
    toast.push({ title: t("common.saved"), tone: "neutral" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    saving.value = false;
  }
}

async function unsub() {
  try {
    await unsubscribeEmailApiV1NotificationPrefsUnsubscribeEmailPost({ throwOnError: true });
    await qc.invalidateQueries({ queryKey: ["notification-prefs", ws.currentId] });
    toast.push({ title: t("notifications.unsubscribed"), tone: "neutral" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}
</script>

<template>
  <section class="flex max-w-xl flex-col gap-4">
    <PageHeader :title="t('settings.notifications')" :lede="t('settings.notificationsLede')" />
    <div v-if="prefs.isPending.value"><FnSkeleton class="h-40 w-full" /></div>
    <template v-else>
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="border-b border-rule text-ink-600">
            <th class="py-2 font-medium">{{ t("notifications.event") }}</th>
            <th class="py-2 font-medium">{{ t("notifications.inApp") }}</th>
            <th class="py-2 font-medium">{{ t("notifications.email") }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ev in events" :key="ev" class="border-b border-rule">
            <td class="py-2 text-ink-900">{{ t(`notifications.events.${ev}`) }}</td>
            <td class="py-2">
              <input
                type="checkbox"
                :checked="cell('in_app', ev)?.enabled"
                @change="toggle('in_app', ev)"
              />
            </td>
            <td class="py-2">
              <input
                type="checkbox"
                :checked="cell('email', ev)?.enabled"
                @change="toggle('email', ev)"
              />
            </td>
          </tr>
        </tbody>
      </table>
      <div class="flex flex-wrap gap-2">
        <FnButton tone="primary" :disabled="saving" @click="save">{{ t("common.save") }}</FnButton>
        <FnButton tone="quiet" @click="unsub">{{ t("notifications.unsubscribeEmail") }}</FnButton>
      </div>
    </template>
  </section>
</template>
