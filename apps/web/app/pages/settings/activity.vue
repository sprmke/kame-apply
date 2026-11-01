<script setup lang="ts">
import { ok } from "~/lib/api";
import { listActivityApiV1ActivityGet, type ActivityRead } from "@kame/api-client";
import { FnButton, FnSelect, FnSkeleton, FnTable } from "@kame/ui";

const { t } = useI18n();
const apiError = useApiError();
const fmt = useFormat();
const filter = ref("all");
const items = ref<ActivityRead[]>([]);
const nextBefore = ref<string | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

const options = computed(() => [
  { value: "all", label: t("activity.all") },
  { value: "workspace.", label: t("activity.workspace") },
  { value: "member.", label: t("activity.members") },
  { value: "invitation.", label: t("activity.invitations") },
  { value: "ai_", label: t("activity.ai") },
]);

async function load(more = false) {
  loading.value = true;
  error.value = null;
  try {
    const data = await ok(
      listActivityApiV1ActivityGet({
        query: {
          action: filter.value === "all" ? undefined : filter.value,
          before: more ? (nextBefore.value ?? undefined) : undefined,
          limit: 25,
        },
      }),
    );
    items.value = more ? [...items.value, ...data.items] : data.items;
    nextBefore.value = data.next_before ?? null;
  } catch (e) {
    error.value = apiError(e);
  } finally {
    loading.value = false;
  }
}
watch(filter, () => load(), { immediate: true });

const columns = computed(() => [
  { key: "when", label: t("activity.when"), mono: true },
  { key: "action", label: t("activity.action"), mono: true },
  { key: "target", label: t("activity.target"), mono: true },
]);
const rows = computed(() =>
  items.value.map((i) => ({
    id: i.id,
    when: fmt.dateTime(i.created_at),
    action: i.action,
    target: i.target_type ? `${i.target_type}` : "—",
  })),
);
</script>

<template>
  <section class="flex flex-col gap-4">
    <PageHeader :title="t('settings.activity')" />
    <div class="max-w-56"><FnSelect v-model="filter" :options="options" /></div>
    <p v-if="error" role="alert" class="text-sm text-oxblood-600">{{ error }}</p>
    <FnSkeleton v-if="loading && !items.length" :lines="5" />
    <FnTable
      v-else
      :columns="columns"
      :rows="rows"
      row-key="id"
      density="compact"
      :caption="t('settings.activity')"
      :empty="t('activity.empty')"
    />
    <div v-if="nextBefore">
      <FnButton :loading="loading" @click="load(true)">{{ t("activity.more") }}</FnButton>
    </div>
  </section>
</template>
