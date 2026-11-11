<script setup lang="ts">
import { forgotPasswordApiV1AuthPasswordForgotPost, schemas } from "@kame/api-client";
import { FnButton, FnField, FnInput } from "@kame/ui";

definePageMeta({ layout: "auth" });
const { t } = useI18n();
const apiError = useApiError();
const { form, err } = useZodForm(schemas.zForgotIn);
const [email, emailAttrs] = form.defineField("email");
const sent = ref(false);
const formError = ref<string | null>(null);

const submit = form.handleSubmit(async (v) => {
  formError.value = null;
  try {
    await forgotPasswordApiV1AuthPasswordForgotPost({ body: { email: v.email } });
    sent.value = true;
  } catch (e) {
    formError.value = apiError(e);
  }
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <h1 class="font-serif text-2xl font-semibold">{{ t("auth.forgotTitle") }}</h1>
    <p v-if="sent" role="status" class="text-sm">{{ t("auth.forgotSent") }}</p>
    <form v-else class="flex flex-col gap-4" novalidate @submit.prevent="submit">
      <p v-if="formError" role="alert" class="text-sm text-oxblood-600">{{ formError }}</p>
      <FnField v-slot="{ id, describedby, invalid }" :label="t('auth.email')" :error="err('email')">
        <FnInput
          :id="id"
          v-model="email"
          v-bind="emailAttrs"
          type="email"
          autocomplete="email"
          inputmode="email"
          :describedby="describedby"
          :invalid="invalid"
        />
      </FnField>
      <FnButton type="submit" tone="primary" :loading="form.isSubmitting.value">{{
        t("auth.sendLink")
      }}</FnButton>
    </form>
    <NuxtLink to="/login" class="text-sm text-brand-700 underline underline-offset-2">{{
      t("auth.backToSignIn")
    }}</NuxtLink>
  </div>
</template>
