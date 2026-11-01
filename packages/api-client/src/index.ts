export * from "./generated";
// The configured client instance (base URL, interceptors) and the Vue Query option helpers are
// not in the generated barrel, so the web app imports them from here.
export { client } from "./generated/client.gen";
export * as queries from "./generated/@tanstack/vue-query.gen";
// Zod schemas generated from the same OpenAPI spec; forms extend them with UX-only rules.
export * as schemas from "./generated/zod.gen";
