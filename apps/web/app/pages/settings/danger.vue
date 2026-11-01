<script setup lang="ts">
import {
  deleteWorkspaceApiV1WorkspaceDelete,
  leaveWorkspaceApiV1WorkspaceLeavePost,
  transferOwnershipApiV1WorkspaceTransferPost,
  queries,
} from "@kame/api-client";
import { FnButton, FnDialog, FnField, FnInput, FnSelect, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const ws = useWorkspaceStore();
const auth = useAuthStore();
const toast = useToast();
const apiError = useApiError();
const qc = useQueryClient();
const cfg = useRuntimeConfig().public;
const exportBusy = ref(false);

const isTeam = computed(() => ws.current?.kind === "team");
const isOwner = computed(() => ws.role === "owner");
const members = useQuery({
  ...queries.listMembersApiV1WorkspaceMembersGetOptions(),
  enabled: isOwner,
});
const heirs = computed(() =>
  (members.data.value ?? [])
    .filter((m) => m.user_id !== auth.user?.id)
    .map((m) => ({ value: m.user_id, label: m.name || m.email })),
);

type Action = "leave" | "transfer" | "delete" | null;
const action = ref<Action>(null);
const open = computed({
  get: () => action.value !== null,
  set: (v) => !v && (action.value = null),
});
const heir = ref("");
const confirmName = ref("");
const busy = ref(false);
const error = ref<string | null>(null);
watch(action, () => {
  heir.value = "";
  confirmName.value = "";
  error.value = null;
});

async function afterLeaving(message: string) {
  toast.push({ title: message, tone: "success" });
  qc.clear();
  await ws.load();
  await navigateTo("/");
}

async function exportWorkspace() {
  exportBusy.value = true;
  try {
    const token = await auth.ensureFresh();
    const base = String(cfg.apiBase || "").replace(/\/$/, "");
    const res = await fetch(`${base}/api/v1/workspace/export`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(ws.currentId ? { "X-Workspace-Id": ws.currentId } : {}),
      },
      credentials: "include",
    });
    if (!res.ok) throw new Error(String(res.status));
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kame-apply-${ws.currentId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.push({ title: t("danger.exported"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    exportBusy.value = false;
  }
}

async function run() {
  busy.value = true;
  error.value = null;
  try {
    if (action.value === "leave") {
      await leaveWorkspaceApiV1WorkspaceLeavePost();
      ws.select(null);
      await afterLeaving(t("danger.left"));
    } else if (action.value === "delete") {
      await deleteWorkspaceApiV1WorkspaceDelete();
      ws.select(null);
      await afterLeaving(t("danger.deleted"));
    } else if (action.value === "transfer") {
      await transferOwnershipApiV1WorkspaceTransferPost({ body: { user_id: heir.value } });
      await ws.load();
      action.value = null;
      toast.push({ title: t("danger.transferred"), tone: "success" });
      qc.invalidateQueries();
    }
  } catch (e) {
    error.value = apiError(e);
  } finally {
    busy.value = false;
  }
}
const canRun = computed(() =>
  action.value === "delete"
    ? confirmName.value === ws.current?.name
    : action.value === "transfer"
      ? !!heir.value
      : true,
);
</script>

<template>
  <section class="flex max-w-xl flex-col gap-6">
    <PageHeader :title="t('settings.danger')" />
    <div v-if="isOwner" class="flex flex-col gap-2 border-t border-rule pt-4">
      <h2 class="font-medium">{{ t("danger.exportTitle") }}</h2>
      <p class="text-sm text-ink-600">{{ t("danger.exportBody") }}</p>
      <div>
        <FnButton :loading="exportBusy" @click="exportWorkspace">{{ t("danger.export") }}</FnButton>
      </div>
    </div>
    <p v-if="!isTeam" class="text-sm text-ink-600">{{ t("danger.personal") }}</p>
    <template v-else>
      <div v-if="isOwner" class="flex flex-col gap-2 border-t border-rule pt-4">
        <h2 class="font-medium">{{ t("danger.transferTitle") }}</h2>
        <p class="text-sm text-ink-600">{{ t("danger.transferBody") }}</p>
        <div>
          <FnButton @click="action = 'transfer'">{{ t("danger.transfer") }}</FnButton>
        </div>
      </div>
      <div v-if="!isOwner" class="flex flex-col gap-2 border-t border-rule pt-4">
        <h2 class="font-medium">{{ t("danger.leaveTitle") }}</h2>
        <p class="text-sm text-ink-600">{{ t("danger.leaveBody") }}</p>
        <div>
          <FnButton tone="danger" @click="action = 'leave'">{{ t("danger.leave") }}</FnButton>
        </div>
      </div>
      <div v-if="isOwner" class="flex flex-col gap-2 border-t border-rule pt-4">
        <h2 class="font-medium text-oxblood-600">{{ t("danger.deleteTitle") }}</h2>
        <p class="text-sm text-ink-600">{{ t("danger.deleteBody") }}</p>
        <div>
          <FnButton tone="danger" @click="action = 'delete'">{{ t("danger.delete") }}</FnButton>
        </div>
      </div>
    </template>

    <FnDialog
      v-model:open="open"
      :title="t(`danger.${action ?? 'leave'}Title`)"
      :close-label="t('common.close')"
    >
      <p v-if="error" role="alert" class="text-sm text-oxblood-600">{{ error }}</p>
      <FnField v-if="action === 'transfer'" v-slot="{ id }" :label="t('danger.newOwner')">
        <FnSelect :id="id" v-model="heir" :options="heirs" :placeholder="t('danger.pick')" />
      </FnField>
      <FnField
        v-if="action === 'delete'"
        v-slot="{ id }"
        :label="t('danger.typeName', { name: ws.current?.name })"
      >
        <FnInput :id="id" v-model="confirmName" autocomplete="off" />
      </FnField>
      <div class="flex justify-end gap-2">
        <FnButton @click="action = null">{{ t("common.cancel") }}</FnButton>
        <FnButton
          :tone="action === 'transfer' ? 'primary' : 'danger'"
          :disabled="!canRun"
          :loading="busy"
          @click="run"
          >{{ t(`danger.${action ?? "leave"}`) }}</FnButton
        >
      </div>
    </FnDialog>
  </section>
</template>
