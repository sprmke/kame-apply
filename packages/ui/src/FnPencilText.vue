<script setup lang="ts">
/** AI-drafted text is pencil until the user accepts it; accepted text is ink. */
withDefaults(defineProps<{ state?: "draft" | "ink"; draftLabel?: string }>(), { state: "draft" });
</script>

<template>
  <span
    class="transition-colors duration-200 ease-[var(--ease-steady)]"
    :class="
      state === 'draft'
        ? 'text-pencil underline decoration-pencil decoration-dashed underline-offset-4'
        : 'text-ink-900'
    "
  >
    <slot />
    <span
      v-if="state === 'draft'"
      class="ml-1.5 align-middle font-mono text-[0.625rem] tracking-wide text-pencil uppercase"
    >
      {{ draftLabel ?? "Draft" }}
    </span>
  </span>
</template>
