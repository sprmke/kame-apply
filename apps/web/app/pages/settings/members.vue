<script setup lang="ts">
import { queries, schemas, type MemberRead } from "@kame/api-client";
import {
  FnButton,
  FnChip,
  FnDialog,
  FnField,
  FnInput,
  FnMenu,
  FnSelect,
  FnSkeleton,
  FnTable,
  useToast,
} from "@kame/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useAuthStore } from "~/stores/auth";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const ws = useWorkspaceStore();
const auth = useAuthStore();
const toast = useToast();
const apiError = useApiError();
const fmt = useFormat();
const qc = useQueryClient();

const RANK: Record<string, number> = { viewer: 0, member: 1, admin: 2, owner: 3 };
const myRank = computed(() => RANK[ws.role ?? "viewer"] ?? 0);
const manageable = (m: MemberRead) =>
  ws.canManage && m.user_id !== auth.user?.id && (RANK[m.role] ?? 0) < myRank.value;
const assignable = computed(() =>
  (["admin", "member", "viewer"] as const)
    .filter((r) => RANK[r]! < myRank.value)
    .map((r) => ({ value: r, label: t(`role.${r}`) })),
);

const members = useQuery(queries.listMembersApiV1WorkspaceMembersGetOptions());
const invites = useQuery({
  ...queries.listInvitationsApiV1WorkspaceInvitationsGetOptions(),
  enabled: computed(() => ws.canManage),
});
const limits = useQuery(queries.getLimitsApiV1WorkspaceLimitsGetOptions());

const refreshAll = () => qc.invalidateQueries();
const changeRole = useMutation(queries.changeMemberRoleApiV1WorkspaceMembersUserIdPatchMutation());
const removeMember = useMutation(queries.removeMemberApiV1WorkspaceMembersUserIdDeleteMutation());
const createInvite = useMutation(queries.createInvitationApiV1WorkspaceInvitationsPostMutation());
const revokeInvite = useMutation(
  queries.revokeInvitationApiV1WorkspaceInvitationsInvitationIdDeleteMutation(),
);

async function onRole(m: MemberRead, role: "admin" | "member" | "viewer") {
  try {
    await changeRole.mutateAsync({ path: { user_id: m.user_id }, body: { role } });
    toast.push({ title: t("common.saved"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
  await refreshAll();
}

const removing = ref<MemberRead | null>(null);
const removeOpen = computed({
  get: () => !!removing.value,
  set: (v) => !v && (removing.value = null),
});
async function confirmRemove() {
  if (!removing.value) return;
  try {
    await removeMember.mutateAsync({ path: { user_id: removing.value.user_id } });
    toast.push({ title: t("members.removed"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
  removing.value = null;
  await refreshAll();
}

const inviteOpen = ref(false);
const { form, err } = useZodForm(schemas.zInvitationCreate, { email: "", role: "member" });
const [email, emailAttrs] = form.defineField("email");
const [role] = form.defineField("role");
const inviteError = ref<string | null>(null);
watch(inviteOpen, (o) => {
  if (o) {
    form.resetForm({ values: { email: "", role: "member" } });
    inviteError.value = null;
  }
});
const submitInvite = form.handleSubmit(async (v) => {
  inviteError.value = null;
  try {
    await createInvite.mutateAsync({ body: { email: v.email, role: v.role } });
    inviteOpen.value = false;
    toast.push({ title: t("members.invited"), tone: "success" });
    await refreshAll();
  } catch (e) {
    inviteError.value = apiError(e);
  }
});
async function onRevoke(id: string) {
  await revokeInvite.mutateAsync({ path: { invitation_id: id } });
  await refreshAll();
}

const columns = computed(() => [
  { key: "who", label: t("members.member") },
  { key: "role", label: t("members.role") },
  { key: "joined", label: t("members.joined") },
  { key: "actions", label: "" },
]);
const rows = computed(() =>
  (members.data.value ?? []).map((m) => ({
    ...m,
    id: m.user_id,
    who: m.name || m.email,
    joined: fmt.date(m.joined_at),
  })),
);
</script>

<template>
  <section class="flex flex-col gap-6">
    <PageHeader :title="t('settings.members')">
      <template #actions>
        <FnButton v-if="ws.canManage" tone="primary" @click="inviteOpen = true">{{
          t("members.invite")
        }}</FnButton>
      </template>
    </PageHeader>
    <p v-if="limits.data.value" class="text-sm text-ink-600">
      {{
        t("members.seats", {
          used: limits.data.value.members_used,
          max: limits.data.value.max_members,
        })
      }}
    </p>

    <FnSkeleton v-if="members.isPending.value" :lines="4" />
    <p v-else-if="members.isError.value" role="alert" class="text-sm text-oxblood-600">
      {{ apiError(members.error.value) }}
    </p>
    <FnTable
      v-else
      :columns="columns"
      :rows="rows"
      row-key="id"
      :caption="t('settings.members')"
      :empty="t('members.empty')"
    >
      <template #cell-who="{ row }">
        <div class="flex flex-col py-1">
          <span class="font-medium">{{ row.who }}</span>
          <span v-if="row.name" class="text-xs text-ink-600">{{ row.email }}</span>
        </div>
      </template>
      <template #cell-role="{ row }">
        <FnSelect
          v-if="manageable(row)"
          :model-value="row.role"
          :options="assignable"
          class="max-w-36"
          @update:model-value="(v) => v && onRole(row, v as 'admin' | 'member' | 'viewer')"
        />
        <FnChip v-else>{{ t(`role.${row.role}`) }}</FnChip>
      </template>
      <template #cell-actions="{ row }">
        <FnMenu
          v-if="manageable(row)"
          :items="[
            { label: t('members.remove'), tone: 'danger', onSelect: () => (removing = row) },
          ]"
        >
          <FnButton tone="ghost" size="sm" :aria-label="t('members.actionsFor', { name: row.who })"
            ><NavIcon name="ph:dots-three"
          /></FnButton>
        </FnMenu>
      </template>
    </FnTable>

    <div v-if="ws.canManage && (invites.data.value?.length ?? 0) > 0" class="flex flex-col gap-2">
      <h2 class="font-serif text-lg font-semibold">{{ t("members.pending") }}</h2>
      <ul class="flex flex-col divide-y divide-rule border-y border-rule">
        <li
          v-for="i in invites.data.value"
          :key="i.id"
          class="flex min-h-12 flex-wrap items-center gap-3 py-1"
        >
          <span class="min-w-0 flex-1 truncate">{{ i.email }}</span>
          <FnChip>{{ t(`role.${i.role}`) }}</FnChip>
          <span class="text-xs text-ink-600">{{
            t("members.expires", { date: fmt.date(i.expires_at) })
          }}</span>
          <FnButton size="sm" tone="ghost" @click="onRevoke(i.id)">{{
            t("members.revoke")
          }}</FnButton>
        </li>
      </ul>
    </div>

    <FnDialog
      v-model:open="inviteOpen"
      :title="t('members.invite')"
      :close-label="t('common.close')"
    >
      <form class="flex flex-col gap-4" novalidate @submit.prevent="submitInvite">
        <p v-if="inviteError" role="alert" class="text-sm text-oxblood-600">{{ inviteError }}</p>
        <FnField
          v-slot="{ id, describedby, invalid }"
          :label="t('auth.email')"
          :error="err('email')"
        >
          <FnInput
            :id="id"
            v-model="email"
            v-bind="emailAttrs"
            type="email"
            inputmode="email"
            autocomplete="off"
            :describedby="describedby"
            :invalid="invalid"
          />
        </FnField>
        <FnField v-slot="{ id }" :label="t('members.role')">
          <FnSelect :id="id" v-model="role" :options="assignable" />
        </FnField>
        <div class="flex justify-end gap-2">
          <FnButton @click="inviteOpen = false">{{ t("common.cancel") }}</FnButton>
          <FnButton type="submit" tone="primary" :loading="createInvite.isPending.value">{{
            t("members.sendInvite")
          }}</FnButton>
        </div>
      </form>
    </FnDialog>

    <FnDialog
      v-model:open="removeOpen"
      :title="t('members.removeTitle')"
      :description="t('members.removeBody', { name: removing?.name || removing?.email })"
      :close-label="t('common.close')"
    >
      <div class="flex justify-end gap-2">
        <FnButton @click="removing = null">{{ t("common.cancel") }}</FnButton>
        <FnButton tone="danger" :loading="removeMember.isPending.value" @click="confirmRemove">{{
          t("members.remove")
        }}</FnButton>
      </div>
    </FnDialog>
  </section>
</template>
