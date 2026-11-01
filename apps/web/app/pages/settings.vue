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
  <div class="mx-auto flex max-w-[880px] flex-col gap-6">
    <nav
      :aria-label="t('settings.nav')"
      class="-mx-4 overflow-x-auto px-4 [mask-image:linear-gradient(to_right,black_calc(100%-28px),transparent)] md:mx-0 md:px-0 md:[mask-image:none]"
    >
      <ul class="flex gap-1 border-b border-rule">
        <li v-for="tab in tabs" :key="tab.to">
          <NuxtLink
            :to="tab.to"
            class="-mb-px flex min-h-11 items-center border-b-2 px-3 text-sm whitespace-nowrap"
            :class="
              route.path === tab.to
                ? 'border-ink-900 font-medium text-ink-900'
                : 'border-transparent text-ink-600 hover:text-ink-900'
            "
            :aria-current="route.path === tab.to ? 'page' : undefined"
            >{{ tab.label }}</NuxtLink
          >
        </li>
      </ul>
    </nav>
    <NuxtPage />
  </div>
</template>
