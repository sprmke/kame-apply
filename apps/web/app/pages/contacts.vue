<script setup lang="ts">
import { client, parseContactsApiV1ContactsParsePost } from "@kame/api-client";
import {
  FnButton,
  FnEmptyState,
  FnField,
  FnSectionCard,
  FnSkeleton,
  FnSkeletonGroup,
  FnTextarea,
  useToast,
} from "@kame/ui";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

type Contact = {
  id: string;
  name: string;
  email: string;
  company: string;
  title: string;
};

type Draft = { name: string; email: string; company: string; title: string };

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const raw = ref("");
const importing = ref(false);

const contacts = useQuery({
  queryKey: computed(() => ["contacts", ws.currentId]),
  queryFn: async () => {
    const { data } = await client.get({ url: "/api/v1/contacts", throwOnError: true });
    return data as Contact[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

function titleCase(value: string): string {
  return value
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w[0]!.toUpperCase() + w.slice(1))
    .join(" ");
}

function companyFromEmail(email: string): string {
  const host = email.split("@")[1] ?? "";
  const base = host.split(".")[0] ?? "";
  if (!base || ["gmail", "outlook", "yahoo", "hotmail", "icloud"].includes(base)) return "";
  return titleCase(base.replace(/[-_]/g, " "));
}

function parseCsvLine(line: string): string[] {
  return line.split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
}

/** One parser for signatures, LinkedIn text, vCards, and CSV. No AI, no column header required. */
function parseInput(text: string): Draft[] {
  const trimmed = text.trim();
  if (!trimmed) return [];

  // vCard
  if (/BEGIN:VCARD/i.test(trimmed)) {
    return trimmed
      .split(/END:VCARD/i)
      .map((card) => {
        const email = card.match(/EMAIL[^:]*:(\S+)/i)?.[1] ?? "";
        const name =
          card.match(/FN:(.+)/i)?.[1]?.trim() ??
          [card.match(/N:([^;\n]*);([^;\n]*)/i)?.[2], card.match(/N:([^;\n]*);([^;\n]*)/i)?.[1]]
            .filter(Boolean)
            .join(" ") ??
          "";
        const org = card.match(/ORG:(.+)/i)?.[1]?.trim() ?? "";
        const title = card.match(/TITLE:(.+)/i)?.[1]?.trim() ?? "";
        return { name: name || email.split("@")[0] || "Unknown", email, company: org, title };
      })
      .filter((c) => c.email || c.name);
  }

  const lines = trimmed
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  // CSV with or without a header
  if (lines.length && lines.filter((l) => l.includes(",")).length >= Math.min(2, lines.length)) {
    const first = parseCsvLine(lines[0]!);
    const hasHeader = first.some((h) => /^(name|email|e-mail|company|title|role)$/i.test(h));
    const header = hasHeader ? first.map((h) => h.toLowerCase()) : [];
    const rows = hasHeader ? lines.slice(1) : lines;
    const idx = (names: string[], fallback: number) => {
      const i = header.findIndex((h) => names.includes(h));
      return i >= 0 ? i : fallback;
    };
    const ni = idx(["name", "full name"], 0);
    const ei = idx(["email", "e-mail"], 1);
    const ci = idx(["company", "organisation", "organization"], 2);
    const ti = idx(["title", "role", "position"], 3);
    return rows
      .map((line) => {
        const cols = parseCsvLine(line);
        return {
          name: cols[ni] || "Unknown",
          email: cols[ei] || "",
          company: cols[ci] || "",
          title: cols[ti] || "",
        };
      })
      .filter((c) => c.email || c.name !== "Unknown");
  }

  // Free text: pair each email with the nearest name line and a role line nearby.
  const emails = [...trimmed.matchAll(/[\w.+-]+@[\w-]+\.[\w.]+/g)].map((m) => m[0]);
  if (!emails.length) {
    const nameLine = lines.find((l) => /^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}$/.test(l));
    return nameLine ? [{ name: nameLine, email: "", company: "", title: "" }] : [];
  }

  return emails.map((email) => {
    const at = trimmed.indexOf(email);
    const before = trimmed
      .slice(0, at)
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean)
      .slice(-4);
    const nameLine = [...before]
      .reverse()
      .find((l) => /^[A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){1,3}$/.test(l));
    const roleLine = before.find((l) => / at |@|\||,/.test(l) && l !== nameLine);
    const company =
      roleLine
        ?.match(/\bat\s+(.+)$/i)?.[1]
        ?.trim()
        .replace(/[|,].*$/, "") ?? companyFromEmail(email);
    const title = roleLine ? (roleLine.split(/\bat\b|\||,/)[0] ?? "").trim() : "";
    return {
      name: nameLine || titleCase(email.split("@")[0]!.replace(/[._-]/g, " ")),
      email,
      company,
      title,
    };
  });
}

const drafts = ref<Draft[]>([]);
const aiBusy = ref(false);

watch(
  raw,
  (value) => {
    drafts.value = parseInput(value);
  },
  { immediate: true },
);

async function readWithAi() {
  if (!raw.value.trim()) return;
  aiBusy.value = true;
  try {
    const { data } = await parseContactsApiV1ContactsParsePost({
      body: { text: raw.value },
      throwOnError: true,
    });
    drafts.value = (data?.items ?? []).map((item) => ({
      name: item.name || "Unknown",
      email: item.email || "",
      company: item.company || "",
      title: item.title || "",
    }));
    if (data?.source === "defaults") {
      toast.push({ title: t("contacts.aiFallback"), tone: "neutral" });
    }
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    aiBusy.value = false;
  }
}

async function importContacts() {
  if (!drafts.value.length) return;
  importing.value = true;
  try {
    await client.post({
      url: "/api/v1/contacts/import",
      body: { contacts: drafts.value.map((c) => ({ ...c, source: "paste" })) },
      throwOnError: true,
    });
    raw.value = "";
    await qc.invalidateQueries({ queryKey: ["contacts", ws.currentId] });
    toast.push({ title: t("contacts.pasted"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    importing.value = false;
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-5">
    <PageHeader :title="t('contacts.title')" :lede="t('contacts.lede')" />

    <FnSectionCard :title="t('contacts.pasteTitle')" :intro="t('contacts.pasteIntro')">
      <FnField v-slot="{ id }" :label="t('contacts.pasteLabel')">
        <FnTextarea :id="id" v-model="raw" :rows="6" :placeholder="t('contacts.csvPlaceholder')" />
      </FnField>

      <div v-if="raw.trim()" class="flex flex-col gap-2">
        <p class="text-sm font-semibold text-ink-900">
          {{ t("contacts.preview", { n: drafts.length }, drafts.length) }}
        </p>
        <p v-if="!drafts.length" class="text-sm text-ink-600">{{ t("contacts.nothingFound") }}</p>
        <ul v-else class="divide-y divide-rule rounded-lg border border-rule">
          <li
            v-for="(d, i) in drafts.slice(0, 6)"
            :key="`${d.email}-${i}`"
            class="px-3 py-2 text-sm"
          >
            <p class="font-medium text-ink-900">{{ d.name }}</p>
            <p class="text-ink-600">
              {{ [d.title, d.company, d.email].filter(Boolean).join(" · ") }}
            </p>
          </li>
        </ul>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <FnButton
          tone="primary"
          :disabled="importing || !drafts.length"
          :loading="importing"
          @click="importContacts"
          >{{ t("contacts.import") }}</FnButton
        >
        <FnButton
          tone="quiet"
          :disabled="aiBusy || !raw.trim()"
          :loading="aiBusy"
          @click="readWithAi"
          >{{ t("contacts.readWithAi") }}</FnButton
        >
      </div>
    </FnSectionCard>

    <FnSkeletonGroup v-if="contacts.isPending.value" :label="t('common.loading')">
      <ul
        class="divide-y divide-rule overflow-hidden rounded-xl border border-rule bg-paper-1 shadow-[var(--shadow-card)]"
      >
        <li v-for="n in 4" :key="n" class="flex flex-col gap-2 px-4 py-3">
          <FnSkeleton class="h-4 w-2/5" />
          <FnSkeleton class="h-3.5 w-3/5" />
        </li>
      </ul>
    </FnSkeletonGroup>
    <FnEmptyState v-else-if="!(contacts.data.value ?? []).length" :title="t('contacts.empty')" />
    <ul
      v-else
      class="divide-y divide-rule overflow-hidden rounded-xl border border-rule bg-paper-1 shadow-[var(--shadow-card)]"
    >
      <li v-for="c in contacts.data.value ?? []" :key="c.id" class="px-4 py-3">
        <p class="font-medium text-ink-900">{{ c.name }}</p>
        <p class="text-sm text-ink-600">
          {{ [c.title, c.company, c.email].filter(Boolean).join(" · ") }}
        </p>
      </li>
    </ul>
  </div>
</template>
