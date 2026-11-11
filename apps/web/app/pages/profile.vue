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
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-8 md:px-6">
    <PageHeader :title="t('career.title')" :lede="t('career.lede')" />
    <nav :aria-label="t('career.nav')" class="flex flex-wrap gap-1 rounded-lg bg-paper-2 p-1">
      <NuxtLink
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.to"
        class="rounded-md px-4 py-2 text-sm font-semibold"
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
