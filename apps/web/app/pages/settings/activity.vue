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
const nextBeforeId = ref<string | null>(null);
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
          before_id: more ? (nextBeforeId.value ?? undefined) : undefined,
          limit: 25,
        },
      }),
    );
    items.value = more ? [...items.value, ...data.items] : data.items;
    nextBefore.value = data.next_before ?? null;
    nextBeforeId.value = data.next_before_id ?? null;
  } catch (e) {
    error.value = apiError(e);
  } finally {
    loading.value = false;
  }
}
watch(filter, () => load(), { immediate: true });

const scopeLabel: Record<string, string> = {
  ai: "AI",
  workspace: "Workspace",
  member: "Member",
  invitation: "Invitation",
  profile: "Profile",
  job: "Job",
  track: "Search",
  run: "Search run",
  application: "Application",
  answer: "Answer",
  resume: "Resume",
  source: "Source",
  settings: "Settings",
};

function humanize(part: string): string {
  const words = scopeLabel[part] ?? part.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function eventLabel(action: string): string {
  return action
    .split(".")
    .map((part) => humanize(part))
    .join(" · ");
}

const columns = computed(() => [
  { key: "when", label: t("activity.when") },
  { key: "action", label: t("activity.action") },
  { key: "target", label: t("activity.target") },
]);
const rows = computed(() =>
  items.value.map((i) => ({
    id: i.id,
    when: fmt.dateTime(i.created_at),
    action: eventLabel(i.action),
    target: i.target_type ? humanize(i.target_type) : "—",
  })),
);
</script>

<template>
  <section class="flex flex-col gap-4">
    <PageHeader :title="t('settings.activity')" />
    <div class="max-w-56"><FnSelect v-model="filter" :options="options" /></div>
    <p v-if="error" role="alert" class="text-sm text-oxblood-600">{{ error }}</p>
    <FnSkeleton v-if="loading && !items.length" :lines="5" />
    <template v-else>
      <ul class="flex flex-col divide-y divide-rule overflow-hidden rounded-xl border border-rule bg-paper-1 sm:hidden">
        <li v-for="r in rows" :key="r.id" class="flex flex-col gap-0.5 px-4 py-3">
          <p class="text-sm font-medium text-ink-900">{{ r.action }}</p>
          <p class="text-xs text-ink-600">{{ r.target }} · {{ r.when }}</p>
        </li>
        <li v-if="!rows.length" class="px-4 py-8 text-center text-sm text-ink-600">
          {{ t("activity.empty") }}
        </li>
      </ul>
      <FnTable
        class="max-sm:hidden"
        :columns="columns"
        :rows="rows"
        row-key="id"
        density="compact"
        :caption="t('settings.activity')"
        :empty="t('activity.empty')"
      />
    </template>
    <div v-if="nextBefore">
      <FnButton :loading="loading" @click="load(true)">{{ t("activity.more") }}</FnButton>
    </div>
  </section>
</template>
