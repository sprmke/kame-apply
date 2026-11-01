<script setup lang="ts">
import { ok } from "~/lib/api";
import {
  googleLinkApiV1AuthGoogleLinkPost,
  googleUnlinkApiV1AuthGoogleLinkDelete,
  queries,
  updateMeApiV1MePatch,
} from "@kame/api-client";
import { FnButton, FnChip, FnField, FnInput, FnSelect, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useAuthStore } from "~/stores/auth";

const { t } = useI18n();
const auth = useAuthStore();
const toast = useToast();
const apiError = useApiError();
const route = useRoute();
const qc = useQueryClient();
const { choice, set } = useTheme();

const me = useQuery(queries.getMeApiV1MeGetOptions());
const providersQ = useQuery({
  queryKey: ["auth-providers"],
  queryFn: async () =>
    (await import("@kame/api-client")).authProvidersApiV1AuthProvidersGet().then((r) => r.data),
});
const zones = computed(() => {
  const all = (
    Intl as unknown as { supportedValuesOf?: (k: string) => string[] }
  ).supportedValuesOf?.("timeZone") ?? ["UTC"];
  return (all.includes("UTC") ? all : ["UTC", ...all]).map((z) => ({ value: z, label: z }));
});

const name = ref("");
const timezone = ref("UTC");
watch(
  () => me.data.value,
  (m) => {
    if (m) {
      name.value = m.name ?? "";
      timezone.value = m.timezone;
    }
  },
  { immediate: true },
);
const saving = ref(false);
const error = ref<string | null>(null);

async function save() {
  saving.value = true;
  error.value = null;
  try {
    const data = await ok(
      updateMeApiV1MePatch({ body: { name: name.value, timezone: timezone.value } }),
    );
    if (auth.user) auth.user = { ...auth.user, name: data.name, timezone: data.timezone };
    toast.push({ title: t("common.saved"), tone: "success" });
    await qc.invalidateQueries();
  } catch (e) {
    error.value = apiError(e);
  } finally {
    saving.value = false;
  }
}

const hasGoogle = computed(() => me.data.value?.providers.includes("google"));
async function linkGoogle() {
  try {
    const data = await ok(googleLinkApiV1AuthGoogleLinkPost());
    window.location.href = data.url;
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}
async function unlinkGoogle() {
  try {
    await googleUnlinkApiV1AuthGoogleLinkDelete();
    toast.push({ title: t("profile.unlinked"), tone: "success" });
    await qc.invalidateQueries();
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}
onMounted(
  () =>
    route.query.linked === "google" && toast.push({ title: t("profile.linked"), tone: "success" }),
);

const themes = computed(() =>
  (["system", "light", "dark"] as const).map((v) => ({ value: v, label: t(`theme.${v}`) })),
);
</script>

<template>
  <section class="flex max-w-md flex-col gap-8">
    <PageHeader :title="t('settings.profile')" />
    <form class="flex flex-col gap-4" novalidate @submit.prevent="save">
      <p v-if="error" role="alert" class="text-sm text-oxblood-600">{{ error }}</p>
      <FnField v-slot="{ id }" :label="t('auth.email')"
        ><FnInput :id="id" :model-value="auth.user?.email ?? ''" disabled
      /></FnField>
      <FnField v-slot="{ id }" :label="t('auth.name')"
        ><FnInput :id="id" v-model="name" autocomplete="name"
      /></FnField>
      <FnField v-slot="{ id }" :label="t('profile.timezone')" :hint="t('profile.timezoneHint')"
        ><FnSelect :id="id" v-model="timezone" :options="zones"
      /></FnField>
      <div>
        <FnButton type="submit" tone="primary" :loading="saving">{{ t("common.save") }}</FnButton>
      </div>
    </form>

    <FnField v-slot="{ id }" :label="t('theme.label')">
      <FnSelect
        :id="id"
        :model-value="choice"
        :options="themes"
        @update:model-value="(v) => v && set(v as 'system' | 'light' | 'dark')"
      />
    </FnField>

    <div class="flex flex-col gap-2 border-t border-rule pt-4">
      <h2 class="font-medium">{{ t("profile.connected") }}</h2>
      <div class="flex items-center gap-3">
        <NavIcon name="ph:google-logo" />
        <span>Google</span>
        <template v-if="hasGoogle">
          <FnChip
            ><span class="text-fern-600" aria-hidden="true">✓</span>
            {{ t("profile.linkedState") }}</FnChip
          >
          <FnButton size="sm" tone="ghost" @click="unlinkGoogle">{{
            t("profile.unlink")
          }}</FnButton>
        </template>
        <FnButton v-else-if="providersQ.data.value?.google" size="sm" @click="linkGoogle">{{
          t("profile.link")
        }}</FnButton>
        <span v-else class="text-sm text-ink-600">{{ t("profile.notAvailable") }}</span>
      </div>
    </div>
  </section>
</template>
