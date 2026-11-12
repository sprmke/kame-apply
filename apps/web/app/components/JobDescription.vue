<script setup lang="ts">
import { FnButton } from "@kame/ui";
import { computed, ref } from "vue";
import { buildMatchGrammar, type MatchTerm, type MatchVerdict } from "~/lib/job-highlights";
import { formatJobDescription } from "~/lib/job-description";

const props = withDefaults(
  defineProps<{
    text?: string | null;
    terms?: MatchTerm[];
    highlight?: boolean;
  }>(),
  { text: null, terms: () => [], highlight: true },
);

const { t } = useI18n();
const expanded = ref(false);
const sections = computed(() => formatJobDescription(props.text));
const visibleSections = computed(() =>
  expanded.value ? sections.value : sections.value.slice(0, 2),
);
const hasMore = computed(() => sections.value.length > 2);
const grammar = computed(() => buildMatchGrammar(props.terms));

const counts = computed(() => {
  const out: Record<MatchVerdict, number> = { met: 0, partial: 0, gap: 0 };
  for (const term of props.terms) out[term.verdict] += 1;
  return out;
});

const termsByLabel = computed(() => {
  const map = new Map<string, MatchTerm>();
  for (const term of props.terms) {
    map.set(term.label.toLowerCase(), term);
    for (const pattern of term.patterns ?? []) map.set(pattern.toLowerCase(), term);
  }
  return map;
});

function toolTerm(tool: string): MatchTerm | undefined {
  return termsByLabel.value.get(tool.trim().toLowerCase());
}

function toolClass(tool: string): string {
  const term = toolTerm(tool);
  return term ? chipClass(term.verdict) : "border-rule bg-paper-2 text-ink-600";
}

function toolIcon(tool: string): string {
  const term = toolTerm(tool);
  return term ? glyph(term.verdict) : "";
}

function toolState(tool: string): string {
  const term = toolTerm(tool);
  return term ? stateLabel(term.verdict) : "";
}

function chipClass(verdict: MatchVerdict): string {
  if (verdict === "met") return "border-brand-200 bg-brand-50 text-brand-700";
  if (verdict === "partial") return "border-dashed border-pencil bg-paper-0 text-pencil";
  return "border-rule bg-paper-2 text-ink-600";
}

function glyph(verdict: MatchVerdict): string {
  if (verdict === "met") return "ph:check";
  if (verdict === "partial") return "ph:circle-half";
  return "ph:minus";
}

function stateLabel(verdict: MatchVerdict): string {
  return t(
    verdict === "met"
      ? "jobs.inProfile"
      : verdict === "partial"
        ? "jobs.related"
        : "jobs.notInProfile",
  );
}

function hint(term: MatchTerm): string {
  return `${term.label}: ${stateLabel(term.verdict)}`;
}
</script>

<template>
  <div class="flex max-w-[68ch] flex-col gap-6">
    <section
      v-if="terms.length"
      class="flex flex-col gap-2.5"
      :aria-label="t('jobs.skillsInPosting')"
    >
      <ul class="flex flex-wrap gap-1.5">
        <li v-for="term in terms" :key="term.key">
          <span
            class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold"
            :class="chipClass(term.verdict)"
            :title="hint(term)"
          >
            <NavIcon :name="glyph(term.verdict)" :size="12" />
            {{ term.label }}
            <span class="sr-only">, {{ stateLabel(term.verdict) }}</span>
          </span>
        </li>
      </ul>
      <p class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-medium text-ink-600">
        <span v-if="counts.met" class="inline-flex items-center gap-1 text-brand-700">
          <NavIcon name="ph:check" :size="12" />{{ counts.met }} {{ t("jobs.inProfile") }}
        </span>
        <span v-if="counts.partial" class="inline-flex items-center gap-1 text-pencil">
          <NavIcon name="ph:circle-half" :size="12" />{{ counts.partial }} {{ t("jobs.related") }}
        </span>
        <span v-if="counts.gap" class="inline-flex items-center gap-1">
          <NavIcon name="ph:minus" :size="12" />{{ counts.gap }} {{ t("jobs.notInProfile") }}
        </span>
      </p>
    </section>

    <p v-if="!sections.length" class="text-sm text-ink-600">No description.</p>
    <section
      v-for="(section, sectionIndex) in visibleSections"
      :key="`${section.title}-${sectionIndex}`"
      class="flex flex-col gap-2.5"
      :aria-label="section.title"
    >
      <h3 class="text-lg font-bold tracking-[-0.02em] text-ink-900">{{ section.title }}</h3>
      <ul
        v-if="section.kind === 'list'"
        class="flex list-disc flex-col gap-2 pl-5 marker:text-ink-400"
      >
        <li
          v-for="(item, index) in section.bullets"
          :key="index"
          class="pl-1 text-base leading-7 text-ink-900"
        >
          <HighlightedText :text="item" :grammar="grammar" :enabled="highlight" />
        </li>
      </ul>
      <div v-else-if="section.kind === 'tools'" class="flex flex-wrap gap-2">
        <span
          v-for="tool in section.tools"
          :key="tool"
          class="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium"
          :class="toolClass(tool)"
        >
          <NavIcon v-if="toolIcon(tool)" :name="toolIcon(tool)" :size="12" class="shrink-0" />
          {{ tool }}
          <span v-if="toolState(tool)" class="sr-only">, {{ toolState(tool) }}</span>
        </span>
      </div>
      <template v-else>
        <p
          v-for="(paragraph, index) in section.paragraphs"
          :key="index"
          class="text-base leading-7 text-ink-900"
        >
          <HighlightedText :text="paragraph" :grammar="grammar" :enabled="highlight" />
        </p>
      </template>
    </section>
    <div v-if="hasMore" class="border-t border-rule pt-4">
      <FnButton size="sm" tone="quiet" :aria-expanded="expanded" @click="expanded = !expanded">
        {{ expanded ? "Show less" : `Read full description (${sections.length} sections)` }}
      </FnButton>
    </div>
  </div>
</template>
