<script setup lang="ts">
import { MORE_NAV, PRIMARY_NAV, SETTINGS_NAV } from "~/lib/nav";

const { t } = useI18n();
const route = useRoute();
defineProps<{ needsYou: number }>();

const moreRef = ref<HTMLDetailsElement | null>(null);
const moreActive = computed(() => MORE_NAV.some((item) => active(item.to)));

onMounted(() => {
  if (moreActive.value && moreRef.value) moreRef.value.open = true;
});
watch(
  () => route.path,
  () => {
    if (moreActive.value && moreRef.value) moreRef.value.open = true;
  },
);

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

    <div class="flex flex-col gap-0.5 px-3">
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

    <details ref="moreRef" class="mt-5 px-3">
      <summary
        class="flex min-h-11 cursor-pointer list-none items-center gap-3 rounded-md px-3 text-sm hover:bg-paper-2 hover:text-ink-900"
        :class="moreActive ? 'font-semibold text-brand-700' : 'text-ink-600'"
      >
        <NavIcon name="ph:dots-three-outline" :size="18" />
        <span class="flex-1">{{ t("shell.tools") }}</span>
        <NavIcon name="ph:caret-down" :size="14" />
      </summary>
      <div class="mt-1 flex flex-col gap-0.5">
        <NuxtLink
          v-for="item in MORE_NAV"
          :key="item.key"
          :to="item.to"
          class="flex min-h-11 flex-col justify-center rounded-md px-3 py-1.5"
          :class="
            active(item.to)
              ? 'bg-brand-50 text-brand-700'
              : 'text-ink-600 hover:bg-paper-2 hover:text-ink-900'
          "
          :aria-current="active(item.to) ? 'page' : undefined"
        >
          <span
            class="flex items-center gap-3 text-sm"
            :class="active(item.to) ? 'font-semibold' : ''"
          >
            <NavIcon :name="item.icon" :size="18" />
            {{ t(`nav.${item.key}`) }}
          </span>
          <span
            v-if="item.descKey"
            class="pl-[1.875rem] text-xs leading-4 text-ink-400"
            :class="active(item.to) ? 'text-brand-700/80' : ''"
            >{{ t(item.descKey) }}</span
          >
        </NuxtLink>
      </div>
    </details>

    <div class="mt-auto flex flex-col gap-0.5 border-t border-rule px-3 py-3">
      <NuxtLink
        to="/needs-you"
        class="flex min-h-11 items-center gap-3 rounded-md px-3 text-sm"
        :class="
          active('/needs-you')
            ? 'bg-brand-50 font-semibold text-brand-700'
            : 'text-ink-600 hover:bg-paper-2 hover:text-ink-900'
        "
        :aria-current="active('/needs-you') ? 'page' : undefined"
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
        to="/help"
        class="flex min-h-11 items-center gap-3 rounded-md px-3 text-sm"
        :class="
          active('/help')
            ? 'bg-brand-50 font-semibold text-brand-700'
            : 'text-ink-600 hover:bg-paper-2 hover:text-ink-900'
        "
        :aria-current="active('/help') ? 'page' : undefined"
      >
        <NavIcon name="ph:question" :size="18" />
        <span>{{ t("shell.help") }}</span>
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
