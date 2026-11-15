<script setup lang="ts">
import { FnButton, FnSectionCard } from "@kame/ui";

const { t } = useI18n();

const words = [
  ["Search", "A role you want. We look for matching jobs on a schedule."],
  ["Search run", "One pass over the job sources for a search."],
  ["How much we do", "How far we go on each match before we stop for you."],
  ["Find and prepare", "We also draft a resume and letter for jobs you shortlist."],
  ["Practice run", "We show what we would have sent, without sending."],
  ["Minimum match", "Only jobs scoring at least this high are considered."],
  ["Company career site", "The system a company uses for job posts and applications."],
  ["Where we look", "A job board or company career site we check."],
  ["How you match", "Each job requirement checked against your profile."],
  ["Resume check", "Scores and the top fixes for your resume."],
  ["What hiring software reads", "The text an applicant system pulls from your file."],
  ["Apply helper", "Fills forms in a browser we control. You watch and approve."],
  ["Proof from your resume", "The line in your profile that backs a claim."],
  ["Not open to you", "The posting says it does not hire from your location or status."],
];

const shortcuts = [
  ["⌘K", "Open the command bar"],
  ["j / k", "Move down or up in a job list"],
  ["s", "Shortlist the open job"],
  ["x", "Skip the open job"],
  ["t", "Tailor a resume for the open job"],
  ["o", "Open the original posting"],
  ["?", "Show the job list shortcuts"],
];
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-5">
    <PageHeader :title="t('shell.help')" />

    <FnSectionCard :title="t('shell.helpGlossary')" :intro="t('help.glossaryIntro')">
      <dl class="divide-y divide-rule">
        <div v-for="[term, meaning] in words" :key="term" class="flex flex-col gap-0.5 py-3">
          <dt class="text-sm font-semibold text-ink-900">{{ term }}</dt>
          <dd class="text-sm leading-6 text-ink-600">{{ meaning }}</dd>
        </div>
      </dl>
    </FnSectionCard>

    <FnSectionCard :title="t('shell.helpShortcuts')">
      <dl class="divide-y divide-rule">
        <div
          v-for="[keys, action] in shortcuts"
          :key="keys"
          class="flex min-h-11 items-center justify-between gap-3 py-2"
        >
          <dt class="text-sm text-ink-900">{{ action }}</dt>
          <dd>
            <kbd
              class="rounded border border-rule bg-paper-2 px-2 py-1 text-xs font-semibold text-ink-600"
              >{{ keys }}</kbd
            >
          </dd>
        </div>
      </dl>
      <p class="text-sm text-ink-600">{{ t("help.shortcutsHint") }}</p>
    </FnSectionCard>

    <FnSectionCard :title="t('shell.helpSetup')">
      <div class="flex flex-wrap items-center gap-2">
        <FnButton as-child tone="primary">
          <NuxtLink to="/start">{{ t("shell.helpSetup") }}</NuxtLink>
        </FnButton>
        <FeedbackButton />
      </div>
    </FnSectionCard>
  </div>
</template>
