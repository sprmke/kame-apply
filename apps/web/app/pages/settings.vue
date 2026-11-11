<script setup lang="ts">
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const route = useRoute();
const ws = useWorkspaceStore();

const tabs = computed(() =>
  [
    { to: "/settings/general", label: t("settings.general"), show: true },
    { to: "/settings/members", label: t("settings.members"), show: true },
    { to: "/settings/ai", label: t("settings.ai"), show: true },
    { to: "/settings/integrations", label: t("settings.integrations"), show: true },
    { to: "/settings/notifications", label: t("settings.notifications"), show: true },
    { to: "/settings/alerts", label: t("settings.alerts"), show: true },
    { to: "/settings/sources", label: t("settings.sources"), show: ws.canManage },
    { to: "/settings/ops", label: t("settings.ops"), show: ws.canManage },
    { to: "/settings/activity", label: t("settings.activity"), show: ws.canManage },
    { to: "/settings/danger", label: t("settings.danger"), show: true },
    { to: "/settings/profile", label: t("settings.profile"), show: true },
    { to: "/settings/sessions", label: t("settings.sessions"), show: true },
  ].filter((x) => x.show),
);
</script>

<template>
  <div class="mx-auto flex max-w-[920px] flex-col gap-8">
    <nav :aria-label="t('settings.nav')">
      <ul class="flex gap-1 overflow-x-auto rounded-lg bg-paper-2 p-1 md:flex-wrap">
        <li v-for="tab in tabs" :key="tab.to">
          <NuxtLink
            :to="tab.to"
            class="flex min-h-11 shrink-0 items-center rounded-md px-4 text-sm font-semibold whitespace-nowrap"
            :class="
              route.path === tab.to
                ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
                : 'text-ink-600 hover:text-ink-900'
            "
            :aria-current="route.path === tab.to ? 'page' : undefined"
            >{{ tab.label }}</NuxtLink
          >
        </li>
      </ul>
    </nav>
    <div class="rounded-xl border border-rule bg-paper-1 p-6 shadow-[var(--shadow-card)]">
      <NuxtPage />
    </div>
  </div>
</template>
