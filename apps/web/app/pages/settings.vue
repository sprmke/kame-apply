<script setup lang="ts">
import { FnDialog } from "@kame/ui";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const route = useRoute();
const ws = useWorkspaceStore();
const mobileOpen = ref(false);

type NavLink = { to: string; label: string };

const groups = computed<{ key: string; label: string; links: NavLink[] }[]>(() => {
  const workspace: NavLink[] = [
    { to: "/settings/general", label: t("settings.general") },
    { to: "/settings/members", label: t("settings.members") },
    { to: "/settings/ai", label: t("settings.ai") },
    { to: "/settings/integrations", label: t("settings.integrations") },
    { to: "/settings/notifications", label: t("settings.notifications") },
    { to: "/settings/alerts", label: t("settings.alerts") },
  ];
  const admin: NavLink[] = ws.canManage
    ? [
        { to: "/settings/sources", label: t("settings.sources") },
        { to: "/settings/ops", label: t("settings.ops") },
        { to: "/settings/activity", label: t("settings.activity") },
      ]
    : [];
  const out = [{ key: "workspace", label: t("shell.workspace"), links: workspace }];
  if (admin.length) out.push({ key: "admin", label: t("settings.groupAdmin"), links: admin });
  out.push({
    key: "account",
    label: t("shell.account"),
    links: [
      { to: "/settings/profile", label: t("settings.profile") },
      { to: "/settings/sessions", label: t("settings.sessions") },
    ],
  });
  return out;
});

const danger = computed<NavLink>(() => ({
  to: "/settings/danger",
  label: t("settings.danger"),
}));

/** Longest matching section, so nested routes such as /settings/integrations/consent keep their parent active. */
const activeTo = computed(() => {
  const links = [...(groups.value.flatMap((g) => g.links) ?? []), danger.value];
  return links
    .filter((l) => route.path === l.to || route.path.startsWith(`${l.to}/`))
    .sort((a, b) => b.to.length - a.to.length)[0]?.to;
});
const current = computed(
  () =>
    [...groups.value.flatMap((g) => g.links), danger.value].find((l) => l.to === activeTo.value) ??
    groups.value[0]?.links[0],
);

watch(
  () => route.path,
  () => {
    mobileOpen.value = false;
  },
);

function isActive(to: string) {
  return activeTo.value === to;
}
function linkClass(to: string) {
  return isActive(to)
    ? "bg-brand-50 font-semibold text-brand-700"
    : "text-ink-600 hover:bg-paper-2 hover:text-ink-900";
}
</script>

<template>
  <div
    class="mx-auto flex w-full max-w-[1080px] flex-col gap-6 xl:grid xl:grid-cols-[13.5rem_minmax(0,1fr)] xl:items-start xl:gap-10"
  >
    <nav class="hidden xl:block" :aria-label="t('settings.nav')">
      <div class="sticky top-24 flex max-h-[calc(100dvh-8rem)] flex-col gap-5 overflow-y-auto">
        <div v-for="group in groups" :key="group.key" class="flex flex-col gap-0.5">
          <p
            class="px-3 pb-1 text-[0.6875rem] font-medium tracking-[0.14em] text-ink-400 uppercase"
          >
            {{ group.label }}
          </p>
          <NuxtLink
            v-for="link in group.links"
            :key="link.to"
            :to="link.to"
            class="flex min-h-11 items-center rounded-md px-3 text-sm transition-colors duration-150"
            :class="linkClass(link.to)"
            :aria-current="isActive(link.to) ? 'page' : undefined"
            >{{ link.label }}</NuxtLink
          >
        </div>
        <div class="border-t border-rule pt-3">
          <NuxtLink
            :to="danger.to"
            class="flex min-h-11 items-center rounded-md px-3 text-sm text-oxblood-600"
            :class="isActive(danger.to) ? 'bg-paper-2 font-semibold' : 'hover:bg-paper-2'"
            :aria-current="isActive(danger.to) ? 'page' : undefined"
            >{{ danger.label }}</NuxtLink
          >
        </div>
      </div>
    </nav>

    <div class="xl:hidden">
      <button
        type="button"
        class="flex min-h-12 w-full items-center gap-2 rounded-xl border border-rule bg-paper-1 px-4 text-left shadow-[var(--shadow-card)]"
        :aria-expanded="mobileOpen"
        @click="mobileOpen = true"
      >
        <span class="text-sm font-semibold text-ink-900">{{ t("settings.nav") }}</span>
        <span class="min-w-0 flex-1 truncate text-sm text-ink-600">/ {{ current?.label }}</span>
        <NavIcon name="ph:caret-down" :size="16" class="shrink-0 text-ink-600" />
      </button>
      <FnDialog
        v-model:open="mobileOpen"
        variant="sheet"
        :title="t('settings.nav')"
        :close-label="t('common.close')"
      >
        <nav class="flex flex-col gap-0.5" :aria-label="t('settings.nav')">
          <div v-for="group in groups" :key="group.key" class="flex flex-col gap-0.5 pb-2">
            <p
              class="px-3 pt-2 pb-1 text-[0.6875rem] font-medium tracking-[0.14em] text-ink-400 uppercase"
            >
              {{ group.label }}
            </p>
            <NuxtLink
              v-for="link in group.links"
              :key="link.to"
              :to="link.to"
              class="flex min-h-12 items-center rounded-md px-3 text-sm"
              :class="linkClass(link.to)"
              :aria-current="isActive(link.to) ? 'page' : undefined"
              >{{ link.label }}</NuxtLink
            >
          </div>
          <div class="border-t border-rule pt-2">
            <NuxtLink
              :to="danger.to"
              class="flex min-h-12 items-center rounded-md px-3 text-sm text-oxblood-600"
              :class="isActive(danger.to) ? 'bg-paper-2 font-semibold' : 'hover:bg-paper-2'"
              :aria-current="isActive(danger.to) ? 'page' : undefined"
              >{{ danger.label }}</NuxtLink
            >
          </div>
        </nav>
      </FnDialog>
    </div>

    <div
      class="min-w-0 rounded-xl border border-rule bg-paper-1 p-5 shadow-[var(--shadow-card)] sm:p-6"
    >
      <NuxtPage />
    </div>
  </div>
</template>
