import {
  getProvenanceApiV1OnboardingSetupsProvenanceGet,
  markSeenApiV1OnboardingSetupsDraftIdSeenPost,
} from "@kame/api-client";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { useWorkspaceStore } from "~/stores/workspace";

export type ProvenancePage = "profile" | "answers" | "writing" | "searches" | "studio" | "account";

const PAGE_KEYS: Record<ProvenancePage, string> = {
  profile: "profile",
  answers: "answers",
  writing: "voice",
  searches: "searches",
  studio: "resumes",
  account: "profile",
};

/** Latest applied setup for the active profile, for the "Filled from your resume" lines. */
export function useSetupProvenance() {
  const ws = useWorkspaceStore();
  const qc = useQueryClient();
  const { profileId } = useActiveProfile();

  const query = useQuery({
    queryKey: computed(() => ["setup-provenance", ws.currentId, profileId.value]),
    queryFn: async () => {
      const { data } = await getProvenanceApiV1OnboardingSetupsProvenanceGet({
        query: { profile_id: profileId.value! },
        throwOnError: true,
      });
      return data;
    },
    enabled: computed(() => Boolean(ws.currentId && profileId.value)),
    staleTime: 60_000,
  });

  function hasPage(page: ProvenancePage): boolean {
    const row = query.data.value;
    if (!row) return false;
    const key = PAGE_KEYS[page];
    const created = row.created?.[key]?.length ?? 0;
    const updated = row.updated?.[key]?.length ?? 0;
    return created + updated > 0;
  }

  function seen(page: ProvenancePage): boolean {
    return Boolean(query.data.value?.seen_pages?.includes(page));
  }

  function recent(): boolean {
    const row = query.data.value;
    if (!row) return false;
    const applied = new Date(row.applied_at).getTime();
    return Number.isFinite(applied) && Date.now() - applied <= 14 * 24 * 60 * 60 * 1000;
  }

  function createdIds(key: string): Set<string> {
    return new Set(query.data.value?.created?.[key] ?? []);
  }

  async function markSeen(page: ProvenancePage) {
    const row = query.data.value;
    if (!row) return;
    try {
      await markSeenApiV1OnboardingSetupsDraftIdSeenPost({
        path: { draft_id: row.draft_id },
        body: { page },
        throwOnError: true,
      });
    } finally {
      await qc.invalidateQueries({ queryKey: ["setup-provenance"] });
    }
  }

  return { query, hasPage, seen, recent, createdIds, markSeen };
}
