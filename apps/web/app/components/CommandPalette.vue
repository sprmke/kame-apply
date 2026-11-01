<script setup lang="ts">
import { useQueryClient } from "@tanstack/vue-query";
import { FnCommandBar, type CommandItem } from "@kame/ui";
import { NAV } from "~/lib/nav";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const open = defineModel<boolean>("open", { default: false });
const emit = defineEmits<{ createWorkspace: [] }>();
const auth = useAuthStore();
const ws = useWorkspaceStore();
const { set } = useTheme();
const queryClient = useQueryClient();

const items = computed<CommandItem[]>(() => [
  ...NAV.map((n) => ({ id: `go:${n.to}`, label: t(`nav.${n.key}`), group: t("command.go") })),
  { id: "go:/settings/members", label: t("settings.members"), group: t("command.go") },
  { id: "go:/settings/ai", label: t("settings.ai"), group: t("command.go") },
  { id: "go:/settings/sessions", label: t("settings.sessions"), group: t("command.go") },
  { id: "act:workspace", label: t("workspace.create"), group: t("command.actions") },
  {
    id: "act:theme-light",
    label: `${t("theme.label")}: ${t("theme.light")}`,
    group: t("command.actions"),
  },
  {
    id: "act:theme-dark",
    label: `${t("theme.label")}: ${t("theme.dark")}`,
    group: t("command.actions"),
  },
  {
    id: "act:theme-system",
    label: `${t("theme.label")}: ${t("theme.system")}`,
    group: t("command.actions"),
  },
  { id: "act:signout", label: t("auth.signOut"), group: t("command.actions") },
]);

async function run(id: string) {
  if (id.startsWith("go:")) return navigateTo(id.slice(3));
  if (id === "act:workspace") return emit("createWorkspace");
  if (id.startsWith("act:theme-")) return set(id.slice(10) as "light" | "dark" | "system");
  if (id === "act:signout") {
    await auth.logout();
    ws.reset();
    queryClient.clear();
    await navigateTo("/login");
  }
}

// ⌘K / Ctrl+K from anywhere in the shell.
onMounted(() => {
  const onKey = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      open.value = !open.value;
    }
  };
  window.addEventListener("keydown", onKey);
  onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
});
</script>

<template>
  <FnCommandBar
    v-model:open="open"
    :items="items"
    :title="t('command.title')"
    :placeholder="t('command.placeholder')"
    :empty="t('command.empty')"
    @select="run"
  />
</template>
