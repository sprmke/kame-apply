<script setup lang="ts">
import type { AnswerRead } from "@kame/api-client";
import { FnButton, FnSuggestions, FnTextarea } from "@kame/ui";

const props = defineProps<{ row: AnswerRead; options?: string[] }>();
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
    <FnTextarea
      v-model="text"
      :rows="2"
      :aria-label="t('career.answer')"
      :placeholder="t('career.answerPlaceholder')"
    />
    <FnSuggestions
      v-if="(options ?? []).length"
      :options="options ?? []"
      :label="t('career.commonAnswers')"
      @select="(value) => (text = value)"
    />
    <div>
      <FnButton size="sm" tone="quiet" @click="emit('save', row, text, true)">{{
        t("common.save")
      }}</FnButton>
    </div>
  </div>
</template>
