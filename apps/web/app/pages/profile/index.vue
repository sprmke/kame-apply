<script setup lang="ts">
import { useActiveProfile } from "~/composables/useActiveProfile";
import type { ExperienceRead } from "@kame/api-client";
import { FnButton, FnChip, FnSkeleton, useToast } from "@kame/ui";

const { t } = useI18n();
const toast = useToast();
const apiError = useApiError();
const { profile, profileId, loading, ensureProfile } = useActiveProfile();
const interviewOpen = ref(false);

onMounted(async () => {
  try {
    await ensureProfile();
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  }
});

function chipTone(s: string): "neutral" | "accent" | "pencil" {
  if (s === "strong") return "accent";
  if (s === "weak") return "pencil";
  return "neutral";
}

function expLabel(e: ExperienceRead) {
  const end = e.is_current ? t("career.present") : e.end_date || "";
  return [e.start_date, end].filter(Boolean).join(" to ");
}

function proofLabel(strength: string | null | undefined): string {
  return strength === "strong" ? t("career.proofStrong") : t("career.proofWeak");
}

const completeness = computed(() => {
  const p = profile.value;
  if (!p) return 0;
  const checks = [
    Boolean(p.display_name),
    Boolean(p.headline),
    Boolean(p.location),
    Boolean(p.experiences?.length),
    Boolean(p.bullets?.length),
    Boolean(p.skills?.length),
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
});

const nextSteps = computed(() => {
  const p = profile.value;
  if (!p) return [];
  const out: { label: string; to: string }[] = [];
  if (!p.headline) out.push({ label: t("career.addHeadline"), to: "/start" });
  if (!p.location) out.push({ label: t("career.addLocation"), to: "/start" });
  if (!p.experiences?.length)
    out.push({ label: t("career.addExperience"), to: "/profile/onboarding" });
  if (!p.skills?.length) out.push({ label: t("career.addSkills"), to: "/profile/onboarding" });
  return out.slice(0, 3);
});
</script>

<template>
  <div class="flex flex-col gap-8">
    <div v-if="loading" class="flex flex-col gap-3">
      <FnSkeleton class="h-8 w-48" />
      <FnSkeleton class="h-24 w-full" />
    </div>
    <template v-else-if="profile">
      <section class="flex flex-col gap-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <h2 class="text-2xl font-bold tracking-[-0.02em] text-ink-900">
              {{ profile.display_name }}
            </h2>
            <p v-if="profile.headline" class="text-ink-600">{{ profile.headline }}</p>
            <p v-if="profile.location" class="text-sm text-ink-600">{{ profile.location }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <FnButton tone="ghost" @click="interviewOpen = true">{{
              t("career.interview")
            }}</FnButton>
            <FnButton tone="primary" @click="navigateTo('/profile/onboarding')">{{
              t("career.upload")
            }}</FnButton>
          </div>
        </div>
        <p v-if="profile.summary" class="max-w-prose text-ink-900">{{ profile.summary }}</p>

        <div class="flex flex-col gap-2 rounded-xl border border-rule bg-paper-1 p-4">
          <div class="flex items-center justify-between gap-2 text-sm">
            <span class="font-semibold text-ink-900">{{ t("career.completeness") }}</span>
            <span class="tabular-nums text-ink-600">{{ completeness }}%</span>
          </div>
          <div
            class="h-2 overflow-hidden rounded-full bg-paper-2"
            role="progressbar"
            :aria-valuenow="completeness"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="t('career.completeness')"
          >
            <div class="h-full rounded-full bg-brand-700" :style="{ width: `${completeness}%` }" />
          </div>
          <ul v-if="nextSteps.length" class="flex flex-col gap-1 text-sm">
            <li v-for="step in nextSteps" :key="step.label">
              <NuxtLink :to="step.to" class="text-brand-700 underline">{{ step.label }}</NuxtLink>
            </li>
          </ul>
        </div>
      </section>

      <section class="flex flex-col gap-3">
        <div class="flex flex-col gap-1">
          <h3 class="text-sm font-semibold tracking-wide text-ink-400 uppercase">
            {{ t("career.experiences") }}
          </h3>
          <p class="text-sm leading-6 text-ink-600">{{ t("career.evidenceHint") }}</p>
        </div>
        <p v-if="!profile.experiences?.length" class="text-sm text-ink-600">
          {{ t("career.emptyExperiences") }}
        </p>
        <article v-for="exp in profile.experiences" :key="exp.id" class="border-t border-rule py-4">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <h4 class="font-medium text-ink-900">{{ exp.title }} · {{ exp.company }}</h4>
            <span class="text-xs tabular-nums text-ink-600">{{ expLabel(exp) }}</span>
          </div>
          <ul class="mt-2 flex flex-col gap-2">
            <li
              v-for="b in profile.bullets.filter((x) => x.experience_id === exp.id)"
              :key="b.id"
              class="flex items-start gap-2 text-sm"
            >
              <FnChip :tone="chipTone(b.evidence_strength ?? 'weak')" class="mt-0.5 shrink-0">{{
                proofLabel(b.evidence_strength)
              }}</FnChip>
              <span :class="b.do_not_use ? 'text-ink-600 line-through' : 'text-ink-900'">{{
                b.text
              }}</span>
            </li>
          </ul>
        </article>
      </section>

      <ProfileFacets v-if="profileId" />

      <section class="flex flex-col gap-2">
        <h3 class="text-sm font-semibold tracking-wide text-ink-400 uppercase">
          {{ t("career.skills") }}
        </h3>
        <div v-if="profile.skills?.length" class="flex flex-wrap gap-2">
          <FnChip v-for="sk in profile.skills" :key="sk.id">
            {{ sk.name }}<template v-if="sk.years != null"> · {{ sk.years }}y</template>
          </FnChip>
        </div>
        <p v-else class="text-sm text-ink-600">{{ t("career.emptySkills") }}</p>
      </section>

      <InterviewDrawer v-if="profileId" v-model:open="interviewOpen" :profile-id="profileId" />
    </template>
    <p v-else class="text-sm text-ink-600">{{ t("career.missing") }}</p>
  </div>
</template>
