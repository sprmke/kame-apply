<script setup lang="ts">
import { FnDialog } from "@kame/ui";
import { NAV } from "~/lib/nav";

const { t } = useI18n();
const route = useRoute();
defineProps<{ needsYou: number }>();
const moreOpen = ref(false);
watch(
  () => route.path,
  () => (moreOpen.value = false),
);

const byKey = (k: string) => NAV.find((n) => n.key === k)!;
const left = [byKey("today"), byKey("jobs")];
const right = [byKey("applications")];
const more = NAV.filter((n) => !["today", "jobs", "applications"].includes(n.key));

function active(to: string) {
  return to === "/" ? route.path === "/" : route.path.startsWith(to);
}
</script>

<template>
  <nav
    :aria-label="t('shell.primaryNav')"
    class="fixed inset-x-0 bottom-0 z-30 grid h-16 grid-cols-5 items-center border-t border-rule bg-paper-1 pb-[env(safe-area-inset-bottom)] md:hidden"
  >
    <NuxtLink
      v-for="item in left"
      :key="item.key"
      :to="item.to"
      class="flex min-h-11 flex-col items-center justify-center gap-0.5 text-xs"
      :class="active(item.to) ? 'font-medium text-ink-900' : 'text-ink-600'"
      :aria-current="active(item.to) ? 'page' : undefined"
    >
      <NavIcon :name="item.icon" />{{ t(`nav.${item.key}`) }}
    </NuxtLink>

    <NuxtLink
      to="/notifications"
      )
      class="mx-auto -mt-5 grid size-14 place-items-center focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-persimmon-700"
      :class="needsYou > 0 ? 'text-on-brand' : 'text-ink-900'"
      :aria-label="t('shell.needsYouCount', needsYou)"
    >
      <!-- Quiet at rest (paper with an ink outline); persimmon only when something needs you. -->
      <svg viewBox="0 0 32 32" class="absolute size-14" aria-hidden="true">
        <path
          d="M16 1.5 29 9v14L16 30.5 3 23V9L16 1.5Z"
          :class="
            needsYou > 0 ? 'fill-persimmon-500 stroke-paper-1' : 'fill-paper-1 stroke-ink-900'
          "
          stroke-width="1.5"
        />
      </svg>
      <span class="relative text-base font-semibold">{{ needsYou }}</span>
    </NuxtLink>

    <NuxtLink
      v-for="item in right"
      :key="item.key"
      :to="item.to"
      class="flex min-h-11 flex-col items-center justify-center gap-0.5 text-xs"
      :class="active(item.to) ? 'font-medium text-ink-900' : 'text-ink-600'"
      :aria-current="active(item.to) ? 'page' : undefined"
    >
      <NavIcon :name="item.icon" />{{ t(`nav.${item.key}`) }}
    </NuxtLink>
    <button
      type="button"
      class="flex min-h-11 flex-col items-center justify-center gap-0.5 text-xs text-ink-600"
      :aria-expanded="moreOpen"
      @click="moreOpen = true"
    >
      <NavIcon name="ph:dots-three-outline" />{{ t("shell.more") }}
    </button>
  </nav>

  <FnDialog
    v-model:open="moreOpen"
    variant="sheet"
    :title="t('shell.more')"
    :close-label="t('common.close')"
  >
    <ul class="flex flex-col">
      <li v-for="item in more" :key="item.key">
        <NuxtLink
          :to="item.to"
          class="flex min-h-12 items-center gap-3 rounded-sm px-2 text-base text-ink-900 hover:bg-paper-2"
        >
          <NavIcon :name="item.icon" />{{ t(`nav.${item.key}`) }}
        </NuxtLink>
      </li>
    </ul>
  </FnDialog>
</template>
