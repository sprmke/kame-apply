import { client } from "@kame/api-client";
import { useQuery } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

export function useAgentInboxStatus() {
  const ws = useWorkspaceStore();
  const q = useQuery({
    queryKey: computed(() => ["agent-bridge-inbox", ws.currentId]),
    queryFn: async () => {
      const { data } = await client.get({
        url: "/api/v1/agent-bridge/inbox",
        throwOnError: true,
      });
      return data as { waiting: number; leased: number };
    },
    enabled: computed(() => Boolean(ws.currentId)),
    refetchInterval: 30_000,
  });
  const waiting = computed(() => q.data.value?.waiting ?? 0);
  return { waiting, query: q };
}
