<script setup lang="ts">
import {
  FnButton,
  FnCheckbox,
  FnChip,
  FnCommandBar,
  FnDialog,
  FnField,
  FnFolderTab,
  FnGradeRing,
  FnInput,
  FnMenu,
  FnPencilText,
  FnPopover,
  FnProofMark,
  FnRiskSeal,
  FnRouteLine,
  FnSelect,
  FnSkeleton,
  FnTable,
  FnTabs,
  FnTextarea,
  FnToaster,
  FnTooltip,
  useToast,
} from "@kame/ui";

definePageMeta({ layout: false });
const { public: cfg } = useRuntimeConfig();
if (!import.meta.dev && !cfg.enableDesign)
  throw createError({ statusCode: 404, statusMessage: "Not Found" });

const { choice, set } = useTheme();
const toast = useToast();
const dialogOpen = ref(false);
const sheetOpen = ref(false);
const cmdOpen = ref(false);
const tab = ref("one");
const sel = ref("b");
const checked = ref(true);
const text = ref("Hello");
const draftAccepted = ref(false);

const swatches = [
  ["paper-0", "bg-paper-0"],
  ["paper-1", "bg-paper-1"],
  ["paper-2", "bg-paper-2"],
  ["rule", "bg-rule"],
  ["edge", "bg-edge"],
  ["ink-900", "bg-ink-900"],
  ["ink-600", "bg-ink-600"],
  ["ink-400", "bg-ink-400"],
  ["persimmon-500", "bg-persimmon-500"],
  ["persimmon-700", "bg-persimmon-700"],
  ["pencil", "bg-pencil"],
  ["fern-600", "bg-fern-600"],
  ["saffron-600", "bg-saffron-600"],
  ["oxblood-600", "bg-oxblood-600"],
  ["track-1", "bg-track-1"],
  ["track-2", "bg-track-2"],
  ["track-3", "bg-track-3"],
  ["track-4", "bg-track-4"],
  ["track-5", "bg-track-5"],
  ["track-6", "bg-track-6"],
  ["track-7", "bg-track-7"],
  ["track-8", "bg-track-8"],
];
const cols = [
  { key: "role", label: "Role" },
  { key: "count", label: "Count", align: "right" as const },
  { key: "id", label: "Id", mono: true },
];
const rows = [
  { id: "a1", role: "Owner", count: 1 },
  { id: "b2", role: "Member", count: 12 },
];
const menu = [
  { label: "Rename", onSelect: () => {} },
  { type: "separator" as const },
  { label: "Delete", tone: "danger" as const, onSelect: () => {} },
];
const commands = [
  { id: "a", label: "Go to Today", group: "Go to" },
  { id: "b", label: "Go to Jobs", group: "Go to" },
  { id: "c", label: "Switch theme", group: "Actions" },
];
const tabs = [
  { value: "one", label: "Overview" },
  { value: "two", label: "Evidence" },
  { value: "three", label: "Notes" },
];
const opts = [
  { value: "a", label: "Alpha" },
  { value: "b", label: "Bravo" },
  { value: "c", label: "Charlie" },
];
</script>

<template>
  <div class="min-h-dvh bg-paper-0 px-4 py-8 text-ink-900 md:px-10" data-testid="design-root">
    <div class="mx-auto flex max-w-5xl flex-col gap-12">
      <header class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <BrandMark wordmark />
          <h1 class="mt-3 font-serif text-[length:var(--text-display)] leading-tight font-semibold">
            Field Notes
          </h1>
          <p class="max-w-prose font-serif text-lg text-ink-600">
            Living style guide. Every component and state, in the current theme.
          </p>
        </div>
        <div class="flex gap-2">
          <FnButton
            v-for="c in ['system', 'light', 'dark'] as const"
            :key="c"
            size="sm"
            :tone="choice === c ? 'primary' : 'quiet'"
            @click="set(c)"
            >{{ c }}</FnButton
          >
        </div>
      </header>

      <section aria-labelledby="d-color" class="flex flex-col gap-3">
        <h2 id="d-color" class="font-serif text-xl font-semibold">Color</h2>
        <ul class="grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-6">
          <li v-for="[name, cls] in swatches" :key="name" class="flex flex-col gap-1">
            <span class="h-12 rounded-sm border border-rule" :class="cls" />
            <span class="font-mono text-[0.6875rem] text-ink-600">{{ name }}</span>
          </li>
        </ul>
      </section>

      <section aria-labelledby="d-type" class="flex flex-col gap-2">
        <h2 id="d-type" class="font-serif text-xl font-semibold">Type</h2>
        <p class="font-serif text-[length:var(--text-display)] leading-tight">Newsreader display</p>
        <p class="font-serif text-xl">Documents and briefs set in Newsreader</p>
        <p class="text-base">Instrument Sans carries the interface at 14px.</p>
        <p class="font-mono text-xs">Martian Mono 0123456789 for data and logs</p>
      </section>

      <section aria-labelledby="d-buttons" class="flex flex-col gap-3">
        <h2 id="d-buttons" class="font-serif text-xl font-semibold">Buttons</h2>
        <div class="flex flex-wrap items-center gap-3">
          <FnButton tone="primary">Primary</FnButton>
          <FnButton>Quiet</FnButton>
          <FnButton tone="ghost">Ghost</FnButton>
          <FnButton tone="danger">Danger</FnButton>
          <FnButton size="sm">Small</FnButton>
          <FnButton tone="primary" loading>Loading</FnButton>
          <FnButton disabled>Disabled</FnButton>
        </div>
      </section>

      <section aria-labelledby="d-forms" class="flex flex-col gap-4">
        <h2 id="d-forms" class="font-serif text-xl font-semibold">Forms</h2>
        <div class="grid gap-4 md:grid-cols-2">
          <FnField v-slot="{ id, describedby, invalid }" label="Text" hint="A short hint">
            <FnInput
              :id="id"
              v-model="text"
              :describedby="describedby"
              :invalid="invalid"
              placeholder="Placeholder"
            />
          </FnField>
          <FnField
            v-slot="{ id, describedby, invalid }"
            label="With error"
            error="Enter a valid email"
          >
            <FnInput :id="id" model-value="nope" :describedby="describedby" :invalid="invalid" />
          </FnField>
          <FnField v-slot="{ id }" label="Disabled"
            ><FnInput :id="id" model-value="Read only" disabled
          /></FnField>
          <FnField v-slot="{ id }" label="Select"
            ><FnSelect :id="id" v-model="sel" :options="opts"
          /></FnField>
          <FnField v-slot="{ id }" label="Textarea"
            ><FnTextarea :id="id" model-value="Notes go here" :rows="3"
          /></FnField>
          <div class="flex flex-col justify-center">
            <FnCheckbox v-model="checked" label="Remember this device" />
          </div>
        </div>
      </section>

      <section aria-labelledby="d-chips" class="flex flex-col gap-3">
        <h2 id="d-chips" class="font-serif text-xl font-semibold">Chips and tabs</h2>
        <div class="flex flex-wrap gap-2">
          <FnChip>Neutral</FnChip><FnChip tone="accent">Accent</FnChip
          ><FnChip tone="pencil">Pencil</FnChip
          ><FnChip removable remove-label="Remove Manila">Manila</FnChip>
        </div>
        <FnTabs v-model="tab" :items="tabs" label="Example tabs">
          <template #one><p class="text-sm text-ink-600">Overview content</p></template>
          <template #two><p class="text-sm text-ink-600">Evidence content</p></template>
          <template #three><p class="text-sm text-ink-600">Notes content</p></template>
        </FnTabs>
      </section>

      <section aria-labelledby="d-overlays" class="flex flex-col gap-3">
        <h2 id="d-overlays" class="font-serif text-xl font-semibold">Overlays</h2>
        <div class="flex flex-wrap gap-3">
          <FnButton @click="dialogOpen = true">Dialog</FnButton>
          <FnButton @click="sheetOpen = true">Sheet</FnButton>
          <FnButton @click="cmdOpen = true">Command bar</FnButton>
          <FnButton
            @click="
              toast.push({ title: 'Saved', description: 'Your change is live', tone: 'success' })
            "
            >Toast</FnButton
          >
          <FnTooltip text="A short tooltip"><FnButton>Tooltip</FnButton></FnTooltip>
          <FnPopover
            ><template #trigger><FnButton>Popover</FnButton></template
            >Popover content with a sentence in it.</FnPopover
          >
          <FnMenu :items="menu"><FnButton>Menu</FnButton></FnMenu>
        </div>
        <FnDialog
          v-model:open="dialogOpen"
          title="Dialog title"
          description="A dialog explains one decision."
          close-label="Close"
        >
          <p class="text-sm">Body text.</p>
          <template #footer
            ><FnButton @click="dialogOpen = false">Cancel</FnButton
            ><FnButton tone="primary" @click="dialogOpen = false">Confirm</FnButton></template
          >
        </FnDialog>
        <FnDialog
          v-model:open="sheetOpen"
          variant="sheet"
          title="Sheet title"
          description="Bottom sheet on phones, side sheet on larger screens."
          close-label="Close"
        >
          <p class="text-sm">Sheet body.</p>
        </FnDialog>
        <FnCommandBar
          v-model:open="cmdOpen"
          :items="commands"
          title="Command bar"
          placeholder="Go to or do something"
          empty="No matches"
        />
      </section>

      <section aria-labelledby="d-data" class="flex flex-col gap-3">
        <h2 id="d-data" class="font-serif text-xl font-semibold">Table and loading</h2>
        <FnTable :columns="cols" :rows="rows" row-key="id" caption="Example table" />
        <FnTable
          :columns="cols"
          :rows="[]"
          row-key="id"
          caption="Empty table"
          empty="Nothing here yet"
        />
        <FnSkeleton :lines="3" />
      </section>

      <section aria-labelledby="d-signature" class="flex flex-col gap-5">
        <h2 id="d-signature" class="font-serif text-xl font-semibold">Signature components</h2>
        <p class="max-w-prose font-serif text-lg leading-relaxed">
          Led the migration of
          <FnProofMark
            :index="1"
            source="Career Profile, Acme 2022"
            quote="Moved 40 services to Kubernetes"
            >forty services</FnProofMark
          >
          and
          <FnPencilText :state="draftAccepted ? 'ink' : 'draft'"
            >cut deploy time by half</FnPencilText
          >.
          <FnButton size="sm" class="ml-2 align-middle" @click="draftAccepted = !draftAccepted">{{
            draftAccepted ? "Revert" : "Accept"
          }}</FnButton>
        </p>
        <FnRouteLine
          :steps="['Found', 'Shortlisted', 'Tailored', 'Applied', 'Responded']"
          :active="2"
          label="Application progress"
        />
        <div class="flex flex-wrap items-center gap-4">
          <FnRiskSeal level="clear" label="Clear" /><FnRiskSeal
            level="caution"
            label="Caution"
          /><FnRiskSeal level="danger" label="Danger" />
          <FnGradeRing grade="A-" from="C" simulation-label="Simulation" />
        </div>
        <div class="flex border-b border-rule">
          <FnFolderTab :hue="1" active>Platform engineer</FnFolderTab
          ><FnFolderTab :hue="5">Data roles</FnFolderTab
          ><FnFolderTab :hue="7">Remote only</FnFolderTab>
        </div>
      </section>
    </div>
    <FnToaster />
  </div>
</template>
