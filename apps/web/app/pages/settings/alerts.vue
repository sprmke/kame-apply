<script setup lang="ts">
import { client } from "@kame/api-client";
import {
  FnButton,
  FnChip,
  FnDialog,
  FnEmptyState,
  FnSectionCard,
  FnSkeleton,
  FnSkeletonGroup,
  useToast,
} from "@kame/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

definePageMeta({ layout: "default" });

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const fmt = useFormat();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const newOpen = ref(false);

type Addr = {
  id: string;
  address: string;
  enabled: boolean;
  created_at: string;
  rotated_at: string | null;
};
type Guide = { provider: string; title: string; steps: string[] };
type Msg = {
  id: string;
  sender: string;
  subject: string;
  provider: string;
  status: string;
  jobs_created: number;
  created_at: string;
};
type Tg = {
  linked: boolean;
  link_code: string | null;
  bot_username: string | null;
  code_expires_at: string | null;
};

const addr = useQuery({
  queryKey: computed(() => ["inbound-address", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/inbound/address",
      throwOnError: true,
    });
    return data as Addr;
  },
  enabled: computed(() => Boolean(ws.currentId) && ws.canManage),
});

const guides = useQuery({
  queryKey: computed(() => ["inbound-guides", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/inbound/guides",
      throwOnError: true,
    });
    return (data ?? []) as Guide[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const messages = useQuery({
  queryKey: computed(() => ["inbound-messages", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/inbound/messages",
      throwOnError: true,
    });
    return (data ?? []) as Msg[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const telegram = useQuery({
  queryKey: computed(() => ["telegram-link", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/telegram/link",
      throwOnError: true,
    });
    return data as Tg;
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const rotate = useMutation({
  mutationFn: async () => {
    await client.post({ url: "/api/v1/inbound/address/rotate", throwOnError: true });
  },
  onSuccess: async () => {
    newOpen.value = false;
    await qc.invalidateQueries({ queryKey: ["inbound-address", ws.currentId] });
    toast.push({ title: t("alerts.newAddressDone"), tone: "success" });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const startTg = useMutation({
  mutationFn: async () => {
    const { data } = await client.post({
      url: "/api/v1/telegram/link",
      throwOnError: true,
    });
    return data as Tg;
  },
  onSuccess: async () => {
    await qc.invalidateQueries({ queryKey: ["telegram-link", ws.currentId] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const unlinkTg = useMutation({
  mutationFn: async () => {
    await client.post({ url: "/api/v1/telegram/unlink", throwOnError: true });
  },
  onSuccess: async () => {
    await qc.invalidateQueries({ queryKey: ["telegram-link", ws.currentId] });
    toast.push({ title: t("alerts.telegramUnlinked"), tone: "success" });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.push({ title: t("common.copied") });
  } catch {
    toast.push({ title: t("common.copyFailed"), tone: "danger" });
  }
}

const tgDeepLink = computed(() => {
  const bot = telegram.data.value?.bot_username;
  const code = telegram.data.value?.link_code;
  if (!bot || !code) return "";
  return `https://t.me/${bot}?start=${code}`;
});

const STATE: Record<string, { key: string; tone: "neutral" | "accent" }> = {
  parsed: { key: "added", tone: "accent" },
  needs_review: { key: "needsLook", tone: "neutral" },
  ignored: { key: "skipped", tone: "neutral" },
  received: { key: "reading", tone: "neutral" },
};
function stateOf(status: string) {
  return STATE[status] ?? { key: "reading", tone: "neutral" as const };
}
const rows = computed(() => messages.data.value ?? []);
</script>

<template>
  <section class="flex max-w-2xl flex-col gap-6">
    <PageHeader :title="t('settings.alerts')" :lede="t('settings.alertsLede')" />

    <FnSectionCard
      v-if="ws.canManage"
      :title="t('alerts.address')"
      :intro="t('alerts.addressIntro')"
    >
      <FnSkeletonGroup
        v-if="addr.isPending.value"
        :label="t('common.loading')"
        class="flex flex-col gap-3"
      >
        <div class="flex flex-wrap items-center gap-2">
          <FnSkeleton class="h-10 w-64 max-w-full rounded-lg" />
          <FnSkeleton class="h-11 w-28 rounded-md" />
        </div>
        <FnSkeleton class="h-11 w-32 rounded-md" />
      </FnSkeletonGroup>
      <div v-else-if="addr.data.value" class="flex flex-col gap-3">
        <div class="flex flex-wrap items-center gap-2">
          <code
            class="max-w-full rounded-lg border border-rule bg-paper-2 px-3 py-2 font-mono text-xs break-all text-ink-900"
            >{{ addr.data.value.address }}</code
          >
          <FnButton size="sm" tone="primary" @click="copy(addr.data.value.address)">
            {{ t("alerts.copyAddress") }}
          </FnButton>
        </div>
        <div>
          <FnButton size="sm" tone="ghost" @click="newOpen = true">
            {{ t("alerts.newAddress") }}
          </FnButton>
        </div>
      </div>
    </FnSectionCard>

    <FnSectionCard
      :title="t('alerts.setup')"
      :intro="t('alerts.setupIntro')"
      :more-label="t('alerts.setupMore')"
    >
      <template #more>
        <p v-if="guides.isError.value" role="alert" class="text-sm text-oxblood-600">
          {{ apiError(guides.error.value) }}
        </p>
        <ul v-else class="flex flex-col gap-4">
          <li v-for="g in guides.data.value ?? []" :key="g.provider" class="flex flex-col gap-1">
            <p class="text-sm font-semibold text-ink-900">{{ g.title }}</p>
            <ol class="flex list-decimal flex-col gap-1 pl-5 text-sm text-ink-600">
              <li v-for="(step, i) in g.steps" :key="i">{{ step }}</li>
            </ol>
          </li>
        </ul>
      </template>
    </FnSectionCard>

    <FnSectionCard :title="t('alerts.telegram')" :intro="t('alerts.telegramIntro')">
      <FnSkeletonGroup
        v-if="telegram.isPending.value"
        :label="t('common.loading')"
        class="flex flex-wrap items-center gap-2"
      >
        <FnSkeleton class="h-7 w-24 rounded-full" />
        <FnSkeleton class="h-11 w-36 rounded-md" />
      </FnSkeletonGroup>
      <div v-else class="flex flex-wrap items-center gap-2">
        <FnChip v-if="telegram.data.value?.linked" tone="accent">
          {{ t("alerts.telegramLinked") }}
        </FnChip>
        <FnButton
          v-if="!telegram.data.value?.linked"
          size="sm"
          tone="quiet"
          :loading="startTg.isPending.value"
          @click="startTg.mutate()"
          >{{ t("alerts.telegramLink") }}</FnButton
        >
        <FnButton
          v-else
          size="sm"
          tone="ghost"
          :loading="unlinkTg.isPending.value"
          @click="unlinkTg.mutate()"
          >{{ t("alerts.telegramUnlink") }}</FnButton
        >
        <a
          v-if="tgDeepLink"
          :href="tgDeepLink"
          target="_blank"
          rel="noopener"
          class="text-sm font-semibold text-brand-700 underline"
          >{{ t("alerts.openBot") }}</a
        >
      </div>
      <code
        v-if="telegram.data.value?.link_code"
        class="w-fit rounded-lg border border-rule bg-paper-2 px-3 py-2 font-mono text-xs text-ink-900"
        >{{ telegram.data.value.link_code }}</code
      >
    </FnSectionCard>

    <FnSectionCard :title="t('alerts.recent')" :intro="t('alerts.recentIntro')">
      <FnSkeletonGroup v-if="messages.isPending.value" :label="t('common.loading')">
        <ul class="flex flex-col divide-y divide-rule">
          <li
            v-for="n in 3"
            :key="n"
            class="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 py-3 text-sm"
          >
            <div class="flex min-w-0 flex-1 flex-col gap-2">
              <FnSkeleton class="h-4 w-3/5" />
              <FnSkeleton class="h-3.5 w-2/5" />
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <FnSkeleton class="h-6 w-20 rounded-full" />
              <FnSkeleton class="h-3 w-24" />
            </div>
          </li>
        </ul>
      </FnSkeletonGroup>
      <FnEmptyState
        v-else-if="messages.isError.value"
        :title="t('alerts.loadError')"
        :body="apiError(messages.error.value)"
        tone="danger"
      >
        <FnButton size="sm" @click="messages.refetch()">{{ t("common.retry") }}</FnButton>
      </FnEmptyState>
      <div v-else-if="!rows.length" class="flex flex-col gap-1">
        <p class="font-semibold text-ink-900">{{ t("alerts.empty") }}</p>
        <p class="text-sm text-ink-600">{{ t("alerts.emptyBody") }}</p>
      </div>
      <ul v-else class="flex flex-col divide-y divide-rule">
        <li
          v-for="m in rows"
          :key="m.id"
          class="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 py-3 text-sm"
        >
          <div class="flex min-w-0 flex-col gap-0.5">
            <p class="font-medium text-ink-900">{{ m.subject || m.sender }}</p>
            <p class="text-ink-600">
              {{ m.provider
              }}<span v-if="m.jobs_created">
                · {{ t("alerts.jobsAdded", { n: m.jobs_created }) }}</span
              >
            </p>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <FnChip :tone="stateOf(m.status).tone">{{
              t(`alerts.state_${stateOf(m.status).key}`)
            }}</FnChip>
            <span class="text-xs text-ink-400">{{ fmt.dateTime(m.created_at) }}</span>
          </div>
        </li>
      </ul>
    </FnSectionCard>

    <FnDialog
      v-model:open="newOpen"
      :title="t('alerts.newAddressTitle')"
      :description="t('alerts.newAddressBody')"
      :close-label="t('common.close')"
    >
      <div class="flex justify-end gap-2">
        <FnButton @click="newOpen = false">{{ t("common.cancel") }}</FnButton>
        <FnButton tone="danger" :loading="rotate.isPending.value" @click="rotate.mutate()">
          {{ t("alerts.newAddress") }}
        </FnButton>
      </div>
    </FnDialog>
  </section>
</template>
