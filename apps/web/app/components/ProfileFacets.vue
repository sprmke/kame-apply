<script setup lang="ts">
import { client } from "@kame/api-client";
import { FnButton, FnChip, useToast } from "@kame/ui";
import { useActiveProfile } from "~/composables/useActiveProfile";
import { useExperience } from "~/composables/useExperience";

const { t, te } = useI18n();
const { profile, profileId, refresh } = useActiveProfile();
const exp = useExperience();
const toast = useToast();
const apiError = useApiError();
const busy = ref(false);
const draft = ref<Record<string, string>>({});

const facetDefs = computed(() => exp.manifest.value?.facets ?? []);
watch(
  facetDefs,
  (defs) => {
    const next = { ...draft.value };
    for (const facet of defs) {
      if (next[facet.key] == null) next[facet.key] = "";
    }
    draft.value = next;
  },
  { immediate: true },
);
const saved = computed(() => {
  const rows = (
    profile.value as unknown as { facets?: { id: string; facet_key: string; value: string }[] }
  )?.facets;
  return rows ?? [];
});

function optionLabel(facetKey: string, value: string): string {
  const def = facetDefs.value.find((facet) => facet.key === facetKey);
  const option = def?.options.find((item) => item.key === value);
  return option ? exp.optionLabel(option) : value;
}

function valuesFor(key: string) {
  return saved.value.filter((row) => row.facet_key === key);
}

function optionsFor(key: string) {
  const def = facetDefs.value.find((facet) => facet.key === key);
  if (!def) return [];
  const chosen = new Set(valuesFor(key).map((row) => row.value));
  return def.options.filter((option) => !chosen.has(option.key));
}

async function add(key: string) {
  const value = draft.value[key];
  if (!value || !profileId.value) return;
  busy.value = true;
  try {
    await client.post({
      url: `/api/v1/profiles/${profileId.value}/facets`,
      body: { facet_key: key, value },
      throwOnError: true,
    });
    draft.value[key] = "";
    await refresh();
    toast.push({ title: t("career.facetAdded"), tone: "success" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}

async function remove(id: string) {
  if (!profileId.value) return;
  busy.value = true;
  try {
    await client.delete({
      url: `/api/v1/profiles/${profileId.value}/facets/${id}`,
      throwOnError: true,
    });
    await refresh();
    toast.push({ title: t("career.facetRemoved"), tone: "neutral" });
  } catch (e) {
    toast.push({ title: apiError(e), tone: "danger" });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section v-if="facetDefs.length" class="flex flex-col gap-3">
    <h3 class="text-sm font-semibold tracking-wide text-ink-400 uppercase">
      {{ t("career.facets") }}
    </h3>
    <div v-for="facet in facetDefs" :key="facet.key" class="flex flex-col gap-2">
      <p class="text-sm font-medium text-ink-900">{{ exp.facetLabel(facet) }}</p>
      <div class="flex flex-wrap items-center gap-2">
        <FnChip
          v-for="row in valuesFor(facet.key)"
          :key="row.id"
          removable
          :remove-label="t('tracks.removeChip')"
          @remove="remove(row.id)"
        >
          {{ optionLabel(facet.key, row.value) }}
        </FnChip>
        <template v-if="optionsFor(facet.key).length">
          <select
            v-model="draft[facet.key]"
            class="min-h-11 rounded-lg border border-edge bg-paper-0 px-3 text-sm text-ink-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
            :aria-label="exp.facetLabel(facet)"
          >
            <option value="">{{ t("career.addFacet") }}</option>
            <option v-for="option in optionsFor(facet.key)" :key="option.key" :value="option.key">
              {{ te(option.label_key) ? t(option.label_key) : option.key }}
            </option>
          </select>
          <FnButton
            size="sm"
            tone="quiet"
            :disabled="busy || !draft[facet.key]"
            @click="add(facet.key)"
            >{{ t("common.save") }}</FnButton
          >
        </template>
      </div>
    </div>
  </section>
</template>
