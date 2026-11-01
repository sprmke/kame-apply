<script setup lang="ts">
import { queries, schemas, type CredentialRead } from "@kame/api-client";
import {
  FnButton,
  FnChip,
  FnCheckbox,
  FnDialog,
  FnField,
  FnInput,
  FnSelect,
  FnSkeleton,
  FnTable,
  useToast,
} from "@kame/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { z } from "zod";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const ws = useWorkspaceStore();
const toast = useToast();
const apiError = useApiError();
const qc = useQueryClient();

const manage = computed(() => ws.canManage);
const usage = useQuery(queries.getUsageApiV1AiUsageGetOptions());
const creds = useQuery({
  ...queries.listCredentialsApiV1AiCredentialsGetOptions(),
  enabled: manage,
});
const providers = useQuery({
  ...queries.listProvidersApiV1AiProvidersGetOptions(),
  enabled: manage,
});
const aiSettings = useQuery({
  ...queries.getAiSettingsApiV1AiSettingsGetOptions(),
  enabled: manage,
});

const addCred = useMutation(queries.addCredentialApiV1AiCredentialsPostMutation());
const delCred = useMutation(queries.deleteCredentialApiV1AiCredentialsCredentialIdDeleteMutation());
const testCred = useMutation(
  queries.testCredentialApiV1AiCredentialsCredentialIdTestPostMutation(),
);
const saveSettings = useMutation(queries.updateAiSettingsApiV1AiSettingsPatchMutation());
const refresh = () => qc.invalidateQueries();

// --- add key ---
const addOpen = ref(false);
const schema = schemas.zCredentialCreate.extend({
  provider: z.string().min(1),
  api_key: z.string().max(500).nullish(),
});
const { form, err } = useZodForm(schema, {
  provider: "gemini",
  api_key: "",
  label: "",
  base_url: "",
});
const [provider] = form.defineField("provider");
const [apiKey, apiKeyAttrs] = form.defineField("api_key");
const [label, labelAttrs] = form.defineField("label");
const [baseUrl] = form.defineField("base_url");
const addError = ref<string | null>(null);
const needsKey = computed(
  () => providers.data.value?.find((p) => p.id === provider.value)?.needs_key ?? true,
);
watch(addOpen, (o) => {
  if (o) {
    form.resetForm({ values: { provider: "gemini", api_key: "", label: "", base_url: "" } });
    addError.value = null;
  }
});
const submitAdd = form.handleSubmit(async (v) => {
  addError.value = null;
  if (needsKey.value && !v.api_key) {
    form.setFieldError("api_key", "validation.required");
    return;
  }
  try {
    const created = await addCred.mutateAsync({
      body: {
        provider: v.provider,
        api_key: v.api_key || null,
        label: v.label || null,
        base_url: v.base_url || null,
      },
    });
    addOpen.value = false;
    await refresh();
    await onTest(created);
  } catch (e) {
    addError.value = apiError(e);
  }
});

async function onTest(c: Pick<CredentialRead, "id">) {
  try {
    const r = await testCred.mutateAsync({ path: { credential_id: c.id } });
    toast.push({
      title:
        r.status === "valid"
          ? t("ai.testValid")
          : r.status === "invalid"
            ? t("ai.testInvalid")
            : t("ai.testError"),
      tone: r.status === "valid" ? "success" : "danger",
    });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
  await refresh();
}

const deleting = ref<CredentialRead | null>(null);
const deleteOpen = computed({
  get: () => !!deleting.value,
  set: (v) => !v && (deleting.value = null),
});
async function confirmDelete() {
  if (!deleting.value) return;
  await delCred.mutateAsync({ path: { credential_id: deleting.value.id } });
  deleting.value = null;
  await refresh();
}

// --- budget ---
const budget = ref("");
const budgetError = ref<string | null>(null);
watch(
  () => aiSettings.data.value?.monthly_budget_cents,
  (c) => c !== undefined && (budget.value = (c / 100).toFixed(2)),
  { immediate: true },
);
async function saveBudget() {
  const cents = Math.round(Number(budget.value) * 100);
  if (!Number.isFinite(cents) || cents < 0) {
    budgetError.value = t("validation.invalid");
    return;
  }
  budgetError.value = null;
  try {
    await saveSettings.mutateAsync({ body: { monthly_budget_cents: cents } });
    toast.push({ title: t("common.saved"), tone: "success" });
    await refresh();
  } catch (e) {
    budgetError.value = apiError(e);
  }
}

// --- tiers and fallback ---
const TIERS = ["bulk", "standard", "premium"] as const;
const tierProvider = reactive<Record<string, string>>({
  bulk: "auto",
  standard: "auto",
  premium: "auto",
});
const tierModel = reactive<Record<string, string>>({ bulk: "", standard: "", premium: "" });
const fallback = ref(false);
watch(
  () => aiSettings.data.value,
  (s) => {
    if (!s) return;
    for (const tier of TIERS) {
      tierProvider[tier] = s.tier_models[tier]?.provider ?? "auto";
      tierModel[tier] = s.tier_models[tier]?.model ?? "";
    }
    fallback.value = s.fallback_enabled;
  },
  { immediate: true },
);
const providerOptions = computed(() => [
  { value: "auto", label: t("ai.auto") },
  ...(providers.data.value ?? []).map((p) => ({ value: p.id, label: p.label })),
]);
const tierError = ref<string | null>(null);
async function saveTiers() {
  tierError.value = null;
  const tier_models: Record<string, { provider: string; model: string }> = {};
  for (const tier of TIERS) {
    if (tierProvider[tier] === "auto") continue;
    const model =
      tierModel[tier] ||
      providers.data.value?.find((p) => p.id === tierProvider[tier])?.tier_models[tier] ||
      "";
    tier_models[tier] = { provider: tierProvider[tier]!, model };
  }
  try {
    await saveSettings.mutateAsync({ body: { tier_models, fallback_enabled: fallback.value } });
    toast.push({ title: t("common.saved"), tone: "success" });
    await refresh();
  } catch (e) {
    tierError.value = apiError(e);
  }
}

const credColumns = computed(() => [
  { key: "provider", label: t("ai.provider") },
  { key: "key", label: t("ai.key") },
  { key: "status", label: t("ai.status") },
  { key: "actions", label: "" },
]);
const credRows = computed(() =>
  (creds.data.value ?? []).map((c) => ({ ...c, key: c.key_hint ? `••••${c.key_hint}` : "—" })),
);
const providerLabel = (id: string) => providers.data.value?.find((p) => p.id === id)?.label ?? id;
const statusGlyph = { valid: "✓", invalid: "✕", untested: "•" } as const;
</script>

<template>
  <section class="flex flex-col gap-10">
    <PageHeader :title="t('settings.ai')" :lede="t('ai.lede')" />

    <div class="flex flex-col gap-3">
      <h2 class="font-serif text-lg font-semibold">{{ t("ai.usageTitle") }}</h2>
      <FnSkeleton v-if="usage.isPending.value" :lines="3" />
      <template v-else-if="usage.data.value">
        <UsageMeter
          :spent-micros="usage.data.value.spent_micros"
          :budget-cents="usage.data.value.budget_cents"
        />
        <UsageChart :days="usage.data.value.by_day" :caption="t('usage.thisMonth')" />
      </template>
    </div>

    <p v-if="!manage" class="text-sm text-ink-600">{{ t("ai.ownersOnly") }}</p>
    <template v-else>
      <div class="flex flex-col gap-3">
        <div class="flex items-center justify-between gap-3">
          <h2 class="font-serif text-lg font-semibold">{{ t("ai.keysTitle") }}</h2>
          <FnButton tone="primary" @click="addOpen = true">{{ t("ai.addKey") }}</FnButton>
        </div>
        <FnSkeleton v-if="creds.isPending.value" :lines="3" />
        <FnTable
          v-else
          :columns="credColumns"
          :rows="credRows"
          row-key="id"
          :caption="t('ai.keysTitle')"
          :empty="t('ai.noKeys')"
        >
          <template #cell-provider="{ row }"
            ><span class="font-medium">{{ providerLabel(row.provider) }}</span
            ><span v-if="row.label" class="ml-2 text-xs text-ink-600">{{
              row.label
            }}</span></template
          >
          <template #cell-key="{ row }"
            ><span class="font-mono text-xs">{{ row.key }}</span></template
          >
          <template #cell-status="{ row }">
            <FnChip :tone="row.status === 'invalid' ? 'neutral' : 'neutral'">
              <span
                aria-hidden="true"
                :class="
                  row.status === 'valid'
                    ? 'text-fern-600'
                    : row.status === 'invalid'
                      ? 'text-oxblood-600'
                      : 'text-ink-600'
                "
                >{{ statusGlyph[row.status as keyof typeof statusGlyph] }}</span
              >
              {{ t(`ai.status_${row.status}`) }}
            </FnChip>
          </template>
          <template #cell-actions="{ row }">
            <div class="flex justify-end gap-1">
              <FnButton
                size="sm"
                :loading="
                  testCred.isPending.value &&
                  testCred.variables.value?.path.credential_id === row.id
                "
                @click="onTest(row)"
                >{{ t("ai.test") }}</FnButton
              >
              <FnButton size="sm" tone="ghost" @click="deleting = row">{{
                t("common.delete")
              }}</FnButton>
            </div>
          </template>
        </FnTable>
      </div>

      <form class="flex max-w-xs flex-col gap-3" novalidate @submit.prevent="saveBudget">
        <h2 class="font-serif text-lg font-semibold">{{ t("ai.budgetTitle") }}</h2>
        <FnField
          v-slot="{ id, describedby, invalid }"
          :label="t('ai.budget')"
          :hint="t('ai.budgetHint')"
          :error="budgetError"
        >
          <FnInput
            :id="id"
            v-model="budget"
            inputmode="decimal"
            :describedby="describedby"
            :invalid="invalid"
          />
        </FnField>
        <div>
          <FnButton type="submit" :loading="saveSettings.isPending.value">{{
            t("common.save")
          }}</FnButton>
        </div>
      </form>

      <form class="flex flex-col gap-3" novalidate @submit.prevent="saveTiers">
        <h2 class="font-serif text-lg font-semibold">{{ t("ai.tiersTitle") }}</h2>
        <p class="text-sm text-ink-600">{{ t("ai.tiersLede") }}</p>
        <p v-if="tierError" role="alert" class="text-sm text-oxblood-600">{{ tierError }}</p>
        <div
          v-for="tier in TIERS"
          :key="tier"
          class="grid items-end gap-3 sm:grid-cols-[8rem_1fr_1fr]"
        >
          <span class="pb-3 text-sm font-medium">{{ t(`ai.tier_${tier}`) }}</span>
          <FnField v-slot="{ id }" :label="t('ai.provider')"
            ><FnSelect :id="id" v-model="tierProvider[tier]" :options="providerOptions"
          /></FnField>
          <FnField v-slot="{ id }" :label="t('ai.model')"
            ><FnInput
              :id="id"
              v-model="tierModel[tier]"
              :disabled="tierProvider[tier] === 'auto'"
              autocomplete="off"
          /></FnField>
        </div>
        <FnCheckbox v-model="fallback" :label="t('ai.fallback')" />
        <div>
          <FnButton type="submit" :loading="saveSettings.isPending.value">{{
            t("common.save")
          }}</FnButton>
        </div>
      </form>
    </template>

    <FnDialog
      v-model:open="addOpen"
      :title="t('ai.addKey')"
      :description="t('ai.addKeyHint')"
      :close-label="t('common.close')"
    >
      <form class="flex flex-col gap-4" novalidate @submit.prevent="submitAdd">
        <p v-if="addError" role="alert" class="text-sm text-oxblood-600">{{ addError }}</p>
        <FnField v-slot="{ id }" :label="t('ai.provider')">
          <FnSelect
            :id="id"
            v-model="provider"
            :options="(providers.data.value ?? []).map((p) => ({ value: p.id, label: p.label }))"
          />
        </FnField>
        <template v-if="needsKey">
          <FnField
            v-slot="{ id, describedby, invalid }"
            :label="t('ai.apiKey')"
            :error="err('api_key')"
          >
            <FnInput
              :id="id"
              v-model="apiKey"
              v-bind="apiKeyAttrs"
              type="password"
              autocomplete="off"
              :describedby="describedby"
              :invalid="invalid"
            />
          </FnField>
        </template>
        <FnField
          v-show="provider === 'ollama'"
          for="ai-base-url"
          :label="t('ai.baseUrl')"
          :error="err('base_url')"
        >
          <FnInput
            id="ai-base-url"
            v-model="baseUrl"
            placeholder="http://localhost:11434/v1"
            :describedby="err('base_url') ? 'ai-base-url-error' : undefined"
            :invalid="!!err('base_url')"
          />
        </FnField>
        <FnField v-slot="{ id, describedby, invalid }" :label="t('ai.label')" :error="err('label')">
          <FnInput
            :id="id"
            v-model="label"
            v-bind="labelAttrs"
            :describedby="describedby"
            :invalid="invalid"
          />
        </FnField>
        <div class="flex justify-end gap-2">
          <FnButton @click="addOpen = false">{{ t("common.cancel") }}</FnButton>
          <FnButton type="submit" tone="primary" :loading="addCred.isPending.value">{{
            t("ai.saveAndTest")
          }}</FnButton>
        </div>
      </form>
    </FnDialog>

    <FnDialog
      v-model:open="deleteOpen"
      :title="t('ai.deleteTitle')"
      :description="t('ai.deleteBody')"
      :close-label="t('common.close')"
    >
      <div class="flex justify-end gap-2">
        <FnButton @click="deleting = null">{{ t("common.cancel") }}</FnButton>
        <FnButton tone="danger" :loading="delCred.isPending.value" @click="confirmDelete">{{
          t("common.delete")
        }}</FnButton>
      </div>
    </FnDialog>
  </section>
</template>
