<script setup lang="ts">
import { queries } from "@kame/api-client";
import {
  FnButton,
  FnChip,
  FnDialog,
  FnEmptyState,
  FnSectionCard,
  FnSkeleton,
  FnSkeletonGroup,
  useToast,
} from "@kame/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const fmt = useFormat();
const qc = useQueryClient();
const sessions = useQuery(queries.listSessionsApiV1MeSessionsGetOptions());
const revoke = useMutation(queries.revokeSessionApiV1MeSessionsSessionIdDeleteMutation());
const pending = ref<string | null>(null);

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
function ip(value: string | null | undefined) {
  if (!value) return null;
  const v4 = value.startsWith("::ffff:") ? value.slice(7) : value;
  return v4 === "127.0.0.1" || v4 === "::1" ? t("sessions.thisNetwork") : v4;
}

async function onRevoke(id: string) {
  try {
    await revoke.mutateAsync({ path: { session_id: id } });
    pending.value = null;
    toast.push({ title: t("sessions.revoked"), tone: "success" });
    await qc.invalidateQueries();
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}
</script>

<template>
  <section class="flex max-w-2xl flex-col gap-6">
    <PageHeader :title="t('settings.sessions')" :lede="t('sessions.lede')" />

    <FnSkeletonGroup v-if="sessions.isPending.value" :label="t('common.loading')">
      <SkeletonSectionCard headed :intro="false">
        <ul class="flex flex-col divide-y divide-rule">
          <li v-for="n in 2" :key="n" class="flex min-h-16 flex-wrap items-center gap-3 py-2">
            <div class="flex min-w-0 flex-1 flex-col gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <FnSkeleton class="h-4 w-40" />
                <FnSkeleton class="h-6 w-20 rounded-full" />
              </div>
              <FnSkeleton class="h-3.5 w-3/5" />
            </div>
            <FnSkeleton class="h-11 w-24 rounded-md" />
          </li>
        </ul>
      </SkeletonSectionCard>
    </FnSkeletonGroup>

    <FnEmptyState
      v-else-if="sessions.isError.value"
      :title="t('sessions.loadError')"
      :body="apiError(sessions.error.value)"
      tone="danger"
    >
      <FnButton size="sm" @click="sessions.refetch()">{{ t("common.retry") }}</FnButton>
    </FnEmptyState>

    <FnEmptyState v-else-if="!sessions.data.value?.length" :title="t('sessions.empty')" />

    <FnSectionCard v-else :title="t('sessions.cardTitle')">
      <ul class="flex flex-col divide-y divide-rule">
        <li
          v-for="s in sessions.data.value"
          :key="s.id"
          class="flex min-h-16 flex-wrap items-center gap-3 py-2"
        >
          <div class="min-w-0 flex-1">
            <p class="flex flex-wrap items-center gap-2 font-medium text-ink-900">
              {{ device(s.user_agent) }}
              <FnChip v-if="s.current" tone="accent">{{ t("sessions.current") }}</FnChip>
            </p>
            <p class="text-sm text-ink-600">
              <span v-if="ip(s.ip)">{{ ip(s.ip) }} · </span
              >{{ t("sessions.lastUsed", { when: fmt.dateTime(s.last_used_at) }) }}
            </p>
          </div>
          <FnButton
            v-if="!s.current"
            size="sm"
            tone="ghost"
            :loading="revoke.isPending.value && revoke.variables.value?.path.session_id === s.id"
            @click="pending = s.id"
            >{{ t("sessions.revoke") }}</FnButton
          >
        </li>
      </ul>
    </FnSectionCard>

    <FnDialog
      :open="!!pending"
      :title="t('sessions.revokeTitle')"
      :description="t('sessions.revokeBody')"
      :close-label="t('common.close')"
      @update:open="(v) => !v && (pending = null)"
    >
      <div class="flex justify-end gap-2">
        <FnButton @click="pending = null">{{ t("common.cancel") }}</FnButton>
        <FnButton
          tone="danger"
          :loading="revoke.isPending.value"
          @click="pending && onRevoke(pending)"
          >{{ t("sessions.revoke") }}</FnButton
        >
      </div>
    </FnDialog>
  </section>
</template>
