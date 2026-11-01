<script setup lang="ts">
definePageMeta({ layout: false });
</script>

<template>
  <main class="mx-auto max-w-2xl px-4 py-12 text-ink-900">
    <h1 class="font-serif text-3xl font-semibold">Privacy</h1>
    <p class="mt-4 text-sm text-ink-700">Last updated: 2026-11-01</p>
    <section class="mt-8 flex flex-col gap-3 text-sm leading-relaxed text-ink-800">
      <p>
        Kame Apply stores your Career Profile, tracks, job matches, applications, and settings in
        your workspace so you can search and apply for jobs.
      </p>
      <h2 class="mt-4 font-serif text-xl">What we store</h2>
      <ul class="list-disc space-y-1 pl-5">
        <li>Account email and name</li>
        <li>Career Profile facts you enter or accept from a resume upload</li>
        <li>Tracks, jobs, applications, and activity in your workspace</li>
        <li>Encrypted AI provider keys you add (never third-party chat login secrets)</li>
      </ul>
      <h2 class="mt-4 font-serif text-xl">What we do not store</h2>
      <ul class="list-disc space-y-1 pl-5">
        <li>Government IDs, bank/card numbers, or full street address before an offer</li>
        <li>Passwords for LinkedIn, Indeed, JobStreet, or other job sites</li>
      </ul>
      <h2 class="mt-4 font-serif text-xl">Your controls</h2>
      <p>
        Export or delete a team workspace under Settings → Danger zone. Export downloads JSON
        without secrets. Delete removes files from object storage immediately.
      </p>
      <p>
        More detail for the browser extension:
        <NuxtLink class="underline" to="/legal/extension-privacy">extension privacy</NuxtLink>. Data
        deletion: <NuxtLink class="underline" to="/legal/data-deletion">data deletion</NuxtLink>.
      </p>
      <h2 class="mt-4 font-serif text-xl">Contact</h2>
      <p>privacy@kame.apply</p>
    </section>
  </main>
</template>
