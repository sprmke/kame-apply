# Spike 6: Hey API + FastAPI + Vue Query

**Date:** 2026-10-28 · **Decision: KEEP (Orval fallback not needed)** · `@hey-api/openapi-ts` 0.99, `@tanstack/vue-query` 5.105, strict TS 5.9. Code: `spikes/hey-api/`.

| Check | Result |
| --- | --- |
| Generated client from FastAPI OpenAPI (real `packages/api-client`) | Works; `gen:api-client` + drift check in CI verified both ways. |
| Strict TS compile of generated vue-query options | Clean (needs `lib: DOM.Iterable` in the consuming tsconfig). |
| Discriminated union (`oneOf` + `discriminator`) | Survives; `r.level === "danger"` narrows to the variant with `reasons`. |
| Unknown query param | Rejected at compile time. |
| Reactive params | `useQuery(computed(() => listJobsOptions({ query: { q: q.value } })))` refetches with the new URL when the ref changes (runtime test `spikes/hey-api/reactive.test.ts`, passes). |

Notes: the `@hey-api/client-fetch` package is deprecated; the client is bundled by the generator, so do not depend on it. `format`/`lint` output options are deprecated in favour of `postProcess: []`. A weak assertion in the first draft of the type test was caught (an `@ts-expect-error` firing on the wrong problem); only the unknown-param check counts as evidence of strict body typing, so add a real required-field test with the first real mutation (Phase 2).
