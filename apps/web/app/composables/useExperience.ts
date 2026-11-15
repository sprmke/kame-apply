import type { IndustryExperienceRead } from "@kame/api-client";
import { getExperienceApiV1WorkspaceExperienceGet } from "@kame/api-client";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useWorkspaceStore } from "~/stores/workspace";

export type Visibility = "visible" | "collapsed" | "hidden";

export type FacetOption = {
  key: string;
  label_key: string;
};

export type Facet = {
  key: string;
  label_key: string;
  kind: "multi" | "single" | "bool" | "range";
  options: FacetOption[];
  group: string;
  match: { filter: boolean; boost: number; ledger_only: boolean };
};

export type PackManifest = {
  key: string;
  version: number;
  label_key: string;
  icon: string;
  states: Record<string, Visibility>;
  groups: { key: string; fields: string[] }[];
  labels: Record<string, string>;
  profile_sections: string[];
  nav: Record<string, boolean>;
  facets: Facet[];
  features: Record<string, boolean>;
  seniority_ladder: { key: string; label_key: string; maps_to: string }[];
  criteria_defaults: {
    work_modes: string[];
    employment_types: string[];
    shifts: string[];
    salary_period: string | null;
    posting_max_age_days: number | null;
  };
};

type Experience = {
  primary: string;
  enabled: IndustryExperienceRead["enabled"];
  manifest: PackManifest;
  packs: Record<string, PackManifest>;
};

/** Reads the server-resolved pack manifest. Pages never branch on the industry key. */
export function useExperience() {
  const ws = useWorkspaceStore();
  const qc = useQueryClient();
  const { t, te } = useI18n();

  const query = useQuery({
    queryKey: computed(() => ["experience", ws.currentId]),
    queryFn: async () => {
      const { data } = await getExperienceApiV1WorkspaceExperienceGet({ throwOnError: true });
      return data as unknown as Experience;
    },
    enabled: computed(() => Boolean(ws.currentId)),
  });

  const data = computed(() => query.data.value ?? null);
  const manifest = computed(() => data.value?.manifest ?? null);
  const enabled = computed(() => data.value?.enabled ?? []);
  const primary = computed(() => data.value?.primary ?? "general");

  function manifestFor(industry?: string | null): PackManifest | null {
    if (!data.value) return null;
    return data.value.packs[industry || primary.value] ?? data.value.packs.general ?? null;
  }

  function stateOf(field: string, industry?: string | null): Visibility {
    return manifestFor(industry)?.states[field] ?? "visible";
  }

  function labelKeyOf(field: string, industry?: string | null): string | null {
    return manifestFor(industry)?.labels[field] ?? null;
  }

  function labelOf(field: string, industry: string | null | undefined, fallback: string): string {
    const key = labelKeyOf(field, industry);
    return key && te(key) ? t(key) : fallback;
  }

  function facetsFor(industry?: string | null): Facet[] {
    return manifestFor(industry)?.facets ?? [];
  }

  function packLabel(key: string): string {
    const item = enabled.value.find((row) => row.key === key);
    if (item?.label) return item.label;
    const candidate = `industry.${key}.label`;
    return te(candidate) ? t(candidate) : key;
  }

  function facetLabel(facet: Facet): string {
    return te(facet.label_key) ? t(facet.label_key) : facet.key;
  }

  function optionLabel(option: FacetOption): string {
    return te(option.label_key) ? t(option.label_key) : option.key;
  }

  async function refresh() {
    await qc.invalidateQueries({ queryKey: ["experience", ws.currentId] });
  }

  return {
    query,
    data,
    manifest,
    enabled,
    primary,
    manifestFor,
    stateOf,
    labelKeyOf,
    labelOf,
    facetsFor,
    packLabel,
    facetLabel,
    optionLabel,
    refresh,
    loading: computed(() => query.isPending.value && !data.value),
  };
}
