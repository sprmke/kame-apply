<script setup lang="ts">
import { FnSkeleton } from "@kame/ui";
import { useAuthStore } from "~/stores/auth";

definePageMeta({ layout: "auth" });
const { t } = useI18n();
const auth = useAuthStore();

// The API set the refresh cookie before redirecting here; the route middleware already
// exchanged it for an access token. Just continue.
onMounted(async () => {
  await navigateTo(auth.isAuthed ? "/" : { path: "/login", query: { error: "oauth_failed" } });
});
</script>

<template>
  <div class="flex flex-col gap-4" role="status">
    <p class="text-sm text-ink-600">{{ t("auth.signingIn") }}</p>
    <FnSkeleton :lines="2" />
  </div>
</template>
