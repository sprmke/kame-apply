<script setup lang="ts">
import { TabsContent, TabsList, TabsRoot, TabsTrigger } from "reka-ui";

export type TabItem = { value: string; label: string };
const model = defineModel<string>();
defineProps<{ items: TabItem[]; label: string }>();
</script>

<template>
  <TabsRoot v-model="model">
    <TabsList :aria-label="label" class="flex gap-1 overflow-x-auto border-b border-rule">
      <TabsTrigger
        v-for="t in items"
        :key="t.value"
        :value="t.value"
        class="-mb-px min-h-11 border-b-2 border-transparent px-3 text-sm text-ink-600 hover:text-ink-900 focus-visible:outline-2 focus-visible:outline-persimmon-700 data-[state=active]:border-ink-900 data-[state=active]:text-ink-900"
      >
        {{ t.label }}
      </TabsTrigger>
    </TabsList>
    <TabsContent v-for="t in items" :key="t.value" :value="t.value" class="pt-4">
      <slot :name="t.value" />
    </TabsContent>
  </TabsRoot>
</template>
