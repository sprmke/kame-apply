<script setup lang="ts">
import { client } from "@kame/api-client";
import { FnButton, FnCheckbox, FnSelect, FnSkeleton, useToast } from "@kame/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

definePageMeta({ layout: "default" });

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const { public: cfg } = useRuntimeConfig();

const mcpUrl = computed(() => `${String(cfg.apiBase).replace(/\/$/, "")}/mcp`);
const setupCmd = computed(() => `claude mcp add --transport http kame ${mcpUrl.value}`);
const pluginCmd =
  "/plugin marketplace add kame-apply/claude-plugins && /plugin install kame-apply@kame-apply";
const workCmd = 'claude -p "/kame:work"';
const connecting = ref(false);
const ack = ref<Record<string, boolean>>({});
const newRunnerToken = ref<string | null>(null);
const runnerMode = ref<"cloud" | "local">("local");

type TokenRow = {
  id: string;
  client_id: string;
  client_name: string;
  token_kind: string;
  scopes: string[];
  last_used_at: string | null;
};
type RoutingRow = { feature: string; route: string; fallback: boolean };
type Inbox = {
  waiting: number;
  leased: number;
  last_picked_up_at: string | null;
  command: string;
};
type PlatformPolicy = {
  platform: string;
  autofill_enabled: boolean;
  terms_acknowledged_at: string | null;
};
type RunnerTokenRow = {
  id: string;
  label: string;
  mode: string;
  last_seen_at: string | null;
  created_at: string;
};

const tokens = useQuery({
  queryKey: computed(() => ["agent-bridge-tokens", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/agent-bridge/tokens",
      throwOnError: true,
    });
    return (data ?? []) as TokenRow[];
  },
  enabled: computed(() => Boolean(ws.currentId) && ws.canManage),
});

const routing = useQuery({
  queryKey: computed(() => ["agent-bridge-routing", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/agent-bridge/routing",
      throwOnError: true,
    });
    return (data ?? []) as RoutingRow[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const inbox = useQuery({
  queryKey: computed(() => ["agent-bridge-inbox", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/agent-bridge/inbox",
      throwOnError: true,
    });
    return data as Inbox;
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const revoke = useMutation({
  mutationFn: async (id: string) => {
    await client.post({
      url: `/api/v1/agent-bridge/tokens/${id}/revoke`,
      throwOnError: true,
    });
  },
  onSuccess: async () => {
    await qc.invalidateQueries({ queryKey: ["agent-bridge-tokens", ws.currentId] });
    toast.push({ title: t("common.saved"), tone: "neutral" });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const runnerTokens = useQuery({
  queryKey: computed(() => ["runner-tokens", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/runs/tokens",
      throwOnError: true,
    });
    return (data ?? []) as RunnerTokenRow[];
  },
  enabled: computed(() => Boolean(ws.currentId) && ws.canManage),
});

const createRunner = useMutation({
  mutationFn: async () => {
    const { data } = await client.post({
      url: "/api/v1/runs/tokens",
      body: { label: runnerMode.value, mode: runnerMode.value },
      throwOnError: true,
    });
    return data as { token: string };
  },
  onSuccess: async (data) => {
    newRunnerToken.value = data.token;
    await qc.invalidateQueries({ queryKey: ["runner-tokens", ws.currentId] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const revokeRunner = useMutation({
  mutationFn: async (id: string) => {
    await client.post({
      url: `/api/v1/runs/tokens/${id}/revoke`,
      throwOnError: true,
    });
  },
  onSuccess: async () => {
    await qc.invalidateQueries({ queryKey: ["runner-tokens", ws.currentId] });
    toast.push({ title: t("common.saved"), tone: "neutral" });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const saveRoute = useMutation({
  mutationFn: async (row: RoutingRow) => {
    await client.put({
      url: "/api/v1/agent-bridge/routing",
      body: row,
      throwOnError: true,
    });
  },
  onSuccess: async () => {
    await qc.invalidateQueries({ queryKey: ["agent-bridge-routing", ws.currentId] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

async function copy(text: string) {
  await navigator.clipboard.writeText(text);
  toast.push({ title: t("common.copied"), tone: "neutral" });
}

const routeOptions = [
  { value: "server", label: "Server model" },
  { value: "agent_inbox", label: "My Claude" },
];

const policies = useQuery({
  queryKey: computed(() => ["extension-policies", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/extension/platform-policies",
      throwOnError: true,
    });
    return (data ?? []) as PlatformPolicy[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const restricted = computed(() =>
  (policies.data.value ?? []).filter((p) =>
    ["linkedin", "indeed", "jobstreet", "seek"].includes(p.platform),
  ),
);

const savePolicy = useMutation({
  mutationFn: async (body: {
    platform: string;
    autofill_enabled: boolean;
    acknowledge_terms: boolean;
  }) => {
    await client.put({
      url: "/api/v1/extension/platform-policies",
      body,
      throwOnError: true,
    });
  },
  onSuccess: async () => {
    await qc.invalidateQueries({ queryKey: ["extension-policies", ws.currentId] });
    toast.push({ title: t("common.saved"), tone: "neutral" });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

type ChromeRuntime = {
  sendMessage: (
    extensionId: string,
    message: unknown,
    responseCallback?: (response: { ok?: boolean }) => void,
  ) => void;
  lastError?: { message?: string };
};

function chromeRuntime(): ChromeRuntime | null {
  const g = globalThis as { chrome?: { runtime?: ChromeRuntime } };
  return g.chrome?.runtime ?? null;
}

async function connectExtension() {
  const extId = String(cfg.extensionId || "").trim();
  const runtime = chromeRuntime();
  if (!extId || !runtime?.sendMessage) {
    toast.push({ title: t("integrations.extensionMissing"), tone: "danger" });
    return;
  }
  connecting.value = true;
  try {
    const { data } = await client.post({
      url: "/api/v1/extension/tokens",
      body: { label: "browser" },
      throwOnError: true,
    });
    const token = (data as { token: string }).token;
    await new Promise<void>((resolve, reject) => {
      runtime.sendMessage(
        extId,
        {
          type: "kame.connect",
          token,
          workspaceId: ws.currentId,
          apiBase: String(cfg.apiBase).replace(/\/$/, ""),
        },
        (resp) => {
          if (runtime.lastError?.message) {
            reject(new Error(runtime.lastError.message));
            return;
          }
          if (!resp?.ok) {
            reject(new Error("Extension did not connect"));
            return;
          }
          resolve();
        },
      );
    });
    toast.push({ title: t("integrations.extensionConnected"), tone: "neutral" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    connecting.value = false;
  }
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <PageHeader :title="t('settings.integrations')" />

    <section class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("integrations.claude") }}</h2>
      <div class="flex flex-col gap-2">
        <label class="text-sm text-ink-600">{{ t("integrations.mcpUrl") }}</label>
        <div class="flex flex-wrap items-center gap-2">
          <code class="rounded-sm bg-paper-2 px-2 py-1 font-mono text-xs">{{ mcpUrl }}</code>
          <FnButton size="sm" variant="ghost" @click="copy(mcpUrl)">{{
            t("common.copy")
          }}</FnButton>
        </div>
      </div>
      <div class="flex flex-col gap-2">
        <label class="text-sm text-ink-600">Claude Code</label>
        <div class="flex flex-wrap items-center gap-2">
          <code class="max-w-full break-all rounded-sm bg-paper-2 px-2 py-1 font-mono text-xs">{{
            setupCmd
          }}</code>
          <FnButton size="sm" variant="ghost" @click="copy(setupCmd)">{{
            t("common.copy")
          }}</FnButton>
        </div>
      </div>
      <div class="flex flex-col gap-2">
        <label class="text-sm text-ink-600">Plugin</label>
        <div class="flex flex-wrap items-center gap-2">
          <code class="max-w-full break-all rounded-sm bg-paper-2 px-2 py-1 font-mono text-xs">{{
            pluginCmd
          }}</code>
          <FnButton size="sm" variant="ghost" @click="copy(pluginCmd)">{{
            t("common.copy")
          }}</FnButton>
        </div>
      </div>
    </section>

    <section class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("integrations.inbox") }}</h2>
      <FnSkeleton v-if="inbox.isPending.value" class="h-10 w-64" />
      <p v-else class="text-sm text-ink-600">
        {{
          t("integrations.inboxStatus", {
            waiting: inbox.data.value?.waiting ?? 0,
            leased: inbox.data.value?.leased ?? 0,
          })
        }}
      </p>
      <div class="flex flex-wrap items-center gap-2">
        <code class="rounded-sm bg-paper-2 px-2 py-1 font-mono text-xs">{{ workCmd }}</code>
        <FnButton size="sm" variant="ghost" @click="copy(workCmd)">{{ t("common.copy") }}</FnButton>
      </div>
    </section>

    <section v-if="ws.canManage" class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("integrations.agents") }}</h2>
      <FnSkeleton v-if="tokens.isPending.value" class="h-24 w-full" />
      <ul v-else class="divide-y divide-rule border border-rule">
        <li
          v-for="tok in tokens.data.value ?? []"
          :key="tok.id"
          class="flex flex-wrap items-center justify-between gap-3 px-3 py-3"
        >
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium text-ink-900">{{ tok.client_name }}</span>
            <span class="font-mono text-xs text-ink-600">{{ tok.token_kind }}</span>
            <p class="font-mono text-xs text-ink-600">
              {{ tok.scopes.slice(0, 8).join(" ") }}
            </p>
          </div>
          <FnButton
            size="sm"
            variant="ghost"
            :disabled="revoke.isPending.value"
            @click="revoke.mutate(tok.id)"
            >{{ t("integrations.revoke") }}</FnButton
          >
        </li>
        <li v-if="!(tokens.data.value ?? []).length" class="px-3 py-4 text-sm text-ink-600">
          {{ t("integrations.noAgents") }}
        </li>
      </ul>
    </section>

    <section class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("integrations.routing") }}</h2>
      <ul class="flex flex-col gap-3">
        <li
          v-for="row in routing.data.value ?? []"
          :key="row.feature"
          class="flex flex-wrap items-center gap-3"
        >
          <span class="min-w-40 text-sm text-ink-900">{{ row.feature }}</span>
          <FnSelect
            :model-value="row.route"
            :options="routeOptions"
            :disabled="!ws.canManage || saveRoute.isPending.value"
            @update:model-value="
              (v) => {
                if (v) saveRoute.mutate({ ...row, route: v });
              }
            "
          />
        </li>
      </ul>
    </section>

    <section class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("integrations.extension") }}</h2>
      <FnButton
        size="sm"
        tone="primary"
        :disabled="connecting || !ws.currentId"
        @click="connectExtension"
        >{{ t("integrations.connectExtension") }}</FnButton
      >
    </section>

    <section v-if="ws.canManage" class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("integrations.runner") }}</h2>
      <div class="flex flex-wrap items-center gap-2">
        <select
          v-model="runnerMode"
          class="min-h-12 rounded-md border border-rule bg-paper-0 px-3 text-sm text-ink-900 focus-visible:border-brand-500 focus-visible:ring-4 focus-visible:ring-brand-100 focus-visible:outline-none"
        >
          <option value="local">{{ t("integrations.runnerLocal") }}</option>
          <option value="cloud">{{ t("integrations.runnerCloud") }}</option>
        </select>
        <FnButton
          size="sm"
          :disabled="createRunner.isPending.value"
          @click="createRunner.mutate()"
          >{{ t("integrations.runnerCreate") }}</FnButton
        >
      </div>
      <div v-if="newRunnerToken" class="flex flex-wrap items-center gap-2">
        <code class="max-w-full break-all rounded-sm bg-paper-2 px-2 py-1 font-mono text-xs">{{
          newRunnerToken
        }}</code>
        <FnButton size="sm" variant="ghost" @click="copy(newRunnerToken)">{{
          t("common.copy")
        }}</FnButton>
        <p class="w-full text-sm text-ink-600">{{ t("integrations.runnerTokenOnce") }}</p>
      </div>
      <ul class="divide-y divide-rule border border-rule">
        <li
          v-for="tok in runnerTokens.data.value ?? []"
          :key="tok.id"
          class="flex flex-wrap items-center justify-between gap-3 px-3 py-3"
        >
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium text-ink-900">{{ tok.label }}</span>
            <span class="font-mono text-xs text-ink-600">{{ tok.mode }}</span>
          </div>
          <FnButton
            size="sm"
            variant="ghost"
            :disabled="revokeRunner.isPending.value"
            @click="revokeRunner.mutate(tok.id)"
            >{{ t("integrations.revoke") }}</FnButton
          >
        </li>
        <li v-if="!(runnerTokens.data.value ?? []).length" class="px-3 py-4 text-sm text-ink-600">
          {{ t("integrations.runnerEmpty") }}
        </li>
      </ul>
    </section>

    <section v-if="ws.canManage" class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("integrations.platforms") }}</h2>
      <ul class="divide-y divide-rule border border-rule">
        <li
          v-for="p in restricted"
          :key="p.platform"
          class="flex flex-wrap items-center justify-between gap-3 px-3 py-3"
        >
          <span class="text-sm font-medium capitalize text-ink-900">{{ p.platform }}</span>
          <div class="flex flex-wrap items-center gap-3">
            <FnCheckbox
              v-if="!p.autofill_enabled"
              v-model="ack[p.platform]"
              :label="t('integrations.ackTerms')"
            />
            <FnButton
              v-if="!p.autofill_enabled"
              size="sm"
              :disabled="savePolicy.isPending.value || !ack[p.platform]"
              @click="
                savePolicy.mutate({
                  platform: p.platform,
                  autofill_enabled: true,
                  acknowledge_terms: true,
                })
              "
              >{{ t("integrations.enableAutofill") }}</FnButton
            >
            <FnButton
              v-else
              size="sm"
              tone="ghost"
              :disabled="savePolicy.isPending.value"
              @click="
                savePolicy.mutate({
                  platform: p.platform,
                  autofill_enabled: false,
                  acknowledge_terms: false,
                })
              "
              >{{ t("integrations.disableAutofill") }}</FnButton
            >
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>
