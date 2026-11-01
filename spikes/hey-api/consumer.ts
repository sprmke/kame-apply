import { useMutation, useQuery } from "@tanstack/vue-query";
import { computed, ref } from "vue";
import {
  createTrackMutation,
  getJobRiskOptions,
  listJobsOptions,
} from "./generated/@tanstack/vue-query.gen";

const q = ref("python");

// Reactive params wrapped in computed: the whole options object is re-derived when q changes.
export function useJobs() {
  return useQuery(computed(() => listJobsOptions({ query: { q: q.value, limit: 20 } })));
}

export function useRisk(id: string) {
  const query = useQuery(computed(() => getJobRiskOptions({ path: { job_id: id } })));
  // Discriminated union must narrow: `reasons` exists only on the danger variant.
  const reasons = computed(() => {
    const r = query.data.value;
    if (!r) return [];
    if (r.level === "danger") return r.reasons;
    return [];
  });
  return { query, reasons };
}

export function useCreateTrack() {
  const m = useMutation(createTrackMutation());
  return () => m.mutate({ body: { name: "AI Engineer" } });
}

// @ts-expect-error `name` is required: strict typing must reject an empty body
export const bad = () => createTrackMutation().mutationFn?.({ body: {} } as never);
// @ts-expect-error unknown query param must be rejected
export const bad2 = () => listJobsOptions({ query: { nope: 1 } });
