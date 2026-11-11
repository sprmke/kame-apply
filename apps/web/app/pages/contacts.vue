<script setup lang="ts">
import { client } from "@kame/api-client";
import { FnButton, FnSkeleton, FnTextarea, useToast } from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

type Contact = {
  id: string;
  name: string;
  email: string;
  company: string;
  title: string;
};

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const csv = ref("");
const importing = ref(false);

const contacts = useQuery({
  queryKey: computed(() => ["contacts", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({ url: "/api/v1/contacts", throwOnError: true });
    return data as Contact[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

function parseCsv(text: string): Array<{
  name: string;
  email: string;
  company: string;
  title: string;
}> {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (!lines.length) return [];
  const header = lines[0]!
    .toLowerCase()
    .split(",")
    .map((h) => h.trim());
  const hasHeader = header.includes("name") || header.includes("email");
  const rows = hasHeader ? lines.slice(1) : lines;
  const idx = (key: string, fallback: number) => {
    const i = header.indexOf(key);
    return i >= 0 ? i : fallback;
  };
  const nameI = hasHeader ? idx("name", 0) : 0;
  const emailI = hasHeader ? idx("email", 1) : 1;
  const companyI = hasHeader ? idx("company", 2) : 2;
  const titleI = hasHeader ? idx("title", 3) : 3;
  return rows.map((line) => {
    const cols = line.split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
    return {
      name: cols[nameI] || "Unknown",
      email: cols[emailI] || "",
      company: cols[companyI] || "",
      title: cols[titleI] || "",
    };
  });
}

async function importCsv() {
  const items = parseCsv(csv.value);
  if (!items.length) return;
  importing.value = true;
  try {
    await client.post({
      url: "/api/v1/contacts/import",
      body: { contacts: items.map((c) => ({ ...c, source: "csv" })) },
      throwOnError: true,
    });
    csv.value = "";
    await qc.invalidateQueries({ queryKey: ["contacts", ws.currentId] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    importing.value = false;
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-8">
    <div class="flex flex-col gap-1">
      <h1 class="text-3xl font-bold tracking-[-0.03em] text-ink-900">{{ t("contacts.title") }}</h1>
      <p class="max-w-2xl text-sm leading-6 text-ink-600">{{ t("contacts.lede") }}</p>
    </div>

    <section
      class="flex flex-col gap-3 rounded-xl border border-rule bg-paper-1 p-6 shadow-[var(--shadow-card)]"
    >
      <FnTextarea
        v-model="csv"
        :rows="5"
        :placeholder="t('contacts.csvPlaceholder')"
        :aria-label="t('contacts.csvPlaceholder')"
      />
      <FnButton
        class="self-start"
        tone="primary"
        :disabled="importing || !csv.trim()"
        @click="importCsv"
        >{{ t("contacts.import") }}</FnButton
      >
    </section>

    <div v-if="contacts.isPending.value"><FnSkeleton class="h-24 w-full" /></div>
    <ul
      v-else
      class="divide-y divide-rule overflow-hidden rounded-xl border border-rule bg-paper-1 shadow-[var(--shadow-card)]"
    >
      <li v-for="c in contacts.data.value ?? []" :key="c.id" class="px-5 py-4">
        <p class="font-medium text-ink-900">{{ c.name }}</p>
        <p class="text-sm text-ink-600">
          {{ [c.title, c.company, c.email].filter(Boolean).join(" · ") }}
        </p>
      </li>
      <li v-if="!(contacts.data.value ?? []).length" class="px-5 py-8 text-sm text-ink-600">
        {{ t("contacts.empty") }}
      </li>
    </ul>
  </div>
</template>
