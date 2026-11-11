<script setup lang="ts">
import { FnButton } from "@kame/ui";
import { computed, ref } from "vue";
import { formatJobDescription } from "~/lib/job-description";

const props = defineProps<{ text?: string | null }>();
const expanded = ref(false);
const sections = computed(() => formatJobDescription(props.text));
const visibleSections = computed(() =>
  expanded.value ? sections.value : sections.value.slice(0, 2),
);
const hasMore = computed(() => sections.value.length > 2);
</script>

<template>
  <div class="flex max-w-[68ch] flex-col gap-6">
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
          {{ item }}
        </li>
      </ul>
      <div v-else-if="section.kind === 'tools'" class="flex flex-wrap gap-2">
        <span
          v-for="tool in section.tools"
          :key="tool"
          class="rounded-full border border-rule bg-paper-2 px-3 py-1 text-sm font-medium text-ink-600"
        >
          {{ tool }}
        </span>
      </div>
      <template v-else>
        <p
          v-for="(paragraph, index) in section.paragraphs"
          :key="index"
          class="text-base leading-7 text-ink-900"
        >
          {{ paragraph }}
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
