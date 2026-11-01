<script setup lang="ts">
import { useQueryClient } from "@tanstack/vue-query";
import { FnButton, FnMenu, type MenuItem } from "@kame/ui";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const ws = useWorkspaceStore();
const queryClient = useQueryClient();
const emit = defineEmits<{ create: [] }>();

function switchTo(id: string) {
  if (id === ws.currentId) return;
  ws.select(id);
  // Cached data belongs to the previous workspace.
  queryClient.clear();
  navigateTo("/");
}

const items = computed<MenuItem[]>(() => [
  ...ws.workspaces.map((w) => ({
    label: `${w.id === ws.currentId ? "✓ " : ""}${w.name}`,
    onSelect: () => switchTo(w.id),
  })),
  { type: "separator" as const },
  { label: t("workspace.create"), onSelect: () => emit("create") },
]);
</script>

<template>
  <FnMenu :items="items" align="start">
    <FnButton
      tone="ghost"
      class="max-w-56 min-w-0 justify-between"
      :aria-label="t('workspace.switch')"
    >
      <span class="truncate font-medium">{{ ws.current?.name ?? "…" }}</span>
      <NavIcon name="ph:caret-down" :size="14" />
    </FnButton>
  </FnMenu>
</template>
