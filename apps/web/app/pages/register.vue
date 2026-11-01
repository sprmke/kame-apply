<script setup lang="ts">
import { schemas } from "@kame/api-client";
import { FnButton, FnField, FnInput } from "@kame/ui";
import { z } from "zod";
import { toApiError } from "~/lib/errors";
import { safeNext } from "~/lib/next";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

definePageMeta({ layout: "auth" });
const { t, te } = useI18n();
const route = useRoute();
const auth = useAuthStore();
const workspace = useWorkspaceStore();
const schema = schemas.zRegisterIn.extend({
  name: z.string().max(120).optional(),
  password: z.string().min(10).max(128),
});
const { form, err } = useZodForm(schema);
const [name, nameAttrs] = form.defineField("name");
const [email, emailAttrs] = form.defineField("email");
const [password, passwordAttrs] = form.defineField("password");
const formError = ref<string | null>(null);

const submit = form.handleSubmit(async (v) => {
  formError.value = null;
  try {
    await auth.register(v.email, v.password, v.name);
    await workspace.load();
    await navigateTo(safeNext(route.query.next));
  } catch (e) {
    const { code } = toApiError(e);
    if (code === "email_taken") form.setFieldError("email", "validation.emailTaken");
    else formError.value = te(`errors.${code}`) ? t(`errors.${code}`) : t("errors.generic");
  }
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <h1 class="font-serif text-2xl font-semibold">{{ t("auth.registerTitle") }}</h1>
    <p v-if="formError" role="alert" class="flex gap-2 text-sm">
      <span class="text-oxblood-600" aria-hidden="true">✕</span><span>{{ formError }}</span>
    </p>
    <form class="flex flex-col gap-4" novalidate @submit.prevent="submit">
      <FnField v-slot="{ id, describedby, invalid }" :label="t('auth.name')" :error="err('name')">
        <FnInput
          :id="id"
          v-model="name"
          v-bind="nameAttrs"
          autocomplete="name"
          :describedby="describedby"
          :invalid="invalid"
        />
      </FnField>
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
        t("auth.createAccount")
      }}</FnButton>
    </form>
    <GoogleButton />
    <p class="text-sm text-ink-600">
      {{ t("auth.haveAccount") }}
      <NuxtLink
        :to="{ path: '/login', query: route.query.next ? { next: route.query.next } : {} }"
        class="text-persimmon-700 underline underline-offset-2"
        >{{ t("auth.signIn") }}</NuxtLink
      >
    </p>
  </div>
</template>
