<script setup lang="ts">
definePageMeta({ layout: false });
</script>

<template>
  <main class="mx-auto max-w-2xl px-4 py-12 text-ink-900">
    <h1 class="font-serif text-3xl font-semibold">Kame Apply extension privacy</h1>
    <p class="mt-4 text-sm text-ink-700">Last updated: 2026-11-01</p>

    <section class="mt-8 flex flex-col gap-3 text-sm leading-relaxed text-ink-800">
      <p>
        The Kame Apply browser extension helps you save job postings and fill application forms
        using your Career Profile. It runs in your browser, on pages you open, after you connect it
        to your account.
      </p>
      <h2 class="mt-4 font-serif text-xl">What we collect</h2>
      <p>
        On your explicit click (Save, Autofill, Answer insert, or I applied), the extension may send
        the page URL, job title/company hints, form field labels and types, and drafted answers to
        the Kame Apply API for your workspace. Field values classified as sensitive (government IDs,
        bank/card numbers, full date of birth, and similar) are not autofilled and are not stored.
      </p>
      <h2 class="mt-4 font-serif text-xl">What we do not do</h2>
      <ul class="list-disc space-y-1 pl-5">
        <li>Background scraping of logged-in feeds</li>
        <li>CAPTCHA solving, proxy rotation, or fingerprint spoofing</li>
        <li>Clicking Submit on your behalf</li>
        <li>Reading passwords or payment card fields for storage</li>
      </ul>
      <h2 class="mt-4 font-serif text-xl">Tokens</h2>
      <p>
        Connect issues a revocable extension token stored in the extension's local storage. You can
        revoke it under Settings → Integrations. Tokens are hashed on the server.
      </p>
      <h2 class="mt-4 font-serif text-xl">Contact</h2>
      <p>Questions: privacy@kame.apply</p>
    </section>
  </main>
</template>
