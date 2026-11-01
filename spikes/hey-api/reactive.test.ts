import { QueryClient, VueQueryPlugin } from "@tanstack/vue-query";
import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent, h, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { client } from "./generated/client.gen";
import { listJobsOptions } from "./generated/@tanstack/vue-query.gen";
import { useQuery } from "@tanstack/vue-query";
import { computed } from "vue";

describe("Hey API + Vue Query reactive params", () => {
  it("refetches with the new query string when a ref changes", async () => {
    const urls: string[] = [];
    client.setConfig({
      baseUrl: "http://api.test",
      fetch: (async (req: Request) => {
        urls.push(new URL(req.url).search);
        return new Response(JSON.stringify({ items: [], next_cursor: null }), {
          headers: { "content-type": "application/json" },
        });
      }) as typeof fetch,
    });
    const q = ref("python");
    const Cmp = defineComponent({
      setup() {
        useQuery(computed(() => listJobsOptions({ query: { q: q.value } })));
        return () => h("div");
      },
    });
    mount(Cmp, { global: { plugins: [[VueQueryPlugin, { queryClient: new QueryClient() }]] } });
    await flushPromises();
    q.value = "go";
    await flushPromises();
    await vi.waitFor(() => expect(urls.length).toBe(2));
    expect(urls[0]).toContain("q=python");
    expect(urls[1]).toContain("q=go");
  });
});
