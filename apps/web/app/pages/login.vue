<script setup lang="ts">
import { schemas } from "@kame/api-client";
import { FnButton, FnField, FnInput } from "@kame/ui";
import { z } from "zod";
import { safeNext } from "~/lib/next";
import { toApiError } from "~/lib/errors";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

definePageMeta({ layout: "auth" });
const { t, te } = useI18n();
const route = useRoute();
const auth = useAuthStore();
const workspace = useWorkspaceStore();
const schema = schemas.zLoginIn.extend({ password: z.string().min(1).max(128) });
const { form, err } = useZodForm(schema);
const [email, emailAttrs] = form.defineField("email");
const [password, passwordAttrs] = form.defineField("password");
const formError = ref<string | null>(null);
const oauthError = computed(() => {
  const code = route.query.error;
  return typeof code === "string" && te(`errors.${code}`) ? t(`errors.${code}`) : null;
});

const submit = form.handleSubmit(async (v) => {
  formError.value = null;
  try {
    await auth.login(v.email, v.password);
    await workspace.load();
    await navigateTo(safeNext(route.query.next));
  } catch (e) {
    const { code } = toApiError(e);
    formError.value = te(`errors.${code}`) ? t(`errors.${code}`) : t("errors.generic");
  }
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <h1 class="font-serif text-2xl font-semibold">{{ t("auth.loginTitle") }}</h1>
    <p v-if="oauthError || formError" role="alert" class="flex gap-2 text-sm">
      <span class="text-oxblood-600" aria-hidden="true">✕</span
      ><span>{{ oauthError || formError }}</span>
    </p>
    <form class="flex flex-col gap-4" novalidate @submit.prevent="submit">
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
      <FnField
        v-slot="{ id, describedby, invalid }"
        :label="t('auth.password')"
        :error="err('password')"
      >
        <FnInput
          :id="id"
          v-model="password"
          v-bind="passwordAttrs"
          type="password"
          autocomplete="current-password"
          :describedby="describedby"
          :invalid="invalid"
        />
      </FnField>
      <FnButton type="submit" tone="primary" :loading="form.isSubmitting.value">{{
        t("auth.signIn")
      }}</FnButton>
    </form>
    <GoogleButton />
    <div class="flex flex-col gap-2 text-sm text-ink-600">
      <NuxtLink to="/forgot-password" class="text-brand-700 underline underline-offset-2">{{
        t("auth.forgot")
      }}</NuxtLink>
      <span
        >{{ t("auth.noAccount") }}
        <NuxtLink
          :to="{ path: '/register', query: route.query.next ? { next: route.query.next } : {} }"
          class="text-brand-700 underline underline-offset-2"
          >{{ t("auth.createAccount") }}</NuxtLink
        ></span
      >
    </div>
  </div>
</template>
