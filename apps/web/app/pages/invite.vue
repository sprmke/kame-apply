<script setup lang="ts">
import { ok } from "~/lib/api";
import { acceptInvitationApiV1InvitationsAcceptPost } from "@kame/api-client";
import { FnButton } from "@kame/ui";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

definePageMeta({ layout: "auth" });
const { t } = useI18n();
const route = useRoute();
const auth = useAuthStore();
const workspace = useWorkspaceStore();
const apiError = useApiError();
const token = computed(() => (typeof route.query.token === "string" ? route.query.token : ""));
const next = computed(() => `/invite?token=${encodeURIComponent(token.value)}`);
const busy = ref(false);
const error = ref<string | null>(null);

async function accept() {
  busy.value = true;
  error.value = null;
  try {
    const data = await ok(
      acceptInvitationApiV1InvitationsAcceptPost({ body: { token: token.value } }),
    );
    await workspace.load();
    workspace.select(data.id);
    await navigateTo("/");
  } catch (e) {
    error.value = apiError(e);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <h1 class="font-serif text-2xl font-semibold">{{ t("invite.title") }}</h1>
    <p v-if="!token" role="alert" class="text-sm">{{ t("errors.invalid_invitation") }}</p>
    <template v-else-if="!auth.isAuthed">
      <p class="text-sm text-ink-600">{{ t("invite.signInFirst") }}</p>
      <div class="flex flex-col gap-2">
        <FnButton as-child tone="primary"
          ><NuxtLink :to="{ path: '/login', query: { next } }">{{
            t("auth.signIn")
          }}</NuxtLink></FnButton
        >
        <FnButton as-child
          ><NuxtLink :to="{ path: '/register', query: { next } }">{{
            t("auth.createAccount")
          }}</NuxtLink></FnButton
        >
      </div>
    </template>
    <template v-else>
      <p class="text-sm text-ink-600">{{ t("invite.signedInAs", { email: auth.user?.email }) }}</p>
      <p v-if="error" role="alert" class="flex gap-2 text-sm">
        <span class="text-oxblood-600" aria-hidden="true">✕</span>{{ error }}
      </p>
      <FnButton tone="primary" :loading="busy" @click="accept">{{ t("invite.join") }}</FnButton>
    </template>
  </div>
</template>
