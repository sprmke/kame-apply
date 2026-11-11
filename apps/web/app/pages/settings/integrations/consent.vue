<script setup lang="ts">
import { client } from "@kame/api-client";
import { FnButton, FnSelect, FnSkeleton, useToast } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

definePageMeta({ layout: "default" });

const route = useRoute();
const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();

const pendingId = computed(() => String(route.query.pending_id || ""));
const selectedScopes = ref<string[]>([]);
const profileId = ref("");
const busy = ref(false);

const pending = useQuery({
  queryKey: computed(() => ["oauth-pending", pendingId.value, ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: `/api/v1/agent-bridge/pending/${pendingId.value}`,
      throwOnError: true,
    });
    return data as {
      id: string;
      client_name: string;
      scopes: string[];
      redirect_uri: string;
    };
  },
  enabled: computed(() => Boolean(pendingId.value && ws.currentId)),
});

watch(
  () => pending.data.value,
  (p) => {
    if (p?.scopes?.length && !selectedScopes.value.length) {
      selectedScopes.value = [...p.scopes];
    }
  },
);

const profiles = useQuery({
  queryKey: computed(() => ["profiles-for-consent", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({
      url: "/api/v1/profiles",
      throwOnError: true,
    });
    return (Array.isArray(data) ? data : []) as { id: string; display_name: string }[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const profileOptions = computed(() =>
  (profiles.data.value ?? []).map((profile) => ({
    value: profile.id,
    label: profile.display_name,
  })),
);

watch(
  () => profiles.data.value,
  (list) => {
    if (list?.length && !profileId.value) profileId.value = list[0]!.id;
  },
);

function toggleScope(scope: string, on: boolean) {
  if (on) selectedScopes.value = [...new Set([...selectedScopes.value, scope])];
  else selectedScopes.value = selectedScopes.value.filter((s) => s !== scope);
}

async function approve() {
  if (!pendingId.value || !profileId.value || !ws.currentId) return;
  busy.value = true;
  try {
    const { data } = await client.post({
      url: "/api/v1/agent-bridge/consent",
      body: {
        pending_id: pendingId.value,
        workspace_id: ws.currentId,
        profile_id: profileId.value,
        scopes: selectedScopes.value,
      },
      throwOnError: true,
    });
    const redirect = (data as { redirect_url: string }).redirect_url;
    window.location.href = redirect;
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="mx-auto flex max-w-lg flex-col gap-6">
    <PageHeader :title="t('integrations.consentTitle')" />
    <FnSkeleton v-if="pending.isPending.value" class="h-40 w-full" />
    <template v-else-if="pending.data.value">
      <p class="text-sm text-ink-600">
        {{ t("integrations.consentClient", { name: pending.data.value.client_name }) }}
      </p>
      <p class="font-mono text-xs text-ink-600 break-all">
        {{ pending.data.value.redirect_uri }}
      </p>
      <label class="text-sm text-ink-900">{{ t("integrations.profile") }}</label>
      <FnSelect
        v-model="profileId"
        :options="profileOptions"
        :ariaLabel="t('integrations.profile')"
      />
      <fieldset class="flex flex-col gap-2">
        <legend class="text-sm text-ink-900">{{ t("integrations.scopes") }}</legend>
        <label
          v-for="scope in pending.data.value.scopes"
          :key="scope"
          class="flex min-h-11 items-center gap-2 text-sm"
        >
          <input
            type="checkbox"
            class="size-4"
            :checked="selectedScopes.includes(scope)"
            @change="toggleScope(scope, ($event.target as HTMLInputElement).checked)"
          />
          <span class="font-mono text-xs">{{ scope }}</span>
        </label>
      </fieldset>
      <FnButton :disabled="busy || !profileId" @click="approve">{{
        t("integrations.allow")
      }}</FnButton>
    </template>
  </div>
</template>
