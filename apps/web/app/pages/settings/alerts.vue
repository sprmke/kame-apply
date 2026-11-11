<script setup lang="ts">
import { client } from "@kame/api-client";
import { FnButton, FnSkeleton, useToast } from "@kame/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

definePageMeta({ layout: "default" });

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();

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
    await qc.invalidateQueries({ queryKey: ["inbound-address", ws.currentId] });
    toast.push({ title: t("common.saved") });
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
    toast.push({ title: t("common.saved") });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.push({ title: t("common.copied") });
  } catch {
    toast.push({ title: t("common.copy"), tone: "danger" });
  }
}

const tgDeepLink = computed(() => {
  const bot = telegram.data.value?.bot_username;
  const code = telegram.data.value?.link_code;
  if (!bot || !code) return "";
  return `https://t.me/${bot}?start=${code}`;
});
</script>

<template>
  <div class="flex flex-col gap-8">
    <PageHeader :title="t('settings.alerts')" :lede="t('settings.alertsLede')" />

    <section v-if="ws.canManage" class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("alerts.address") }}</h2>
      <FnSkeleton v-if="addr.isPending.value" class="h-10 w-full" />
      <div v-else class="flex flex-wrap items-center gap-2">
        <code class="max-w-full break-all rounded-sm bg-paper-2 px-2 py-1 font-mono text-xs">{{
          addr.data.value?.address
        }}</code>
        <FnButton size="sm" tone="ghost" @click="copy(addr.data.value?.address || '')">{{
          t("common.copy")
        }}</FnButton>
        <FnButton
          size="sm"
          tone="quiet"
          :disabled="rotate.isPending.value"
          @click="rotate.mutate()"
          >{{ t("alerts.rotate") }}</FnButton
        >
      </div>
    </section>

    <section class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("alerts.setup") }}</h2>
      <ul class="flex flex-col gap-4">
        <li v-for="g in guides.data.value ?? []" :key="g.provider" class="flex flex-col gap-1">
          <p class="text-sm font-medium text-ink-900">{{ g.title }}</p>
          <ol class="list-decimal pl-5 text-sm text-ink-600">
            <li v-for="(step, i) in g.steps" :key="i">{{ step }}</li>
          </ol>
        </li>
      </ul>
    </section>

    <section class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("alerts.telegram") }}</h2>
      <p v-if="telegram.data.value?.linked" class="text-sm text-ink-600">
        {{ t("alerts.telegramLinked") }}
      </p>
      <div class="flex flex-wrap items-center gap-2">
        <FnButton
          v-if="!telegram.data.value?.linked"
          size="sm"
          :disabled="startTg.isPending.value"
          @click="startTg.mutate()"
          >{{ t("alerts.telegramLink") }}</FnButton
        >
        <FnButton
          v-else
          size="sm"
          tone="quiet"
          :disabled="unlinkTg.isPending.value"
          @click="unlinkTg.mutate()"
          >{{ t("alerts.telegramUnlink") }}</FnButton
        >
        <a
          v-if="tgDeepLink"
          :href="tgDeepLink"
          target="_blank"
          rel="noopener"
          class="text-sm text-brand-700 underline"
          >{{ t("alerts.openBot") }}</a
        >
      </div>
      <code
        v-if="telegram.data.value?.link_code"
        class="w-fit rounded-sm bg-paper-2 px-2 py-1 font-mono text-xs"
        >{{ telegram.data.value.link_code }}</code
      >
    </section>

    <section class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("alerts.recent") }}</h2>
      <ul class="divide-y divide-rule border border-rule">
        <li
          v-for="m in messages.data.value ?? []"
          :key="m.id"
          class="flex flex-col gap-1 px-3 py-3 text-sm"
        >
          <div class="flex flex-wrap justify-between gap-2">
            <span class="font-medium text-ink-900">{{ m.subject || m.provider }}</span>
            <span class="font-mono text-[0.6875rem] text-ink-600">{{ m.status }}</span>
          </div>
          <span class="text-ink-600"
            >{{ m.provider }} · {{ m.jobs_created }} jobs · {{ m.sender }}</span
          >
        </li>
        <li v-if="!(messages.data.value ?? []).length" class="px-3 py-4 text-sm text-ink-600">
          {{ t("alerts.empty") }}
        </li>
      </ul>
    </section>
  </div>
</template>
