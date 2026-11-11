<script setup lang="ts">
definePageMeta({ layout: false });
</script>

<template>
  <main class="mx-auto max-w-2xl px-4 py-12 text-ink-900">
    <h1 class="font-serif text-3xl font-semibold">Terms</h1>
    <p class="mt-4 text-sm text-ink-600">Last updated: 2026-11-01</p>
    <section class="mt-8 flex flex-col gap-3 text-sm leading-relaxed text-ink-900">
      <p>
        Kame Apply is a job-search workbench. You stay responsible for applications you submit and
        for following the terms of each job site you use.
      </p>
      <h2 class="mt-4 font-serif text-xl">Your account</h2>
      <p>
        Keep your credentials private. You may invite others only to team workspaces you own or
        administer. Do not use the product to harass employers or scrape sites against their terms.
      </p>
      <h2 class="mt-4 font-serif text-xl">AI drafts</h2>
      <p>
        Generated resumes, letters, and answers are drafts until you accept them. Claims must come
        from your Career Profile. Gaps stay gaps.
      </p>
      <h2 class="mt-4 font-serif text-xl">Apply assist</h2>
      <p>
        Autofill and apply assist never click Submit unless you have turned on that policy. On
        LinkedIn, Indeed, and JobStreet, Submit always stays with you.
      </p>
      <h2 class="mt-4 font-serif text-xl">Availability</h2>
      <p>
        The free-tier host may pause for maintenance or provider outages. We aim for recoverability
        via backups, not perfect uptime.
      </p>
      <p>
        Privacy:
        <NuxtLink class="underline" to="/legal/privacy">privacy</NuxtLink>.
      </p>
    </section>
  </main>
</template>
