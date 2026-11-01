import { listWorkspacesApiV1WorkspacesGet, type WorkspaceRead } from "@kame/api-client";
import { defineStore } from "pinia";
import { computed, ref } from "vue";

const KEY = "kame.workspace";

function readStored(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export const useWorkspaceStore = defineStore("workspace", () => {
  const workspaces = ref<WorkspaceRead[]>([]);
  const currentId = ref<string | null>(null);
  const loaded = ref(false);

  const current = computed(() => workspaces.value.find((w) => w.id === currentId.value) ?? null);
  const role = computed(() => current.value?.role ?? null);
  const canManage = computed(() => role.value === "owner" || role.value === "admin");

  async function load() {
    const { data } = await listWorkspacesApiV1WorkspacesGet({ throwOnError: true });
    workspaces.value = data;
    const stored = readStored();
    const pick = data.find((w) => w.id === (currentId.value ?? stored)) ?? data[0] ?? null;
    select(pick?.id ?? null);
    loaded.value = true;
  }

  function select(id: string | null) {
    currentId.value = id;
    try {
      if (id) localStorage.setItem(KEY, id);
      else localStorage.removeItem(KEY);
    } catch {
      // storage can be unavailable (private mode); the choice then lasts for this tab only
    }
  }

  function reset() {
    workspaces.value = [];
    currentId.value = null;
    loaded.value = false;
  }

  return { workspaces, currentId, current, role, canManage, loaded, load, select, reset };
});
