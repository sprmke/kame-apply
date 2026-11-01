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
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 md:px-6">
    <PageHeader :title="t('career.title')" />
    <nav :aria-label="t('career.nav')" class="flex flex-wrap gap-1 border-b border-rule">
      <NuxtLink
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.to"
        class="relative px-3 py-2 text-sm"
        :class="
          active(tab.to, tab.exact) ? 'font-medium text-ink-900' : 'text-ink-600 hover:text-ink-900'
        "
        :aria-current="active(tab.to, tab.exact) ? 'page' : undefined"
      >
        <span
          v-if="active(tab.to, tab.exact)"
          class="absolute inset-x-2 bottom-0 h-0.5 bg-ink-900"
          aria-hidden="true"
        />
        {{ t(`career.tabs.${tab.key}`) }}
      </NuxtLink>
    </nav>
    <NuxtPage />
  </div>
</template>
