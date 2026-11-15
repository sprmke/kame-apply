<script setup lang="ts">
import { FnButton } from "@kame/ui";

/** One-time panel after setup apply. Each page keeps its own AI control for the next step. */
const props = defineProps<{ trackId: string }>();
const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const storageKey = computed(() => `kame.setupDone.${props.trackId}`);
const visible = ref(false);

onMounted(() => {
  visible.value =
    route.query.setup_done === "1" && window.localStorage.getItem(storageKey.value) !== "1";
});

const pages = computed(() => [
  { key: "profile", to: "/profile", control: t("setup.doneProfileControl") },
  { key: "answers", to: "/profile/answers", control: t("setup.doneAnswersControl") },
  {
    key: "searches",
    to: `/tracks/${props.trackId}/look-for`,
    control: t("setup.doneSearchControl"),
  },
  { key: "studio", to: "/studio", control: t("setup.doneStudioControl") },
  {
    key: "improve",
    to: `/tracks/${props.trackId}/improve`,
    control: t("setup.doneImproveControl"),
  },
]);

function dismiss() {
  window.localStorage.setItem(storageKey.value, "1");
  visible.value = false;
  const query = { ...route.query };
  delete query.setup_done;
  void router.replace({ query });
}
</script>

<template>
  <section
    v-if="visible"
    class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-4 shadow-[var(--shadow-card)]"
    aria-labelledby="setup-done-title"
  >
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div class="flex flex-col gap-1">
        <h2 id="setup-done-title" class="text-lg font-bold text-ink-900">
          {{ t("setup.donePanelTitle") }}
        </h2>
        <p class="text-sm text-ink-600">{{ t("setup.donePanelBody") }}</p>
      </div>
      <FnButton tone="ghost" @click="dismiss">{{ t("setup.donePanelDismiss") }}</FnButton>
    </div>
    <ul class="flex flex-col gap-2">
      <li
        v-for="page in pages"
        :key="page.key"
        class="flex flex-wrap items-center justify-between gap-2 text-sm"
      >
        <NuxtLink :to="page.to" class="font-semibold text-brand-700 underline">
          {{ t(`setup.donePage.${page.key}`) }}
        </NuxtLink>
        <span class="text-ink-600">{{ page.control }}</span>
      </li>
    </ul>
  </section>
</template>
