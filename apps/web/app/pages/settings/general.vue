<script setup lang="ts">
import { renameWorkspaceApiV1WorkspacePatch, schemas } from "@kame/api-client";
import { FnButton, FnChip, FnField, FnInput, useToast } from "@kame/ui";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const ws = useWorkspaceStore();
const toast = useToast();
const apiError = useApiError();
const { form, err } = useZodForm(schemas.zWorkspaceUpdate, { name: ws.current?.name ?? "" });
const [name, nameAttrs] = form.defineField("name");
const formError = ref<string | null>(null);

watch(
  () => ws.current?.name,
  (n) => form.resetForm({ values: { name: n ?? "" } }),
);

const submit = form.handleSubmit(async (v) => {
  formError.value = null;
  try {
    await renameWorkspaceApiV1WorkspacePatch({ body: { name: v.name } });
    await ws.load();
    toast.push({ title: t("common.saved"), tone: "success" });
  } catch (e) {
    formError.value = apiError(e);
  }
});

// Unsaved-changes guard (vee-validate-forms skill).
onBeforeRouteLeave(() => (form.meta.value.dirty ? window.confirm(t("common.unsaved")) : true));
</script>

<template>
  <section class="flex max-w-md flex-col gap-4">
    <PageHeader :title="t('settings.general')" :lede="t('settings.generalLede')" />
    <p class="flex items-center gap-2 text-sm text-ink-600">
      {{ t("workspace.kind") }}
      <FnChip>{{
        ws.current?.kind === "personal" ? t("workspace.personal") : t("workspace.team")
      }}</FnChip>
    </p>
    <form class="flex flex-col gap-4" novalidate @submit.prevent="submit">
      <p v-if="formError" role="alert" class="text-sm text-oxblood-600">{{ formError }}</p>
      <FnField
        v-slot="{ id, describedby, invalid }"
        :label="t('workspace.name')"
        :error="err('name')"
      >
        <FnInput
          :id="id"
          v-model="name"
          v-bind="nameAttrs"
          :disabled="!ws.canManage"
          :describedby="describedby"
          :invalid="invalid"
        />
      </FnField>
      <div v-if="ws.canManage">
        <FnButton type="submit" tone="primary" :loading="form.isSubmitting.value">{{
          t("common.save")
        }}</FnButton>
      </div>
      <p v-else class="text-sm text-ink-600">{{ t("workspace.readOnly") }}</p>
    </form>
  </section>
</template>
