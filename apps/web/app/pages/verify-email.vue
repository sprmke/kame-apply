<script setup lang="ts">
import { verifyEmailApiV1AuthVerifyEmailPost } from "@kame/api-client";
import { FnButton, FnSkeleton } from "@kame/ui";
import { useAuthStore } from "~/stores/auth";

definePageMeta({ layout: "auth" });
const { t } = useI18n();
const route = useRoute();
const auth = useAuthStore();
const state = ref<"working" | "done" | "failed">("working");

onMounted(async () => {
  const token = route.query.token;
  if (typeof token !== "string") {
    state.value = "failed";
    return;
  }
  try {
    await verifyEmailApiV1AuthVerifyEmailPost({ body: { token } });
    if (auth.user) auth.user = { ...auth.user, email_verified: true };
    state.value = "done";
  } catch {
    state.value = "failed";
  }
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <h1 class="font-serif text-2xl font-semibold">{{ t("auth.verifyTitle") }}</h1>
    <FnSkeleton v-if="state === 'working'" :lines="2" />
    <p v-else-if="state === 'done'" role="status" class="text-sm">{{ t("auth.verified") }}</p>
    <p v-else role="alert" class="text-sm">{{ t("errors.invalid_token") }}</p>
    <FnButton v-if="state !== 'working'" as-child tone="primary"
      ><NuxtLink to="/">{{ t("common.continue") }}</NuxtLink></FnButton
    >
  </div>
</template>
