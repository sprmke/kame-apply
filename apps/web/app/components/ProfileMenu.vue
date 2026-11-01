<script setup lang="ts">
import { useQueryClient } from "@tanstack/vue-query";
import { FnButton, FnMenu, type MenuItem } from "@kame/ui";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const auth = useAuthStore();
const workspace = useWorkspaceStore();
const { choice, set } = useTheme();
const queryClient = useQueryClient();

const initial = computed(() =>
  (auth.user?.name || auth.user?.email || "?").slice(0, 1).toUpperCase(),
);

async function signOut() {
  await auth.logout();
  workspace.reset();
  queryClient.clear();
  await navigateTo("/login");
}

const items = computed<MenuItem[]>(() => [
  { label: auth.user?.email ?? "", disabled: true, onSelect: () => {} },
  { type: "separator" },
  { label: t("career.title"), onSelect: () => navigateTo("/profile") },
  { label: t("career.tabs.answers"), onSelect: () => navigateTo("/profile/answers") },
  { label: t("career.tabs.voice"), onSelect: () => navigateTo("/profile/voice") },
  { label: t("career.tabs.documents"), onSelect: () => navigateTo("/profile/documents") },
  { type: "separator" },
  { label: t("settings.profile"), onSelect: () => navigateTo("/settings/profile") },
  {
    label: `${t("theme.label")}: ${t(`theme.${choice.value}`)}`,
    onSelect: () =>
      set(choice.value === "light" ? "dark" : choice.value === "dark" ? "system" : "light"),
  },
  { type: "separator" },
  { label: t("auth.signOut"), onSelect: signOut },
]);
</script>

<template>
  <FnMenu :items="items">
    <FnButton
      tone="ghost"
      class="!min-h-11 !w-11 !rounded-full !px-0"
      :aria-label="t('shell.profileMenu')"
    >
      <span
        class="grid size-8 place-items-center rounded-full bg-paper-2 text-sm font-semibold text-ink-900"
        >{{ initial }}</span
      >
    </FnButton>
  </FnMenu>
</template>
