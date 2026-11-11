<script setup lang="ts">
import {
  applyChangesApiV1ResumesVersionIdApplyPost,
  bulkDecideApiV1ResumesVersionIdChangesBulkPost,
  computeInsightsApiV1TracksTrackIdInsightsPost,
  createResumeApiV1ResumesPost,
  critiqueResumeApiV1ResumesVersionIdCritiquePost,
  decideChangeApiV1ResumeChangesChangeIdPost,
  getInsightsApiV1TracksTrackIdInsightsGet,
  parseViewApiV1ResumesVersionIdParseViewGet,
  improveResumeApiV1ResumesVersionIdImprovePost,
  listChangesApiV1ResumesVersionIdChangesGet,
  listProfilesApiV1ProfilesGet,
  listResumesApiV1ResumesGet,
  listTracksApiV1TracksGet,
  renderResumeApiV1ResumesVersionIdRenderPost,
  type ChangeRead,
  type CritiqueRead,
  type InsightsRead,
  type ParseViewRead,
  type ResumeVersionRead,
} from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton, useToast } from "@kame/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const qc = useQueryClient();
const route = useRoute();
const router = useRouter();

type Tab = "critique" | "diff" | "insights" | "skim" | "parse";

const tab = ref<Tab>("critique");
const trackId = computed(() => (route.query.track as string) || "");
const selectedId = ref<string | null>(null);
const template = ref("classic");
const pageSize = ref<"letter" | "a4">("letter");
const renderUrls = ref<{ pdf?: string | null; docx?: string | null; txt?: string | null }>({});
const parseGate = ref<Record<string, unknown> | null>(null);

const tracks = useQuery({
  queryKey: computed(() => ["tracks", ws.currentId]),
  queryFn: async () => {
    const { data } = await listTracksApiV1TracksGet({ throwOnError: true });
    return data ?? [];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const profiles = useQuery({
  queryKey: computed(() => ["profiles", ws.currentId]),
  queryFn: async () => {
    const { data } = await listProfilesApiV1ProfilesGet({ throwOnError: true });
    return data ?? [];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

const resumes = useQuery({
  queryKey: computed(() => ["resumes", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await listResumesApiV1ResumesGet({
      query: trackId.value ? { track_id: trackId.value } : {},
      throwOnError: true,
    });
    return (data ?? []) as ResumeVersionRead[];
  },
  enabled: computed(() => Boolean(ws.currentId)),
});

watch(
  () => resumes.data.value,
  (rows) => {
    if (!rows?.length) {
      selectedId.value = null;
      return;
    }
    const first = rows[0];
    if (first && (!selectedId.value || !rows.some((r) => String(r.id) === selectedId.value))) {
      selectedId.value = String(first.id);
    }
  },
  { immediate: true },
);

const selected = computed(
  () => resumes.data.value?.find((r) => String(r.id) === selectedId.value) ?? null,
);

const critiqueQ = useQuery({
  queryKey: computed(() => ["resume-critique", selectedId.value]),
  queryFn: async () => {
    const c = selected.value?.critique as CritiqueRead | undefined;
    return c && Object.keys(c).length ? c : null;
  },
  enabled: computed(() => Boolean(selectedId.value)),
});

const changesQ = useQuery({
  queryKey: computed(() => ["resume-changes", selectedId.value]),
  queryFn: async () => {
    const { data } = await listChangesApiV1ResumesVersionIdChangesGet({
      path: { version_id: selectedId.value! },
      throwOnError: true,
    });
    return (data ?? []) as ChangeRead[];
  },
  enabled: computed(() => Boolean(selectedId.value)),
});

const insightsQ = useQuery({
  queryKey: computed(() => ["track-insights", trackId.value]),
  queryFn: async () => {
    const { data } = await getInsightsApiV1TracksTrackIdInsightsGet({
      path: { track_id: trackId.value },
      query: { window_days: 30 },
      throwOnError: true,
    });
    return data as InsightsRead;
  },
  enabled: computed(() => Boolean(trackId.value) && tab.value === "insights"),
});

const parseQ = useQuery({
  queryKey: computed(() => ["resume-parse", selectedId.value]),
  queryFn: async () => {
    const { data } = await parseViewApiV1ResumesVersionIdParseViewGet({
      path: { version_id: selectedId.value! },
      throwOnError: true,
    });
    return data as ParseViewRead;
  },
  enabled: computed(() => Boolean(selectedId.value) && tab.value === "parse"),
});

function setTrack(id: string) {
  router.replace({ query: { ...route.query, track: id || undefined } });
}

const createMut = useMutation({
  mutationFn: async () => {
    const tid = trackId.value;
    const track = tracks.data.value?.find((tr) => String(tr.id) === tid);
    const profileId = track?.profile_id || profiles.data.value?.[0]?.id;
    if (!profileId) throw new Error("No profile");
    const { data } = await createResumeApiV1ResumesPost({
      body: {
        profile_id: String(profileId),
        track_id: tid || null,
        label: track?.name || "Base resume",
        template: template.value,
        page_size: pageSize.value,
      },
      throwOnError: true,
    });
    return data as ResumeVersionRead;
  },
  onSuccess: async (data) => {
    selectedId.value = String(data.id);
    await qc.invalidateQueries({ queryKey: ["resumes"] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const critiqueMut = useMutation({
  mutationFn: async () => {
    const { data } = await critiqueResumeApiV1ResumesVersionIdCritiquePost({
      path: { version_id: selectedId.value! },
      throwOnError: true,
    });
    return data as CritiqueRead;
  },
  onSuccess: async () => {
    tab.value = "critique";
    await qc.invalidateQueries({ queryKey: ["resumes"] });
    await qc.invalidateQueries({ queryKey: ["resume-critique"] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const improveMut = useMutation({
  mutationFn: async () => {
    const { data } = await improveResumeApiV1ResumesVersionIdImprovePost({
      path: { version_id: selectedId.value! },
      body: { window_days: 30 },
      throwOnError: true,
    });
    return data;
  },
  onSuccess: async () => {
    tab.value = "diff";
    await qc.invalidateQueries({ queryKey: ["resume-changes"] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const insightsMut = useMutation({
  mutationFn: async () => {
    const { data } = await computeInsightsApiV1TracksTrackIdInsightsPost({
      path: { track_id: trackId.value },
      query: { window_days: 30 },
      throwOnError: true,
    });
    return data;
  },
  onSuccess: async () => {
    tab.value = "insights";
    await qc.invalidateQueries({ queryKey: ["track-insights"] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

const renderMut = useMutation({
  mutationFn: async () => {
    const { data } = await renderResumeApiV1ResumesVersionIdRenderPost({
      path: { version_id: selectedId.value! },
      body: { template: template.value, page_size: pageSize.value },
      throwOnError: true,
    });
    return data;
  },
  onSuccess: async (data) => {
    renderUrls.value = {
      pdf: data?.pdf_url,
      docx: data?.docx_url,
      txt: data?.txt_url,
    };
    parseGate.value = (data?.parse_gate as Record<string, unknown>) || null;
    await qc.invalidateQueries({ queryKey: ["resumes"] });
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

async function decide(changeId: string, status: "accepted" | "rejected") {
  try {
    await decideChangeApiV1ResumeChangesChangeIdPost({
      path: { change_id: changeId },
      body: { status },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["resume-changes"] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function bulk(status: "accepted" | "rejected") {
  try {
    await bulkDecideApiV1ResumesVersionIdChangesBulkPost({
      path: { version_id: selectedId.value! },
      body: { status },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["resume-changes"] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

async function applyAccepted() {
  try {
    await applyChangesApiV1ResumesVersionIdApplyPost({
      path: { version_id: selectedId.value! },
      throwOnError: true,
    });
    await qc.invalidateQueries({ queryKey: ["resumes", "resume-changes"] });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
}

const critique = computed(() => {
  const live = critiqueMut.data.value;
  if (live) return live;
  return (selected.value?.critique as CritiqueRead | undefined) || critiqueQ.data.value;
});

const skim = computed(() => {
  const c = critique.value as CritiqueRead | null | undefined;
  return (c?.skim_zone as { summary?: string; first_role?: string } | undefined) || null;
});

const activeInsights = computed(
  () => (insightsMut.data.value || insightsQ.data.value || null) as InsightsRead | null,
);

const insightSkills = computed(() => {
  const raw = (activeInsights.value?.skills || []) as Array<{
    name: string;
    frequency: number;
    status: string;
  }>;
  return raw;
});

const insightTitles = computed(() => {
  const raw = (activeInsights.value?.titles || []) as Array<{ title?: string; count?: number }>;
  return raw.slice(0, 8).map((ti) => ({ title: ti.title || "", count: ti.count || 0 }));
});

function skillTone(status: string): "neutral" | "accent" | "pencil" {
  if (status === "have_shown") return "accent";
  if (status === "have_not_shown") return "pencil";
  return "neutral";
}

const contentPreview = computed(() => {
  const c = selected.value?.content as Record<string, unknown> | undefined;
  if (!c) return "";
  const contact = (c.contact || {}) as { full_name?: string; email?: string; location?: string };
  const summary = (c.summary as { text?: string } | undefined)?.text || "";
  const sections =
    (c.sections as Array<{
      heading?: string;
      lines?: { text: string }[];
      items?: { title?: string; subtitle?: string; lines?: { text: string }[] }[];
    }>) || [];
  const parts = [
    contact.full_name || "",
    [contact.email, contact.location].filter(Boolean).join(" · "),
  ];
  if (summary) parts.push("", summary);
  for (const sec of sections) {
    parts.push("", (sec.heading || "").toUpperCase());
    for (const line of sec.lines || []) parts.push(`• ${line.text}`);
    for (const item of sec.items || []) {
      parts.push([item.title, item.subtitle].filter(Boolean).join(", "));
      for (const line of item.lines || []) parts.push(`• ${line.text}`);
    }
  }
  return parts.filter((p) => p !== undefined).join("\n");
});
</script>

<template>
  <div class="mx-auto flex max-w-6xl flex-col gap-4 p-4 md:p-6">
    <header class="flex flex-wrap items-center gap-2">
      <h1 class="font-display text-xl text-ink-900">{{ t("nav.studio") }}</h1>
      <label class="sr-only" for="studio-track">Search</label>
      <select
        id="studio-track"
        class="border border-ink-200 bg-paper px-2 py-1 text-sm text-ink-900"
        :value="trackId"
        @change="setTrack(($event.target as HTMLSelectElement).value)"
      >
        <option value="">All searches</option>
        <option v-for="tr in tracks.data.value || []" :key="String(tr.id)" :value="String(tr.id)">
          {{ tr.name }}
        </option>
      </select>
      <div class="ml-auto flex flex-wrap gap-1">
        <FnButton
          size="sm"
          :tone="(resumes.data.value || []).length ? 'ghost' : 'primary'"
          :disabled="createMut.isPending.value"
          @click="createMut.mutate()"
        >
          New resume
        </FnButton>
        <FnButton
          size="sm"
          tone="ghost"
          :disabled="!selectedId || critiqueMut.isPending.value"
          @click="critiqueMut.mutate()"
        >
          Critique
        </FnButton>
        <FnButton
          size="sm"
          tone="ghost"
          :disabled="!selectedId || improveMut.isPending.value"
          @click="improveMut.mutate()"
        >
          Improve
        </FnButton>
        <FnButton
          size="sm"
          tone="ghost"
          :disabled="!trackId || insightsMut.isPending.value"
          @click="insightsMut.mutate()"
        >
          Insights
        </FnButton>
        <FnButton
          size="sm"
          :tone="selectedId ? 'primary' : 'ghost'"
          :disabled="!selectedId || renderMut.isPending.value"
          @click="renderMut.mutate()"
        >
          Render
        </FnButton>
      </div>
    </header>

    <div class="flex flex-wrap gap-1 border-b border-ink-100 pb-2">
      <FnButton
        v-for="item in [
          ['critique', 'Critique'],
          ['diff', 'Diff'],
          ['insights', 'Insights'],
          ['skim', 'Skim'],
          ['parse', 'Parse'],
        ] as const"
        :key="item[0]"
        size="sm"
        :tone="tab === item[0] ? 'primary' : 'ghost'"
        @click="tab = item[0]"
      >
        {{ item[1] }}
      </FnButton>
    </div>

    <div class="grid gap-4 lg:grid-cols-[220px_1fr]">
      <aside class="flex flex-col gap-2">
        <div v-if="resumes.isPending.value" class="space-y-2">
          <FnSkeleton class="h-10" />
          <FnSkeleton class="h-10" />
        </div>
        <div v-else-if="!(resumes.data.value || []).length" class="flex flex-col items-start gap-2">
          <p class="text-sm text-ink-600">No resumes yet.</p>
          <FnButton
            size="sm"
            tone="primary"
            :disabled="createMut.isPending.value"
            @click="createMut.mutate()"
          >
            Create a resume
          </FnButton>
        </div>
        <ul v-else class="divide-y divide-ink-100 border border-ink-100">
          <li v-for="row in resumes.data.value" :key="String(row.id)">
            <button
              type="button"
              class="w-full px-3 py-2 text-left text-sm"
              :class="
                String(row.id) === selectedId
                  ? 'bg-persimmon-50 text-ink-900'
                  : 'text-ink-700 hover:bg-ink-50'
              "
              @click="selectedId = String(row.id)"
            >
              <span class="block truncate font-medium">{{ row.label || "Resume" }}</span>
              <span class="text-xs text-ink-500">{{ row.template }} · {{ row.page_size }}</span>
            </button>
          </li>
        </ul>
        <div class="flex flex-col gap-2 border border-ink-100 p-2 text-sm">
          <label class="flex flex-col gap-1">
            Template
            <select v-model="template" class="border border-ink-200 bg-paper px-2 py-1">
              <option value="classic">Classic</option>
              <option value="compact">Compact</option>
              <option value="modern">Modern</option>
              <option value="serif">Serif</option>
            </select>
          </label>
          <label class="flex flex-col gap-1">
            Page
            <select v-model="pageSize" class="border border-ink-200 bg-paper px-2 py-1">
              <option value="letter">Letter</option>
              <option value="a4">A4</option>
            </select>
          </label>
          <div v-if="parseGate" class="text-xs text-ink-600">
            Parse gate: {{ parseGate.ok ? "pass" : "fail" }}
          </div>
          <div v-if="renderUrls.pdf || renderUrls.docx" class="flex flex-col gap-1">
            <a
              v-if="renderUrls.pdf"
              class="text-persimmon-700 underline"
              :href="renderUrls.pdf"
              target="_blank"
              rel="noopener"
              >PDF</a
            >
            <a
              v-if="renderUrls.docx"
              class="text-persimmon-700 underline"
              :href="renderUrls.docx"
              target="_blank"
              rel="noopener"
              >DOCX</a
            >
            <a
              v-if="renderUrls.txt"
              class="text-persimmon-700 underline"
              :href="renderUrls.txt"
              target="_blank"
              rel="noopener"
              >Text</a
            >
          </div>
        </div>
      </aside>

      <section class="min-w-0">
        <div v-if="!selected" class="text-sm text-ink-600">Select or create a base resume</div>

        <div v-else-if="tab === 'critique'" class="flex flex-col gap-3">
          <div
            v-if="!critique || !Object.keys(critique.categories || {}).length"
            class="text-sm text-ink-600"
          >
            Run Critique
          </div>
          <template v-else>
            <ul class="grid gap-2 sm:grid-cols-2">
              <li
                v-for="(cat, key) in critique.categories"
                :key="String(key)"
                class="border border-ink-100 px-3 py-2 text-sm"
              >
                <span class="font-medium capitalize">{{ key }}</span>
                <span class="ml-2 text-ink-600"
                  >{{ (cat as { score?: number }).score }}/{{ (cat as { max?: number }).max }}</span
                >
              </li>
            </ul>
            <ol class="list-decimal space-y-2 pl-5 text-sm">
              <li v-for="(fix, i) in critique.top_fixes || []" :key="i">
                {{ (fix as { message?: string }).message }}
              </li>
            </ol>
          </template>
        </div>

        <div v-else-if="tab === 'diff'" class="flex flex-col gap-3">
          <div class="flex flex-wrap gap-1">
            <FnButton size="sm" tone="ghost" @click="bulk('accepted')">Accept all</FnButton>
            <FnButton size="sm" tone="ghost" @click="bulk('rejected')">Reject all</FnButton>
            <FnButton size="sm" @click="applyAccepted">Apply accepted</FnButton>
          </div>
          <div v-if="changesQ.isPending.value"><FnSkeleton class="h-16" /></div>
          <p v-else-if="!(changesQ.data.value || []).length" class="text-sm text-ink-600">
            No proposed changes
          </p>
          <ul v-else class="divide-y divide-ink-100 border border-ink-100">
            <li
              v-for="ch in changesQ.data.value"
              :key="String(ch.id)"
              class="flex flex-col gap-2 p-3 text-sm sm:flex-row"
            >
              <div class="min-w-0 flex-1">
                <div class="font-medium">{{ ch.op }} · {{ ch.status }}</div>
                <p class="text-ink-600">{{ ch.reason }}</p>
                <p v-if="ch.before" class="mt-1 text-ink-500 line-through">{{ ch.before }}</p>
                <p v-if="ch.after" class="text-ink-900">{{ ch.after }}</p>
                <p v-if="ch.ask" class="mt-1 text-persimmon-800">{{ ch.ask }}</p>
              </div>
              <div v-if="ch.status === 'proposed'" class="flex shrink-0 gap-1">
                <FnButton size="sm" @click="decide(String(ch.id), 'accepted')">Accept</FnButton>
                <FnButton size="sm" tone="ghost" @click="decide(String(ch.id), 'rejected')"
                  >Reject</FnButton
                >
              </div>
            </li>
          </ul>
        </div>

        <div v-else-if="tab === 'insights'" class="flex flex-col gap-3">
          <div v-if="!trackId" class="text-sm text-ink-600">Pick a Track</div>
          <div v-else-if="insightsQ.isPending.value || insightsMut.isPending.value">
            <FnSkeleton class="h-24" />
          </div>
          <div v-else-if="activeInsights" class="flex flex-col gap-3">
            <p class="text-sm text-ink-600">
              Sample {{ activeInsights.sample_size }}
              <span v-if="activeInsights.low_confidence"> · Low confidence (&lt;30)</span>
            </p>
            <div class="overflow-x-auto">
              <table class="w-full min-w-[28rem] border-collapse text-left text-sm">
                <thead>
                  <tr class="border-b border-ink-100 text-ink-600">
                    <th class="py-1 pr-2 font-medium">Skill</th>
                    <th class="py-1 pr-2 font-medium">Freq</th>
                    <th class="py-1 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(sk, i) in insightSkills" :key="i" class="border-b border-ink-50">
                    <td class="py-1 pr-2">{{ sk.name }}</td>
                    <td class="py-1 pr-2">{{ sk.frequency }}</td>
                    <td class="py-1">
                      <FnChip :tone="skillTone(sk.status)">{{ sk.status }}</FnChip>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <ul v-if="insightTitles.length" class="text-sm text-ink-700">
              <li v-for="(ti, i) in insightTitles" :key="i">{{ ti.title }} ({{ ti.count }})</li>
            </ul>
          </div>
          <p v-else class="text-sm text-ink-600">Run Insights</p>
        </div>

        <div v-else-if="tab === 'skim'" class="flex flex-col gap-3">
          <div class="border border-persimmon-200 bg-persimmon-50/40 p-3 text-sm">
            <p class="font-medium text-ink-900">7-second zone</p>
            <p class="mt-2 whitespace-pre-wrap text-ink-800">
              {{ skim?.summary || contentPreview.slice(0, 280) }}
            </p>
            <p v-if="skim?.first_role" class="mt-2 text-ink-700">{{ skim.first_role }}</p>
          </div>
          <pre
            class="whitespace-pre-wrap border border-ink-100 p-3 font-mono text-xs text-ink-800"
            >{{ contentPreview }}</pre>
        </div>

        <div v-else-if="tab === 'parse'" class="flex flex-col gap-2 text-sm">
          <div v-if="parseQ.isPending.value"><FnSkeleton class="h-20" /></div>
          <template v-else-if="parseQ.data.value">
            <p><span class="text-ink-600">Name</span> {{ parseQ.data.value.name }}</p>
            <p><span class="text-ink-600">Email</span> {{ parseQ.data.value.email || "-" }}</p>
            <p>
              <span class="text-ink-600">Sections</span>
              {{ (parseQ.data.value.sections || []).join(", ") }}
            </p>
            <ul class="list-disc pl-5">
              <li v-for="(emp, i) in parseQ.data.value.employers || []" :key="i">
                {{ (emp as { title?: string }).title }} ·
                {{ (emp as { company?: string }).company }}
              </li>
            </ul>
            <p>{{ (parseQ.data.value.skills || []).join(", ") }}</p>
          </template>
        </div>
      </section>
    </div>
  </div>
</template>
