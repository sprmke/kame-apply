<script setup lang="ts">
import { queries } from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton, useToast } from "@kame/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const fmt = useFormat();
const qc = useQueryClient();
const sessions = useQuery(queries.listSessionsApiV1MeSessionsGetOptions());
const revoke = useMutation(queries.revokeSessionApiV1MeSessionsSessionIdDeleteMutation());

function device(ua: string | null | undefined): string {
  if (!ua) return t("sessions.unknown");
  const browser = /Edg\//.test(ua)
    ? "Edge"
    : /Chrome\//.test(ua)
      ? "Chrome"
      : /Firefox\//.test(ua)
        ? "Firefox"
        : /Safari\//.test(ua)
          ? "Safari"
          : null;
  const os = /Windows/.test(ua)
    ? "Windows"
    : /Mac OS X/.test(ua)
      ? "macOS"
      : /Android/.test(ua)
        ? "Android"
        : /iPhone|iPad/.test(ua)
          ? "iOS"
          : /Linux/.test(ua)
            ? "Linux"
            : null;
  return [browser, os].filter(Boolean).join(" · ") || t("sessions.unknown");
}

async function onRevoke(id: string) {
  try {
    await revoke.mutateAsync({ path: { session_id: id } });
    toast.push({ title: t("sessions.revoked"), tone: "success" });
    await qc.invalidateQueries();
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}
</script>

<template>
  <section class="flex flex-col gap-4">
    <PageHeader :title="t('settings.sessions')" :lede="t('sessions.lede')" />
    <FnSkeleton v-if="sessions.isPending.value" :lines="3" />
    <ul v-else class="flex flex-col divide-y divide-rule border-y border-rule">
      <li
        v-for="s in sessions.data.value"
        :key="s.id"
        class="flex min-h-16 flex-wrap items-center gap-3 py-2"
      >
        <div class="min-w-0 flex-1">
          <p class="font-medium">
            {{ device(s.user_agent) }}
            <FnChip v-if="s.current" tone="accent">{{ t("sessions.current") }}</FnChip>
          </p>
          <p class="font-mono text-xs text-ink-600">
            {{ s.ip }} · {{ t("sessions.lastUsed", { when: fmt.dateTime(s.last_used_at) }) }}
          </p>
        </div>
        <FnButton
          v-if="!s.current"
          size="sm"
          tone="danger"
          :loading="revoke.isPending.value && revoke.variables.value?.path.session_id === s.id"
          @click="onRevoke(s.id)"
          >{{ t("sessions.revoke") }}</FnButton
        >
      </li>
    </ul>
  </section>
</template>
