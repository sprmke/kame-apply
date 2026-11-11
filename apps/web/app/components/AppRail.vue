<script setup lang="ts">
import { MORE_NAV, PRIMARY_NAV, SETTINGS_NAV } from "~/lib/nav";

const { t } = useI18n();
const route = useRoute();
defineProps<{ needsYou: number }>();

function active(to: string) {
  return to === "/" ? route.path === "/" : route.path.startsWith(to);
}
</script>

<template>
  <nav
    :aria-label="t('shell.primaryNav')"
    class="hidden w-60 shrink-0 flex-col overflow-y-auto border-r border-rule bg-paper-1 md:flex"
  >
    <NuxtLink to="/" class="flex items-center gap-2 px-5 py-5" :aria-label="t('app.name')">
      <BrandMark :size="28" wordmark />
    </NuxtLink>

    <div class="px-3">
      <p class="px-3 pb-2 text-[0.6875rem] font-medium tracking-[0.14em] text-ink-400 uppercase">
        {{ t("shell.workspace") }}
      </p>
      <NuxtLink
        v-for="item in PRIMARY_NAV"
        :key="item.key"
        :to="item.to"
        class="relative flex min-h-11 items-center gap-3 rounded-md px-3 text-sm transition-colors duration-150"
        :class="
          active(item.to)
            ? 'bg-brand-50 font-semibold text-brand-700'
            : 'text-ink-600 hover:bg-paper-2 hover:text-ink-900'
        "
        :aria-current="active(item.to) ? 'page' : undefined"
      >
        <NavIcon :name="item.icon" :size="18" />
        <span class="flex-1">{{ t(`nav.${item.key}`) }}</span>
        <span
          v-if="item.key === 'today' && needsYou > 0"
          class="grid min-w-5 place-items-center rounded-full bg-brand-500 px-1.5 text-[0.625rem] leading-5 font-semibold text-on-brand"
          >{{ needsYou }}</span
        >
      </NuxtLink>
    </div>

    <details class="mt-6 px-3">
      <summary
        class="flex min-h-11 cursor-pointer list-none items-center gap-3 rounded-md px-3 text-sm text-ink-600 hover:bg-paper-2 hover:text-ink-900"
      >
        <NavIcon name="ph:dots-three-outline" :size="18" />
        <span class="flex-1">{{ t("shell.moreTools") }}</span>
        <NavIcon name="ph:caret-down" :size="14" />
      </summary>
      <div class="mt-1 flex flex-col">
        <NuxtLink
          v-for="item in MORE_NAV"
          :key="item.key"
          :to="item.to"
          class="flex min-h-11 items-center gap-3 rounded-md px-3 text-sm"
          :class="
            active(item.to)
              ? 'bg-brand-50 font-semibold text-brand-700'
              : 'text-ink-600 hover:bg-paper-2 hover:text-ink-900'
          "
        >
          <NavIcon :name="item.icon" :size="18" />
          <span>{{ t(`nav.${item.key}`) }}</span>
        </NuxtLink>
      </div>
    </details>

    <div class="mt-auto flex flex-col gap-1 border-t border-rule px-3 py-3">
      <NuxtLink
        to="/notifications"
        class="flex min-h-11 items-center gap-3 rounded-md px-3 text-sm text-ink-600 hover:bg-paper-2 hover:text-ink-900"
      >
        <NavIcon name="ph:bell" :size="18" />
        <span class="flex-1">{{ t("shell.needsYou") }}</span>
        <span
          v-if="needsYou > 0"
          class="grid min-w-5 place-items-center rounded-full bg-brand-500 px-1.5 text-[0.625rem] leading-5 font-semibold text-on-brand"
          >{{ needsYou }}</span
        >
      </NuxtLink>
      <NuxtLink
        :to="SETTINGS_NAV.to"
        class="flex min-h-11 items-center gap-3 rounded-md px-3 text-sm"
        :class="
          active(SETTINGS_NAV.to)
            ? 'bg-brand-50 font-semibold text-brand-700'
            : 'text-ink-600 hover:bg-paper-2 hover:text-ink-900'
        "
      >
        <NavIcon :name="SETTINGS_NAV.icon" :size="18" />
        <span>{{ t(`nav.${SETTINGS_NAV.key}`) }}</span>
      </NuxtLink>
    </div>
  </nav>
</template>
