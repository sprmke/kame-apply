<script setup lang="ts">
import type { AnswerRead } from "@kame/api-client";
import { FnButton, FnTextarea } from "@kame/ui";

const props = defineProps<{ row: AnswerRead }>();
const emit = defineEmits<{ save: [row: AnswerRead, text: string, approved: boolean] }>();
const { t } = useI18n();
const text = ref(props.row.answer);
watch(
  () => props.row.answer,
  (v) => {
    text.value = v;
  },
);
</script>

<template>
  <div class="flex flex-col gap-2">
    <FnTextarea v-model="text" :rows="2" :aria-label="t('career.answer')" />
    <div>
      <FnButton size="sm" tone="primary" @click="emit('save', row, text, true)">{{
        t("common.save")
      }}</FnButton>
    </div>
  </div>
</template>
