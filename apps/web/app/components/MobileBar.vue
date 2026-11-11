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

function active(to: string) {
  return to === "/" ? route.path === "/" : route.path.startsWith(to);
}
</script>

<template>
  <nav
    :aria-label="t('shell.primaryNav')"
    class="fixed inset-x-0 bottom-0 z-30 grid h-16 grid-cols-5 items-center border-t border-rule bg-paper-1 pb-[env(safe-area-inset-bottom)] shadow-[0_-8px_24px_-20px_rgba(16,24,40,0.35)] md:hidden"
  >
    <NuxtLink
      v-for="item in primary"
      :key="item.key"
      :to="item.to"
      class="relative flex min-h-11 flex-col items-center justify-center gap-0.5 text-[0.6875rem]"
      :class="active(item.to) ? 'font-semibold text-brand-700' : 'text-ink-600'"
      :aria-current="active(item.to) ? 'page' : undefined"
    >
      <NavIcon :name="item.icon" :size="18" />
      {{ t(`nav.${item.key}`) }}
      <span
        v-if="item.key === 'today' && needsYou > 0"
        class="absolute top-1 right-1/2 mr-2 grid min-w-4 place-items-center rounded-full bg-brand-500 px-1 text-[0.5625rem] leading-4 font-semibold text-on-brand"
        >{{ needsYou }}</span
      >
    </NuxtLink>
    <button
      type="button"
      class="flex min-h-11 flex-col items-center justify-center gap-0.5 text-[0.6875rem] text-ink-600"
      :aria-expanded="moreOpen"
      aria-label="More"
      @click="moreOpen = true"
    >
      <NavIcon name="ph:dots-three-outline" :size="18" />{{ t("shell.more") }}
    </button>
  </nav>

  <FnDialog
    v-model:open="moreOpen"
    variant="sheet"
    :title="t('shell.more')"
    :close-label="t('common.close')"
  >
    <div class="flex flex-col gap-4">
      <NuxtLink
        to="/notifications"
        class="flex min-h-12 items-center gap-3 rounded-md bg-paper-2 px-3 text-base text-ink-900"
      >
        <NavIcon name="ph:bell" :size="18" />
        <span class="flex-1">{{ t("shell.needsYou") }}</span>
        <span
          v-if="needsYou > 0"
          class="grid min-w-5 place-items-center rounded-full bg-brand-500 px-1.5 text-[0.625rem] leading-5 font-semibold text-on-brand"
          >{{ needsYou }}</span
        >
      </NuxtLink>

      <section class="flex flex-col">
        <p class="px-3 pb-1 text-[0.6875rem] tracking-[0.14em] text-ink-400 uppercase">
          {{ t("shell.account") }}
        </p>
        <NuxtLink
          :to="account.to"
          class="flex min-h-12 items-center gap-3 rounded-md px-3 text-base text-ink-900 hover:bg-paper-2"
        >
          <NavIcon :name="account.icon" :size="18" />{{ t(`nav.${account.key}`) }}
        </NuxtLink>
        <NuxtLink
          :to="SETTINGS_NAV.to"
          class="flex min-h-12 items-center gap-3 rounded-md px-3 text-base text-ink-900 hover:bg-paper-2"
        >
          <NavIcon :name="SETTINGS_NAV.icon" :size="18" />{{ t(`nav.${SETTINGS_NAV.key}`) }}
        </NuxtLink>
      </section>

      <section class="flex flex-col">
        <p class="px-3 pb-1 text-[0.6875rem] tracking-[0.14em] text-ink-400 uppercase">
          {{ t("shell.moreTools") }}
        </p>
        <NuxtLink
          v-for="item in MORE_NAV"
          :key="item.key"
          :to="item.to"
          class="flex min-h-12 items-center gap-3 rounded-md px-3 text-base text-ink-900 hover:bg-paper-2"
        >
          <NavIcon :name="item.icon" :size="18" />{{ t(`nav.${item.key}`) }}
        </NuxtLink>
      </section>
    </div>
  </FnDialog>
</template>
