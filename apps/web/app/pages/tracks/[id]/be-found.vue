<script setup lang="ts">
import { client } from "@kame/api-client";
import { FnButton, FnSkeleton, useToast } from "@kame/ui";
import { useMutation, useQuery } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

definePageMeta({ layout: "default" });

const route = useRoute();
const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const ws = useWorkspaceStore();
const trackId = computed(() => String(route.params.id || ""));

type Block = { kind: string; text: string; why: string; char_count: number };
type Opt = {
  headline: Block;
  about: Block;
  skills_order: string[];
  skills_why: string;
  experience: Block[];
  open_to_work: string[];
  github_checklist: string[];
};

const opt = useQuery({
  queryKey: computed(() => ["linkedin-optimize", ws.currentId, trackId.value]),
  queryFn: async () => {
    const { data } = await client.get({
      url: `/api/v1/tracks/${trackId.value}/linkedin-optimize`,
      throwOnError: true,
    });
    return data as Opt;
  },
  enabled: computed(() => Boolean(ws.currentId && trackId.value)),
});

const paste = ref("");
const report = ref<{
  score: number;
  issues: { field: string; severity: string; message: string; fix: string }[];
} | null>(null);

const check = useMutation({
  mutationFn: async () => {
    const { data } = await client.post({
      url: "/api/v1/strategy/consistency",
      body: { linkedin_text: paste.value, track_id: trackId.value },
      throwOnError: true,
    });
    return data as typeof report.value;
  },
  onSuccess: (data) => {
    report.value = data;
  },
  onError: (e) => toast.push({ title: apiError(e), tone: "danger" }),
});

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.push({ title: t("common.copied") });
  } catch {
    toast.push({ title: t("common.copy"), tone: "danger" });
  }
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <PageHeader :title="t('beFound.title')" />

    <FnSkeleton v-if="opt.isPending.value" class="h-40 w-full" />
    <template v-else-if="opt.data.value">
      <section class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <h2 class="font-display text-lg text-ink-900">{{ t("beFound.headline") }}</h2>
          <FnButton size="sm" variant="ghost" @click="copy(opt.data.value.headline.text)">{{
            t("common.copy")
          }}</FnButton>
        </div>
        <p class="whitespace-pre-wrap text-sm text-ink-900">{{ opt.data.value.headline.text }}</p>
        <p class="text-xs text-ink-600">{{ opt.data.value.headline.why }}</p>
      </section>

      <section class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <h2 class="font-display text-lg text-ink-900">{{ t("beFound.about") }}</h2>
          <FnButton size="sm" variant="ghost" @click="copy(opt.data.value.about.text)">{{
            t("common.copy")
          }}</FnButton>
        </div>
        <pre class="whitespace-pre-wrap font-sans text-sm text-ink-900">{{
          opt.data.value.about.text
        }}</pre>
        <p class="text-xs text-ink-600">{{ opt.data.value.about.why }}</p>
      </section>

      <section class="flex flex-col gap-2">
        <h2 class="font-display text-lg text-ink-900">{{ t("beFound.skills") }}</h2>
        <p class="text-sm text-ink-900">{{ opt.data.value.skills_order.join(" · ") }}</p>
        <p class="text-xs text-ink-600">{{ opt.data.value.skills_why }}</p>
      </section>

      <section class="flex flex-col gap-3">
        <h2 class="font-display text-lg text-ink-900">{{ t("beFound.experience") }}</h2>
        <div
          v-for="(ex, i) in opt.data.value.experience"
          :key="i"
          class="flex flex-col gap-1 border-b border-rule pb-3"
        >
          <div class="flex justify-end">
            <FnButton size="sm" variant="ghost" @click="copy(ex.text)">{{
              t("common.copy")
            }}</FnButton>
          </div>
          <pre class="whitespace-pre-wrap font-sans text-sm text-ink-900">{{ ex.text }}</pre>
          <p class="text-xs text-ink-600">{{ ex.why }}</p>
        </div>
      </section>

      <section class="flex flex-col gap-2">
        <h2 class="font-display text-lg text-ink-900">{{ t("beFound.openToWork") }}</h2>
        <ol class="list-decimal pl-5 text-sm text-ink-600">
          <li v-for="(step, i) in opt.data.value.open_to_work" :key="i">{{ step }}</li>
        </ol>
      </section>

      <section class="flex flex-col gap-2">
        <h2 class="font-display text-lg text-ink-900">{{ t("beFound.github") }}</h2>
        <ul class="list-disc pl-5 text-sm text-ink-600">
          <li v-for="(step, i) in opt.data.value.github_checklist" :key="i">{{ step }}</li>
        </ul>
      </section>
    </template>

    <section class="flex flex-col gap-3">
      <h2 class="font-display text-lg text-ink-900">{{ t("beFound.consistency") }}</h2>
      <textarea
        v-model="paste"
        rows="6"
        class="w-full border border-rule bg-paper-1 p-2 text-sm"
        :aria-label="t('beFound.paste')"
      ></textarea>
      <FnButton
        size="sm"
        :disabled="paste.length < 20 || check.isPending.value"
        @click="check.mutate()"
        >{{ t("beFound.check") }}</FnButton
      >
      <div v-if="report" class="flex flex-col gap-2 text-sm">
        <p class="font-medium text-ink-900">{{ t("beFound.score") }} {{ report.score }}</p>
        <ul class="flex flex-col gap-1">
          <li v-for="(iss, i) in report.issues" :key="i" class="text-ink-600">
            {{ iss.message }} · {{ iss.fix }}
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>
