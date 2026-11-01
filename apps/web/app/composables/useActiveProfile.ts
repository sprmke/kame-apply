import {
  createProfileApiV1ProfilesPost,
  getProfileApiV1ProfilesProfileIdGet,
  listProfilesApiV1ProfilesGet,
  type ProfileFull,
  type ProfileRead,
} from "@kame/api-client";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const STORAGE_KEY = "kame.activeProfile";

function storageKey(wsId: string | null | undefined) {
  return wsId ? `${STORAGE_KEY}:${wsId}` : STORAGE_KEY;
}

/** Active career profile for the workspace (selected, default, or first). */
export function useActiveProfile() {
  const ws = useWorkspaceStore();
  const qc = useQueryClient();
  const enabled = computed(() => Boolean(ws.currentId));
  const selectedId = ref<string | null>(null);

  watch(
    () => ws.currentId,
    (id) => {
      if (!import.meta.client || !id) {
        selectedId.value = null;
        return;
      }
      selectedId.value = localStorage.getItem(storageKey(id));
    },
    { immediate: true },
  );

  const list = useQuery({
    queryKey: computed(() => ["profiles", ws.currentId]),
    queryFn: async () => {
      const { data } = await listProfilesApiV1ProfilesGet({ throwOnError: true });
      return data ?? [];
    },
    enabled,
  });

  const profileMeta = computed<ProfileRead | null>(() => {
    const rows = list.data.value ?? [];
    if (!rows.length) return null;
    if (selectedId.value) {
      const hit = rows.find((p) => p.id === selectedId.value);
      if (hit) return hit;
    }
    return rows.find((p) => p.is_default) ?? rows[0] ?? null;
  });

  const profileId = computed(() => profileMeta.value?.id ?? null);

  const full = useQuery({
    queryKey: computed(() => ["profile", ws.currentId, profileId.value]),
    queryFn: async () => {
      const id = profileId.value;
      if (!id) throw new Error("no profile");
      const { data } = await getProfileApiV1ProfilesProfileIdGet({
        path: { profile_id: id },
        throwOnError: true,
      });
      return data as ProfileFull;
    },
    enabled: computed(() => Boolean(profileId.value)),
  });

  function selectProfile(id: string) {
    selectedId.value = id;
    if (import.meta.client && ws.currentId) {
      localStorage.setItem(storageKey(ws.currentId), id);
    }
  }

  async function ensureProfile(displayName = "My profile"): Promise<string> {
    if (profileId.value) return profileId.value;
    const { data } = await createProfileApiV1ProfilesPost({
      body: { display_name: displayName },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["profiles", ws.currentId] });
    if (data?.id) selectProfile(data.id);
    return data!.id;
  }

  async function refresh() {
    await qc.invalidateQueries({ queryKey: ["profiles", ws.currentId] });
    if (profileId.value) {
      await qc.invalidateQueries({ queryKey: ["profile", ws.currentId, profileId.value] });
    }
  }

  return {
    list,
    full,
    profileMeta,
    profileId,
    profile: computed(() => full.data.value ?? null),
    selectProfile,
    ensureProfile,
    refresh,
    loading: computed(
      () => list.isPending.value || (Boolean(profileId.value) && full.isPending.value),
    ),
    error: computed(() => list.error.value || full.error.value),
  };
}
