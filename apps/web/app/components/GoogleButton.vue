<script setup lang="ts">
import { authProvidersApiV1AuthProvidersGet } from "@kame/api-client";
import { FnButton } from "@kame/ui";
import { useQuery } from "@tanstack/vue-query";

const { t } = useI18n();
const { public: cfg } = useRuntimeConfig();
const { data } = useQuery({
  queryKey: ["auth-providers"],
  queryFn: async () => (await authProvidersApiV1AuthProvidersGet()).data,
  staleTime: 5 * 60_000,
});
</script>

<template>
  <FnButton
    v-if="data?.google"
    as="a"
    :href="`${cfg.apiBase}/api/v1/auth/google/start`"
    class="w-full"
  >
    <NavIcon name="ph:google-logo" />{{ t("auth.google") }}
  </FnButton>
</template>
