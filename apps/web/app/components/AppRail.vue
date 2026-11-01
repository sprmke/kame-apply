<script setup lang="ts">
import { FnTooltip } from "@kame/ui";
import { NAV } from "~/lib/nav";

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
    class="hidden w-16 shrink-0 flex-col items-center gap-1 border-r border-rule bg-paper-1 py-3 md:flex"
  >
    <NuxtLink
      to="/"
      class="mb-3 grid size-11 place-items-center rounded-sm"
      :aria-label="t('app.name')"
    >
      <BrandMark :size="30" />
    </NuxtLink>
    <template v-for="item in NAV" :key="item.key">
      <div v-if="item.key === 'settings'" class="mt-auto flex flex-col items-center gap-1">
        <FnTooltip :text="t('shell.needsYou')">
          <NuxtLink
            to="/notifications"
            )
            class="relative grid size-11 place-items-center rounded-sm text-ink-600 hover:bg-paper-2"
            :aria-label="t('shell.needsYouCount', needsYou)"
          >
            <NavIcon name="ph:bell" />
            <span
              v-if="needsYou > 0"
              class="absolute top-1 right-1 grid min-w-4 place-items-center rounded-full bg-persimmon-500 px-1 text-[0.625rem] leading-4 font-semibold text-on-brand"
              >{{ needsYou }}</span
            >
          </NuxtLink>
        </FnTooltip>
        <FnTooltip :text="t(`nav.${item.key}`)">
          <NuxtLink
            :to="item.to"
            class="relative grid size-11 place-items-center rounded-sm hover:bg-paper-2"
            :class="active(item.to) ? 'bg-paper-2 text-ink-900' : 'text-ink-600'"
            :aria-label="t(`nav.${item.key}`)"
            :aria-current="active(item.to) ? 'page' : undefined"
          >
            <span
              v-if="active(item.to)"
              class="absolute inset-y-2 left-0 w-0.5 rounded-full bg-persimmon-500"
              aria-hidden="true"
            />
            <NavIcon :name="item.icon" />
          </NuxtLink>
        </FnTooltip>
      </div>
      <FnTooltip v-else :text="t(`nav.${item.key}`)">
        <NuxtLink
          :to="item.to"
          class="relative grid size-11 place-items-center rounded-sm hover:bg-paper-2"
          :class="active(item.to) ? 'bg-paper-2 text-ink-900' : 'text-ink-600'"
          :aria-label="t(`nav.${item.key}`)"
          :aria-current="active(item.to) ? 'page' : undefined"
        >
          <span
            v-if="active(item.to)"
            class="absolute inset-y-2 left-0 w-0.5 rounded-full bg-persimmon-500"
            aria-hidden="true"
          />
          <NavIcon :name="item.icon" />
        </NuxtLink>
      </FnTooltip>
    </template>
  </nav>
</template>
