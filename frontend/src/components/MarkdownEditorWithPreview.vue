<template>
  <div class="md-editor-preview">
    <el-input
      :model-value="modelValue"
      type="textarea"
      :rows="rows"
      :placeholder="placeholder"
      @update:model-value="emit('update:modelValue', $event)"
    />
    <div class="md-editor-preview__bar">
      <span class="md-editor-preview__hint">{{ hintText }}</span>
      <el-button type="primary" link @click="openPreview">预览渲染效果</el-button>
    </div>
    <el-dialog
      v-model="previewVisible"
      :title="`预览：${fieldLabel}`"
      width="min(820px, 94vw)"
      append-to-body
      destroy-on-close
      class="md-preview-dialog"
    >
      <el-alert
        type="info"
        :closable="false"
        class="md-preview-dialog__alert"
        title="以下为保存前预览：Markdown 与 LaTeX（$…$、$$…$$、\\(…\\)、\\[…\\]）将按学生端相近方式渲染。"
      />
      <div v-if="!trimmedSource" class="md-preview-dialog__empty">（当前为空）</div>
      <MarkdownPreview v-else :source="modelValue" />
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

import MarkdownPreview from '@/components/MarkdownPreview.vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  rows: {
    type: Number,
    default: 6
  },
  placeholder: {
    type: String,
    default: ''
  },
  fieldLabel: {
    type: String,
    default: '内容'
  },
  hintText: {
    type: String,
    default: '支持 Markdown；公式可使用 $行内$、$$独立公式$$、\\(行内\\)、\\[块级\\]。'
  }
})

const emit = defineEmits(['update:modelValue'])

const previewVisible = ref(false)
const trimmedSource = computed(() => (props.modelValue || '').trim())

const openPreview = () => {
  previewVisible.value = true
}
</script>

<style scoped>
.md-editor-preview__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.md-editor-preview__hint {
  font-size: 12px;
  color: #64748b;
  line-height: 1.45;
  flex: 1;
  min-width: 200px;
}

.md-preview-dialog__alert {
  margin-bottom: 14px;
}

.md-preview-dialog__empty {
  color: #94a3b8;
  font-size: 14px;
  padding: 12px 0;
}
</style>
