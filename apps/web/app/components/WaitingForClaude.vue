<script setup lang="ts">
import { FnButton, useToast } from "@kame/ui";

defineProps<{ waiting?: number }>();
const { t } = useI18n();
const toast = useToast();
const cmd = 'claude -p "/kame:work"';

async function copy() {
  await navigator.clipboard.writeText(cmd);
  toast.push({ title: t("common.copied"), tone: "neutral" });
}
</script>

<template>
  <div
    class="flex flex-wrap items-center gap-2 rounded-sm border border-rule bg-paper-2 px-3 py-2 text-sm text-ink-800"
  >
    <span>{{ t("integrations.waitingClaude") }}</span>
    <code class="font-mono text-xs">{{ cmd }}</code>
    <FnButton size="sm" variant="ghost" @click="copy">{{ t("common.copy") }}</FnButton>
  </div>
</template>
