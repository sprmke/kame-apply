<script setup lang="ts">
const { t } = useI18n();
const route = useRoute();

const tabs = computed(() => [
  { to: "/profile", key: "career", exact: true },
  { to: "/profile/answers", key: "answers" },
  { to: "/profile/voice", key: "voice" },
  { to: "/profile/documents", key: "documents" },
]);

function active(to: string, exact?: boolean) {
  return exact ? route.path === to : route.path.startsWith(to);
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-6">
    <PageHeader :title="t('career.title')" :lede="t('career.lede')" />
    <nav :aria-label="t('career.nav')" class="flex gap-1 overflow-x-auto rounded-lg bg-paper-2 p-1">
      <NuxtLink
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.to"
        class="flex min-h-11 shrink-0 items-center rounded-md px-3 text-sm font-semibold whitespace-nowrap sm:px-4"
        :class="
          active(tab.to, tab.exact)
            ? 'bg-paper-1 text-brand-700 shadow-[var(--shadow-card)]'
            : 'text-ink-600 hover:text-ink-900'
        "
        :aria-current="active(tab.to, tab.exact) ? 'page' : undefined"
      >
        {{ t(`career.tabs.${tab.key}`) }}
      </NuxtLink>
    </nav>
    <div class="rounded-xl border border-rule bg-paper-1 p-6 shadow-[var(--shadow-card)]">
      <NuxtPage />
    </div>
  </div>
</template>
