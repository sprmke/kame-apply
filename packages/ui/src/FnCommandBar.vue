<script setup lang="ts">
import {
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
  ListboxContent,
  ListboxFilter,
  ListboxGroup,
  ListboxGroupLabel,
  ListboxItem,
  ListboxRoot,
} from "reka-ui";
import { computed, ref, watch } from "vue";

export type CommandItem = { id: string; label: string; group?: string; hint?: string };

const open = defineModel<boolean>("open", { default: false });
const props = defineProps<{
  items: CommandItem[];
  title: string;
  placeholder: string;
  empty: string;
}>();
const emit = defineEmits<{ select: [id: string] }>();

const query = ref("");
watch(open, (o) => o && (query.value = ""));

const groups = computed(() => {
  const q = query.value.trim().toLowerCase();
  const hits = props.items.filter((i) => !q || i.label.toLowerCase().includes(q));
  const map = new Map<string, CommandItem[]>();
  for (const h of hits) map.set(h.group ?? "", [...(map.get(h.group ?? "") ?? []), h]);
  return [...map.entries()];
});

function choose(id: string) {
  open.value = false;
  emit("select", id);
}
</script>

<template>
  <DialogRoot v-model:open="open">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-40 bg-ink-900/40" />
      <DialogContent
        class="fixed top-[12vh] left-1/2 z-50 w-[calc(100vw-32px)] max-w-lg -translate-x-1/2 overflow-hidden rounded-md border border-rule bg-paper-1 shadow-float focus:outline-none"
      >
        <DialogTitle class="sr-only">{{ title }}</DialogTitle>
        <DialogDescription class="sr-only">{{ placeholder }}</DialogDescription>
        <ListboxRoot @update:model-value="(v) => v && choose(String((v as CommandItem).id))">
          <ListboxFilter
            v-model="query"
            :placeholder="placeholder"
            :aria-label="placeholder"
            class="min-h-12 w-full border-b border-rule bg-transparent px-4 text-base text-ink-900 placeholder:text-ink-400 focus:outline-none"
          />
          <ListboxContent class="max-h-[50vh] overflow-y-auto p-1">
            <p v-if="!groups.length" class="px-3 py-6 text-center text-sm text-ink-600">
              {{ empty }}
            </p>
            <ListboxGroup v-for="[g, rows] in groups" :key="g">
              <ListboxGroupLabel
                v-if="g"
                class="px-3 pt-2 pb-1 text-xs font-medium tracking-wide text-ink-600 uppercase"
              >
                {{ g }}
              </ListboxGroupLabel>
              <ListboxItem
                v-for="r in rows"
                :key="r.id"
                :value="r"
                class="flex min-h-11 cursor-pointer items-center justify-between gap-3 rounded-sm px-3 text-sm text-ink-900 data-[highlighted]:bg-paper-2"
              >
                <span>{{ r.label }}</span>
                <span v-if="r.hint" class="font-mono text-xs text-ink-600">{{ r.hint }}</span>
              </ListboxItem>
            </ListboxGroup>
          </ListboxContent>
        </ListboxRoot>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
