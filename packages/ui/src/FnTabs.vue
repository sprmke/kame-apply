<script setup lang="ts">
import { TabsContent, TabsList, TabsRoot, TabsTrigger } from "reka-ui";

export type TabItem = { value: string; label: string };
const model = defineModel<string>();
defineProps<{ items: TabItem[]; label: string }>();
</script>

<template>
  <TabsRoot v-model="model">
    <TabsList :aria-label="label" class="flex gap-1 overflow-x-auto rounded-lg bg-paper-2 p-1">
      <TabsTrigger
        v-for="t in items"
        :key="t.value"
        :value="t.value"
        class="min-h-11 rounded-md px-4 text-sm font-semibold text-ink-600 transition-colors hover:text-ink-900 focus-visible:outline-2 focus-visible:outline-brand-500 data-[state=active]:bg-paper-1 data-[state=active]:text-brand-700 data-[state=active]:shadow-[var(--shadow-card)]"
      >
        {{ t.label }}
      </TabsTrigger>
    </TabsList>
    <TabsContent v-for="t in items" :key="t.value" :value="t.value" class="pt-5">
      <slot :name="t.value" />
    </TabsContent>
  </TabsRoot>
</template>
