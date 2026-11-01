<script setup lang="ts">
import { resendVerificationApiV1AuthVerifyEmailResendPost } from "@kame/api-client";
import { FnButton, useToast } from "@kame/ui";
import { useAuthStore } from "~/stores/auth";

const { t } = useI18n();
const auth = useAuthStore();
const toast = useToast();
const apiError = useApiError();
const busy = ref(false);

async function resend() {
  busy.value = true;
  try {
    await resendVerificationApiV1AuthVerifyEmailResendPost();
    toast.push({ title: t("verify.sent"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div
    v-if="auth.user && !auth.user.email_verified"
    role="status"
    class="flex flex-wrap items-center gap-3 rounded-md border border-saffron-600 bg-paper-1 px-4 py-3 text-sm"
  >
    <span aria-hidden="true" class="text-saffron-600">!</span>
    <span class="flex-1">{{ t("verify.banner", { email: auth.user.email }) }}</span>
    <FnButton size="sm" :loading="busy" @click="resend">{{ t("verify.resend") }}</FnButton>
  </div>
</template>
