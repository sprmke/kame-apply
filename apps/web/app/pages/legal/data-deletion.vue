<script setup lang="ts">
definePageMeta({ layout: false });
</script>

<template>
  <main class="mx-auto max-w-2xl px-4 py-12 text-ink-900">
    <h1 class="font-serif text-3xl font-semibold">Data deletion</h1>
    <p class="mt-4 text-sm text-ink-700">Last updated: 2026-11-01</p>
    <section class="mt-8 flex flex-col gap-3 text-sm leading-relaxed text-ink-800">
      <h2 class="mt-4 font-serif text-xl">Export</h2>
      <p>
        Workspace owners can download a JSON export under Settings → Danger zone. Secrets, tokens,
        and encrypted keys are omitted. File bytes stay in object storage until you delete.
      </p>
      <h2 class="mt-4 font-serif text-xl">Delete a team workspace</h2>
      <p>
        The owner types the workspace name to confirm. Object storage under that workspace is
        removed immediately. The workspace is hidden from members and hard-removed after 30 days.
      </p>
      <h2 class="mt-4 font-serif text-xl">Personal workspace</h2>
      <p>
        Your personal workspace cannot be deleted on its own while the account exists. Contact
        privacy@kame.apply to close the account and remove personal workspace data.
      </p>
      <h2 class="mt-4 font-serif text-xl">Backups</h2>
      <p>
        Nightly database backups may retain deleted rows until the backup retention window ends (14
        daily and 8 weekly copies).
      </p>
    </section>
  </main>
</template>
