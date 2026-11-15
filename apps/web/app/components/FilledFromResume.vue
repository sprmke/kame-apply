<script setup lang="ts">
import { FnButton } from "@kame/ui";
import { useSetupProvenance, type ProvenancePage } from "~/composables/useSetupProvenance";

const props = defineProps<{
  page: ProvenancePage;
  /** The page's own AI control, for example "Suggest settings". */
  control: string;
}>();
const { t } = useI18n();
const { hasPage, seen, recent, markSeen } = useSetupProvenance();

const show = computed(() => hasPage(props.page) && recent() && !seen(props.page));

async function dismiss() {
  await markSeen(props.page);
}
</script>

<template>
  <div
    v-if="show"
    class="flex flex-wrap items-center gap-2 rounded-lg border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-ink-600"
  >
    <span class="min-w-0 flex-1">{{ t("setup.filledFrom", { control }) }}</span>
    <FnButton tone="ghost" @click="dismiss">{{ t("setup.gotIt") }}</FnButton>
  </div>
</template>
