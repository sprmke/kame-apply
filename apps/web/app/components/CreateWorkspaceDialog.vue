<script setup lang="ts">
import { ok } from "~/lib/api";
import { createWorkspaceApiV1WorkspacesPost } from "@kame/api-client";
import { FnButton, FnDialog, FnField, FnInput, useToast } from "@kame/ui";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const open = defineModel<boolean>("open", { default: false });
const ws = useWorkspaceStore();
const toast = useToast();
const apiError = useApiError();
const name = ref("");
const busy = ref(false);
const error = ref<string | null>(null);

watch(open, (o) => {
  if (o) {
    name.value = "";
    error.value = null;
  }
});

async function submit() {
  if (!name.value.trim()) {
    error.value = t("validation.required");
    return;
  }
  busy.value = true;
  error.value = null;
  try {
    const data = await ok(createWorkspaceApiV1WorkspacesPost({ body: { name: name.value } }));
    await ws.load();
    ws.select(data.id);
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
  <FnDialog v-model:open="open" :title="t('workspace.create')" :close-label="t('common.close')">
    <form class="flex flex-col gap-4" novalidate @submit.prevent="submit">
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
        <FnButton type="submit" tone="primary" :loading="busy">{{ t("common.create") }}</FnButton>
      </div>
    </form>
  </FnDialog>
</template>
