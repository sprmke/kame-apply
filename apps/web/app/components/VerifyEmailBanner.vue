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
    class="flex flex-col gap-3 rounded-xl border border-saffron-600 bg-paper-1 px-4 py-4 text-sm sm:flex-row sm:items-center"
  >
    <span class="flex flex-1 items-start gap-3">
      <span aria-hidden="true" class="mt-0.5 font-bold text-saffron-600">!</span>
      <span class="break-words">{{ t("verify.banner", { email: auth.user.email }) }}</span>
    </span>
    <FnButton class="self-start sm:self-auto" size="sm" :loading="busy" @click="resend">{{
      t("verify.resend")
    }}</FnButton>
  </div>
</template>
