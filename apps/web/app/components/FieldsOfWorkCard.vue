<script setup lang="ts">
import {
  addWorkspaceIndustryApiV1WorkspaceIndustriesPost,
  listIndustriesApiV1IndustriesGet,
  removeWorkspaceIndustryApiV1WorkspaceIndustriesKeyDelete,
  setPrimaryIndustryApiV1WorkspaceIndustriesPrimaryPut,
  type IndustrySummary,
  type WorkspaceIndustryRead,
} from "@kame/api-client";
import { FnButton, useToast } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useExperience } from "~/composables/useExperience";
import { useWorkspaceStore } from "~/stores/workspace";

const { t, te } = useI18n();
const ws = useWorkspaceStore();
const exp = useExperience();
const toast = useToast();
const apiError = useApiError();
const busy = ref(false);
const pendingPrimary = ref<string | null>(null);

const industries = useQuery({
  queryKey: ["industries"],
  queryFn: async () => {
    const { data } = await listIndustriesApiV1IndustriesGet({ throwOnError: true });
    return (data?.items ?? []) as IndustrySummary[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const enabled = computed<WorkspaceIndustryRead[]>(() => exp.enabled.value);
const enabledKeys = computed(() => new Set(enabled.value.map((item) => item.key)));
const available = computed(() =>
  (industries.data.value ?? []).filter(
    (item) => !enabledKeys.value.has(item.key) && item.key !== "general",
  ),
);

function label(item: { key: string; label_key: string; label?: string | null }): string {
  if (item.label) return item.label;
  return te(item.label_key) ? t(item.label_key) : item.key;
}

function icon(item: WorkspaceIndustryRead): string {
  return item.icon || "ph:briefcase";
}

function preview(key: string): string {
  const next = exp.manifestFor(key);
  const current = exp.manifestFor(exp.primary.value);
  if (!next || !current) return "";
  const bits: string[] = [];
  const nextName = exp.packLabel(key);
  bits.push(t("workspace.primaryPreview", { name: nextName }));
  if (next.states.shifts !== current.states.shifts) {
    bits.push(
      next.states.shifts === "visible"
        ? t("workspace.previewShifts")
        : t("workspace.previewShiftsHidden"),
    );
  }
  if (next.states.remote_eligibility !== current.states.remote_eligibility) {
    bits.push(
      next.states.remote_eligibility === "hidden"
        ? t("workspace.previewRemoteHidden")
        : t("workspace.previewRemote"),
    );
  }
  if (next.features.github_links !== current.features.github_links) {
    bits.push(
      next.features.github_links === false
        ? t("workspace.previewGithub")
        : t("workspace.previewGithubOn"),
    );
  }
  const currentSections = current.profile_sections;
  const moved = next.profile_sections.findIndex(
    (section, index) => currentSections.indexOf(section) !== index,
  );
  if (moved >= 0) bits.push(t("workspace.previewProfile"));
  return bits.join(" ");
}

async function afterChange(message: string) {
  await exp.refresh();
  toast.push({ title: message, tone: "success" });
}

async function add(key: string) {
  busy.value = true;
  try {
    await addWorkspaceIndustryApiV1WorkspaceIndustriesPost({
      body: { key, is_primary: false },
      throwOnError: true,
    });
    await afterChange(t("workspace.fieldAdded"));
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}

async function remove(key: string) {
  const item = enabled.value.find((row) => row.key === key);
  if (!item) return;
  if (!window.confirm(t("workspace.removeFieldConfirm", { name: label(item) }))) return;
  busy.value = true;
  try {
    await removeWorkspaceIndustryApiV1WorkspaceIndustriesKeyDelete({
      path: { key },
      throwOnError: true,
    });
    if (pendingPrimary.value === key) pendingPrimary.value = null;
    await afterChange(t("workspace.fieldRemoved"));
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}

async function makePrimary(key: string) {
  busy.value = true;
  try {
    await setPrimaryIndustryApiV1WorkspaceIndustriesPrimaryPut({
      body: { key },
      throwOnError: true,
    });
    pendingPrimary.value = null;
    await afterChange(t("workspace.primaryChanged"));
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="flex max-w-xl flex-col gap-3 border-t border-rule pt-5">
    <div>
      <h2 class="text-sm font-semibold text-ink-900">{{ t("workspace.fieldsOfWork") }}</h2>
      <p class="mt-1 text-xs text-ink-600">{{ t("workspace.fieldsOfWorkHint") }}</p>
    </div>

    <ul class="divide-y divide-rule border-y border-rule">
      <li v-for="item in enabled" :key="item.key" class="flex min-h-14 items-center gap-3 py-2.5">
        <span class="grid size-9 shrink-0 place-items-center rounded-lg bg-paper-2 text-ink-600">
          <Icon :name="icon(item)" :size="18" aria-hidden="true" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="flex items-center gap-2">
            <span class="truncate text-sm font-medium text-ink-900">{{ label(item) }}</span>
            <span
              v-if="item.is_primary"
              class="rounded-full bg-brand-100 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-brand-700 uppercase"
              >{{ t("workspace.primaryField") }}</span
            >
          </span>
          <span v-if="!item.is_primary && item.key !== 'general'" class="text-xs text-ink-600">{{
            t("workspace.notPrimary")
          }}</span>
          <span v-else-if="item.key === 'general'" class="text-xs text-ink-600">{{
            t("workspace.fallback")
          }}</span>
        </span>
        <div v-if="ws.canManage && item.key !== 'general'" class="flex items-center gap-1">
          <FnButton
            v-if="!item.is_primary"
            size="sm"
            tone="quiet"
            :disabled="busy"
            @click="pendingPrimary = pendingPrimary === item.key ? null : item.key"
            >{{ t("workspace.makePrimary") }}</FnButton
          >
          <FnButton size="sm" tone="ghost" :disabled="busy" @click="remove(item.key)">{{
            t("common.delete")
          }}</FnButton>
        </div>
      </li>
    </ul>

    <div
      v-if="pendingPrimary"
      class="flex flex-col gap-2 rounded-lg border border-brand-200 bg-brand-50 px-3 py-2.5 text-sm text-ink-900"
      role="status"
    >
      <p>{{ preview(pendingPrimary) }}</p>
      <div class="flex flex-wrap gap-2">
        <FnButton size="sm" tone="primary" :loading="busy" @click="makePrimary(pendingPrimary)">{{
          t("workspace.confirm")
        }}</FnButton>
        <FnButton size="sm" tone="quiet" @click="pendingPrimary = null">{{
          t("common.cancel")
        }}</FnButton>
      </div>
    </div>

    <div v-if="ws.canManage && available.length" class="flex flex-wrap items-center gap-2">
      <FnButton
        v-for="item in available"
        :key="item.key"
        size="sm"
        tone="quiet"
        :disabled="busy"
        @click="add(item.key)"
      >
        <Icon :name="item.icon" :size="16" aria-hidden="true" />
        {{ label(item) }}
      </FnButton>
    </div>
    <p v-if="!ws.canManage" class="text-sm text-ink-600">{{ t("workspace.fieldsReadOnly") }}</p>
  </section>
</template>
