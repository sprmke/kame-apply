<script setup lang="ts">
import { needsYouApiV1NeedsYouGet } from "@kame/api-client";
import { FnButton, FnToaster } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
useTheme();
const paletteOpen = ref(false);
const createOpen = ref(false);
const ws = useWorkspaceStore();

const needsQuery = useQuery({
  queryKey: computed(() => ["needs-you-count", ws.currentId]),
  queryFn: async () => {
    const { data } = await needsYouApiV1NeedsYouGet({ throwOnError: true });
    return data?.count ?? 0;
  },
  enabled: computed(() => Boolean(ws.currentId)),
  refetchInterval: 20_000,
});
const needsYou = computed(() => needsQuery.data.value ?? 0);
</script>

<template>
  <div class="flex min-h-dvh bg-paper-0 text-ink-900">
    <a
      href="#main"
      class="sr-only z-[70] rounded-sm bg-paper-1 px-3 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >{{ t("shell.skip") }}</a
    >
    <AppRail :needs-you="needsYou" />
    <div class="flex min-w-0 flex-1 flex-col">
      <header
        class="sticky top-0 z-20 flex h-14 items-center gap-2 border-b border-rule bg-paper-0 px-3 md:px-5"
      >
        <NuxtLink to="/" class="md:hidden" :aria-label="t('app.name')"
          ><BrandMark :size="28"
        /></NuxtLink>
        <WorkspaceSwitcher @create="createOpen = true" />
        <div class="ml-auto flex items-center gap-1">
          <span class="hidden md:inline-flex">
            <FnButton
              tone="quiet"
              size="sm"
              :aria-label="t('command.open')"
              @click="paletteOpen = true"
            >
              <NavIcon name="ph:magnifying-glass" :size="16" />
              <span class="text-ink-600">{{ t("command.search") }}</span>
              <kbd class="rounded-sm border border-rule px-1 font-mono text-[0.625rem] text-ink-600"
                >⌘K</kbd
              >
            </FnButton>
          </span>
          <span class="md:hidden">
            <FnButton
              tone="ghost"
              class="!w-11 !px-0"
              :aria-label="t('command.open')"
              @click="paletteOpen = true"
            >
              <NavIcon name="ph:magnifying-glass" />
            </FnButton>
          </span>
          <FeedbackButton />
          <ProfileMenu />
        </div>
      </header>
      <main
        id="main"
        tabindex="-1"
        class="flex-1 px-4 pt-6 pb-24 focus:outline-none md:px-8 md:pb-10"
      >
        <slot />
      </main>
    </div>
    <MobileBar :needs-you="needsYou" />
    <CommandPalette v-model:open="paletteOpen" @create-workspace="createOpen = true" />
    <CreateWorkspaceDialog v-model:open="createOpen" />
    <FnToaster :dismiss-label="t('common.dismiss')" />
  </div>
</template>
