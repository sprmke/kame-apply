<script setup lang="ts">
import { resetPasswordApiV1AuthPasswordResetPost } from "@kame/api-client";
import { FnButton, FnField, FnInput, useToast } from "@kame/ui";
import { z } from "zod";
import { toApiError } from "~/lib/errors";

definePageMeta({ layout: "auth" });
const { t, te } = useI18n();
const route = useRoute();
const toast = useToast();
const token = computed(() => (typeof route.query.token === "string" ? route.query.token : ""));
const { form, err } = useZodForm(z.object({ password: z.string().min(10).max(128) }));
const [password, passwordAttrs] = form.defineField("password");
const formError = ref<string | null>(null);

const submit = form.handleSubmit(async (v) => {
  formError.value = null;
  try {
    await resetPasswordApiV1AuthPasswordResetPost({
      body: { token: token.value, password: v.password },
    });
    toast.push({ title: t("auth.resetDone"), tone: "success" });
    await navigateTo("/login");
  } catch (e) {
    const { code } = toApiError(e);
    formError.value = te(`errors.${code}`) ? t(`errors.${code}`) : t("errors.generic");
  }
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <h1 class="font-serif text-2xl font-semibold">{{ t("auth.resetTitle") }}</h1>
    <p v-if="!token" role="alert" class="text-sm">{{ t("errors.invalid_token") }}</p>
    <form v-else class="flex flex-col gap-4" novalidate @submit.prevent="submit">
      <p v-if="formError" role="alert" class="flex gap-2 text-sm">
        <span class="text-oxblood-600" aria-hidden="true">✕</span>{{ formError }}
      </p>
      <FnField
        v-slot="{ id, describedby, invalid }"
        :label="t('auth.newPassword')"
        :hint="t('auth.passwordHint')"
        :error="err('password')"
      >
        <FnInput
          :id="id"
          v-model="password"
          v-bind="passwordAttrs"
          type="password"
          autocomplete="new-password"
          :describedby="describedby"
          :invalid="invalid"
        />
      </FnField>
      <FnButton type="submit" tone="primary" :loading="form.isSubmitting.value">{{
        t("auth.setPassword")
      }}</FnButton>
    </form>
  </div>
</template>
