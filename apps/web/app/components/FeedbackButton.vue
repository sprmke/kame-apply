<script setup lang="ts">
import { FnButton, FnDialog, FnField, FnSelect, FnTextarea, useToast } from "@kame/ui";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const auth = useAuthStore();
const ws = useWorkspaceStore();
const toast = useToast();
const apiError = useApiError();
const cfg = useRuntimeConfig().public;
const route = useRoute();

const open = ref(false);
const busy = ref(false);
const error = ref<string | null>(null);
const category = ref("general");
const message = ref("");

const categories = computed(() =>
  (["bug", "friction", "idea", "general"] as const).map((c) => ({
    value: c,
    label: t(`feedback.${c}`),
  })),
);

async function send() {
  busy.value = true;
  error.value = null;
  try {
    const token = await auth.ensureFresh();
    const base = String(cfg.apiBase || "").replace(/\/$/, "");
    const res = await fetch(`${base}/api/v1/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(ws.currentId ? { "X-Workspace-Id": ws.currentId } : {}),
      },
      credentials: "include",
      body: JSON.stringify({
        category: category.value,
        message: message.value,
        page: route.fullPath,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.error?.message || String(res.status));
    }
    open.value = false;
    message.value = "";
    toast.push({ title: t("feedback.sent"), tone: "success" });
  } catch (e) {
    error.value = apiError(e);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div>
    <FnButton tone="quiet" size="sm" :aria-label="t('feedback.open')" @click="open = true">
      {{ t("feedback.open") }}
    </FnButton>
    <FnDialog v-model:open="open" :title="t('feedback.title')" :close-label="t('common.close')">
      <p v-if="error" role="alert" class="text-sm text-oxblood-600">{{ error }}</p>
      <p class="text-sm text-ink-600">{{ t("feedback.hint") }}</p>
      <FnField v-slot="{ id }" :label="t('feedback.category')">
        <FnSelect :id="id" v-model="category" :options="categories" />
      </FnField>
      <FnField v-slot="{ id }" :label="t('feedback.message')">
        <FnTextarea :id="id" v-model="message" :rows="4" />
      </FnField>
      <div class="flex justify-end gap-2">
        <FnButton @click="open = false">{{ t("common.cancel") }}</FnButton>
        <FnButton
          tone="primary"
          :disabled="message.trim().length < 10"
          :loading="busy"
          @click="send"
          >{{ t("feedback.send") }}</FnButton
        >
      </div>
    </FnDialog>
  </div>
</template>
