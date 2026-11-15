<script setup lang="ts">
import {
  addCustomPackApiV1WorkspaceIndustriesCustomPost,
  addWorkspaceIndustryApiV1WorkspaceIndustriesPost,
  createWorkspaceApiV1WorkspacesPost,
  draftPackApiV1IndustriesDraftPost,
  listIndustriesApiV1IndustriesGet,
  listWorkspaceIndustriesApiV1WorkspaceIndustriesGet,
  removeWorkspaceIndustryApiV1WorkspaceIndustriesKeyDelete,
  type CustomPackDraftRead,
  type IndustrySummary,
} from "@kame/api-client";
import { FnButton, FnDialog, FnField, FnInput, FnSkeleton, useToast } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useExperience } from "~/composables/useExperience";
import { ok } from "~/lib/api";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const open = defineModel<boolean>("open", { default: false });
const ws = useWorkspaceStore();
const exp = useExperience();
const toast = useToast();
const apiError = useApiError();
const name = ref("");
const step = ref(0);
const selected = ref<string[]>([]);
const primary = ref<string | null>(null);
const busy = ref(false);
const error = ref<string | null>(null);
const elseText = ref("");
const elseBusy = ref(false);
const elseError = ref<string | null>(null);
const elseStatus = ref<string | null>(null);
const customPacks = ref<Record<string, CustomPackDraftRead>>({});
const customDescriptions = ref<Record<string, string>>({});

const industries = useQuery({
  queryKey: ["industries"],
  queryFn: async () => {
    const { data } = await listIndustriesApiV1IndustriesGet({ throwOnError: true });
    return (data?.items ?? []) as IndustrySummary[];
  },
  enabled: computed(() => open.value),
});
const customSummaries = computed<IndustrySummary[]>(() =>
  Object.values(customPacks.value).map(
    (draft) =>
      ({
        key: draft.key,
        label_key: draft.pack.label_key,
        label: draft.pack.display_name || draft.key,
        icon: draft.pack.icon,
        role_families: [],
        draft: true,
      }) as unknown as IndustrySummary & { draft: boolean },
  ),
);
const options = computed(() => [...customSummaries.value, ...(industries.data.value ?? [])]);

watch(open, (o) => {
  if (o) {
    name.value = "";
    step.value = 0;
    selected.value = [];
    primary.value = null;
    error.value = null;
    elseText.value = "";
    elseError.value = null;
    elseStatus.value = null;
    customPacks.value = {};
    customDescriptions.value = {};
  }
});

async function draftElse() {
  if (!elseText.value.trim()) {
    elseError.value = t("workspace.somethingElseRequired");
    return;
  }
  elseBusy.value = true;
  elseError.value = null;
  elseStatus.value = null;
  try {
    const { data } = await draftPackApiV1IndustriesDraftPost({
      body: { description: elseText.value.trim() },
      throwOnError: true,
    });
    if (!data) return;
    customPacks.value = { ...customPacks.value, [data.key]: data };
    customDescriptions.value = {
      ...customDescriptions.value,
      [data.key]: elseText.value.trim(),
    };
    if (selected.value.includes(data.key)) {
      elseStatus.value = t("workspace.draftReady");
    } else if (selected.value.length >= 2) {
      elseError.value = t("workspace.limitTwo");
    } else {
      selected.value = [...selected.value, data.key];
      if (!primary.value) primary.value = data.key;
      elseStatus.value = t("workspace.draftReady");
    }
  } catch (e) {
    elseError.value = apiError(e);
  } finally {
    elseBusy.value = false;
  }
}

function next() {
  if (!name.value.trim()) {
    error.value = t("validation.required");
    return;
  }
  error.value = null;
  step.value = 1;
}

async function submit() {
  if (!name.value.trim()) {
    error.value = t("validation.required");
    step.value = 0;
    return;
  }
  busy.value = true;
  error.value = null;
  try {
    const data = await ok(createWorkspaceApiV1WorkspacesPost({ body: { name: name.value } }));
    await ws.load();
    ws.select(data.id);
    const chosen = selected.value.filter((key) => key !== "general");
    const current = await listWorkspaceIndustriesApiV1WorkspaceIndustriesGet({
      throwOnError: true,
    });
    for (const row of current.data?.items ?? []) {
      if (row.key === "general" || chosen.includes(row.key)) continue;
      await removeWorkspaceIndustryApiV1WorkspaceIndustriesKeyDelete({
        path: { key: row.key },
        throwOnError: true,
      }).catch(() => null);
    }
    for (const [index, key] of chosen.entries()) {
      const custom = customPacks.value[key];
      if (custom) {
        await addCustomPackApiV1WorkspaceIndustriesCustomPost({
          body: {
            key,
            description: customDescriptions.value[key] ?? elseText.value.trim(),
            base_pack: custom.base_pack,
            is_primary: index === 0,
          },
          throwOnError: true,
        });
      } else {
        await addWorkspaceIndustryApiV1WorkspaceIndustriesPost({
          body: { key, is_primary: index === 0 },
          throwOnError: true,
        });
      }
    }
    await exp.refresh();
    open.value = false;
    toast.push({ title: t("workspace.created"), tone: "success" });
    await navigateTo("/");
  } catch (e) {
    error.value = apiError(e);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <FnDialog
    v-model:open="open"
    :title="t('workspace.create')"
    size="lg"
    :close-label="t('common.close')"
  >
    <form class="flex flex-col gap-4" novalidate @submit.prevent="step === 0 ? next() : submit()">
      <p class="text-xs font-semibold tracking-wide text-ink-600 uppercase">
        {{ t("workspace.step", { n: step + 1 }) }}
      </p>

      <template v-if="step === 0">
        <FnField v-slot="{ id, describedby, invalid }" :label="t('workspace.name')" :error="error">
          <FnInput
            :id="id"
            v-model="name"
            :describedby="describedby"
            :invalid="invalid"
            autocomplete="off"
          />
        </FnField>
        <div class="flex justify-end gap-2">
          <FnButton @click="open = false">{{ t("common.cancel") }}</FnButton>
          <FnButton type="submit" tone="primary">{{ t("workspace.next") }}</FnButton>
        </div>
      </template>

      <template v-else>
        <div class="flex flex-col gap-2">
          <p class="text-sm font-semibold text-ink-900">{{ t("workspace.pickField") }}</p>
          <div v-if="industries.isPending.value" class="grid gap-2 sm:grid-cols-2">
            <FnSkeleton v-for="n in 4" :key="n" class="h-16 w-full" />
          </div>
          <IndustryPicker
            v-else
            v-model:selected="selected"
            v-model:primary="primary"
            :industries="options"
            :disabled="busy"
          />
          <p class="text-xs text-ink-600">{{ t("workspace.pickFieldHint") }}</p>
          <p v-if="selected.length >= 2" class="text-xs text-ink-600">
            {{ t("workspace.limitTwo") }}
          </p>
          <FnField :label="t('workspace.somethingElse')" :error="elseError">
            <template #default="{ id, describedby, invalid }">
              <FnInput
                :id="id"
                v-model="elseText"
                :aria-describedby="describedby"
                :aria-invalid="invalid"
                :placeholder="t('workspace.somethingElsePlaceholder')"
                maxlength="600"
                @keydown.enter.prevent="draftElse"
              />
              <FnButton
                class="self-start"
                size="sm"
                tone="quiet"
                :loading="elseBusy"
                @click="draftElse"
                >{{ t("workspace.draftField") }}</FnButton
              >
            </template>
          </FnField>
          <p v-if="elseStatus" role="status" class="text-xs text-ink-600">{{ elseStatus }}</p>
        </div>
        <p v-if="error" role="alert" class="text-sm text-oxblood-600">{{ error }}</p>
        <div class="flex flex-wrap justify-between gap-2">
          <FnButton :disabled="busy" @click="step = 0">{{ t("workspace.back") }}</FnButton>
          <FnButton type="submit" tone="primary" :loading="busy">{{ t("common.create") }}</FnButton>
        </div>
      </template>
    </form>
  </FnDialog>
</template>
