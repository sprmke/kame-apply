<script setup lang="ts">
import { FnDialog } from "@kame/ui";
import { MORE_NAV, PRIMARY_NAV, SETTINGS_NAV } from "~/lib/nav";

const { t } = useI18n();
const route = useRoute();
defineProps<{ needsYou: number }>();
const moreOpen = ref(false);
watch(
  () => route.path,
  () => (moreOpen.value = false),
);

const primary = PRIMARY_NAV.slice(0, 4);
const account = PRIMARY_NAV.find((item) => item.key === "profile")!;
const tools = MORE_NAV;

function active(to: string) {
  return to === "/" ? route.path === "/" : route.path.startsWith(to);
}
</script>

<template>
  <nav
    :aria-label="t('shell.primaryNav')"
    class="fixed inset-x-0 bottom-0 z-30 grid min-h-16 grid-cols-5 items-stretch border-t border-rule bg-paper-1 pb-[env(safe-area-inset-bottom)] shadow-[0_-8px_24px_-20px_rgba(16,24,40,0.35)] md:hidden"
  >
    <NuxtLink
      v-for="item in primary"
      :key="item.key"
      :to="item.to"
      class="relative flex min-h-11 flex-col items-center justify-center gap-0.5 px-1 text-[0.6875rem]"
      :class="active(item.to) ? 'font-semibold text-brand-700' : 'text-ink-600'"
      :aria-current="active(item.to) ? 'page' : undefined"
    >
      <NavIcon :name="item.icon" :size="20" />
      <span class="truncate">{{ t(`nav.${item.key}`) }}</span>
      <span
        v-if="item.key === 'today' && needsYou > 0"
        class="absolute top-1.5 right-1/2 mr-2 grid min-w-4 place-items-center rounded-full bg-brand-500 px-1 text-[0.5625rem] leading-4 font-semibold text-on-brand"
        >{{ needsYou }}</span
      >
    </NuxtLink>
    <button
      type="button"
      class="relative flex min-h-11 flex-col items-center justify-center gap-0.5 px-1 text-[0.6875rem]"
      :class="needsYou > 0 ? 'text-brand-700' : 'text-ink-600'"
      :aria-expanded="moreOpen"
      :aria-label="t('shell.more')"
      @click="moreOpen = true"
    >
      <NavIcon name="ph:dots-three-outline" :size="20" />{{ t("shell.more") }}
      <span
        v-if="needsYou > 0"
        class="absolute top-1 right-3 grid min-w-4 place-items-center rounded-full bg-brand-500 px-1 text-[0.5625rem] leading-4 font-semibold text-on-brand"
        >{{ needsYou }}</span
      >
    </button>
  </nav>

  <FnDialog
    v-model:open="moreOpen"
    variant="sheet"
    :title="t('shell.more')"
    :close-label="t('common.close')"
  >
    <div class="flex flex-col gap-5 pb-[env(safe-area-inset-bottom)]">
      <NuxtLink
        to="/needs-you"
        class="flex min-h-12 items-center gap-3 rounded-md bg-brand-50 px-3 text-base font-semibold text-brand-700"
      >
        <NavIcon name="ph:bell" :size="20" />
        <span class="flex-1">{{ t("shell.needsYou") }}</span>
        <span
          v-if="needsYou > 0"
          class="grid min-w-5 place-items-center rounded-full bg-brand-500 px-1.5 text-[0.6875rem] leading-5 font-semibold text-on-brand"
          >{{ needsYou }}</span
        >
      </NuxtLink>

      <section class="flex flex-col">
        <p class="px-3 pb-1 text-xs font-semibold tracking-[0.12em] text-ink-400 uppercase">
          {{ t("shell.tools") }}
        </p>
        <NuxtLink
          v-for="item in tools"
          :key="item.key"
          :to="item.to"
          class="flex min-h-12 flex-col justify-center gap-0.5 rounded-md px-3 py-1.5 hover:bg-paper-2"
        >
          <span class="flex items-center gap-3 text-base text-ink-900">
            <NavIcon :name="item.icon" :size="20" />{{ t(`nav.${item.key}`) }}
          </span>
          <span v-if="item.descKey" class="pl-8 text-xs text-ink-400">{{ t(item.descKey) }}</span>
        </NuxtLink>
      </section>

      <section class="flex flex-col border-t border-rule pt-2">
        <NuxtLink
          :to="account.to"
          class="flex min-h-12 items-center gap-3 rounded-md px-3 text-base text-ink-900 hover:bg-paper-2"
        >
          <NavIcon :name="account.icon" :size="20" />{{ t(`nav.${account.key}`) }}
        </NuxtLink>
        <NuxtLink
          to="/help"
          class="flex min-h-12 items-center gap-3 rounded-md px-3 text-base text-ink-900 hover:bg-paper-2"
        >
          <NavIcon name="ph:question" :size="20" />{{ t("shell.help") }}
        </NuxtLink>
        <NuxtLink
          :to="SETTINGS_NAV.to"
          class="flex min-h-12 items-center gap-3 rounded-md px-3 text-base text-ink-900 hover:bg-paper-2"
        >
          <NavIcon :name="SETTINGS_NAV.icon" :size="20" />{{ t("nav.settings") }}
        </NuxtLink>
      </section>
    </div>
  </FnDialog>
</template>
