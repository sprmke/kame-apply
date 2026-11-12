<script setup lang="ts">
import { computed } from "vue";
import {
  segmentText,
  type MatchGrammar,
  type MatchTerm,
  type TextSegment,
} from "~/lib/job-highlights";

const props = withDefaults(
  defineProps<{
    text: string;
    grammar?: MatchGrammar | null;
    enabled?: boolean;
  }>(),
  { grammar: null, enabled: true },
);

const { t } = useI18n();
const segments = computed<TextSegment[]>(() =>
  props.enabled ? segmentText(props.text, props.grammar) : [{ text: props.text }],
);

function hint(term: MatchTerm): string {
  const state = t(
    `jobs.${term.verdict === "met" ? "inProfile" : term.verdict === "partial" ? "related" : "notInProfile"}`,
  );
  return `${term.label}: ${state}`;
}
</script>

<template>
  <template v-for="(segment, index) in segments" :key="index">
    <mark
      v-if="segment.term"
      :class="`match match-${segment.term.verdict}`"
      :title="hint(segment.term)"
      :data-match="segment.term.key"
      >{{ segment.text }}</mark
    >
    <template v-else>{{ segment.text }}</template>
  </template>
</template>

<style scoped>
.match {
  margin: 0 -0.02em;
  border-radius: 3px;
  padding: 0.05em 0.16em;
  color: var(--ink-900);
  -webkit-box-decoration-break: clone;
  box-decoration-break: clone;
}

.match-met {
  background: color-mix(in oklab, var(--brand-500) 16%, transparent);
}

.match-partial {
  background: color-mix(in oklab, var(--pencil) 12%, transparent);
}

.match-gap {
  background: color-mix(in oklab, var(--ink-400) 14%, transparent);
}
</style>

<style>
/* Theme overrides stay in a global block: the scoped compiler drops descendant
   selectors that begin with :global(). The class names are component-specific. */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .match-met {
    background: color-mix(in oklab, var(--brand-500) 30%, transparent);
  }

  :root:not([data-theme="light"]) .match-partial {
    background: color-mix(in oklab, var(--pencil) 24%, transparent);
  }

  :root:not([data-theme="light"]) .match-gap {
    background: color-mix(in oklab, var(--ink-400) 22%, transparent);
  }
}

:root[data-theme="dark"] .match-met {
  background: color-mix(in oklab, var(--brand-500) 30%, transparent);
}

:root[data-theme="dark"] .match-partial {
  background: color-mix(in oklab, var(--pencil) 24%, transparent);
}

:root[data-theme="dark"] .match-gap {
  background: color-mix(in oklab, var(--ink-400) 22%, transparent);
}
</style>
