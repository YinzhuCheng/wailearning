<template>
  <div class="md-panel">
    <div v-if="isMarkdown" class="md-panel__toolbar">
      <el-button size="small" :disabled="disabled" @click="insertHeading('## ')">标题</el-button>
      <el-button size="small" :disabled="disabled" @click="insertBold">加粗</el-button>
      <el-button size="small" :disabled="disabled" @click="insertList">列表</el-button>
      <el-button size="small" :disabled="disabled" @click="insertCode">代码</el-button>
      <el-upload
        v-if="enableImageUpload"
        class="md-panel__upload"
        :auto-upload="false"
        :show-file-list="false"
        accept="image/*,.jpg,.jpeg,.png,.gif,.webp,.bmp"
        :disabled="disabled"
        :on-change="onImagePick"
      >
        <el-button size="small" :loading="uploading" :disabled="disabled">上传图片</el-button>
      </el-upload>
      <el-button size="small" :disabled="disabled" @click="promptImageUrl">图片链接</el-button>
    </div>
    <el-input
      ref="inputRef"
      :model-value="modelValue"
      type="textarea"
      :autosize="{ minRows, maxRows }"
      :placeholder="effectivePlaceholder"
      :disabled="disabled"
      class="md-panel__input"
      :data-testid="dataTestid || undefined"
      @update:model-value="v => $emit('update:modelValue', v)"
    />
    <div v-if="hint" class="md-panel__hint">{{ hint }}</div>
    <div v-if="showFormatToggle" class="md-panel__format">
      <span class="md-panel__format-label">正文格式</span>
      <el-radio-group
        :model-value="contentFormat"
        size="small"
        :disabled="disabled"
        @update:model-value="onContentFormatChange"
      >
        <el-radio-button label="markdown">Markdown</el-radio-button>
        <el-radio-button label="plain">纯文本</el-radio-button>
      </el-radio-group>
      <span v-if="contentFormat === 'plain'" class="md-panel__format-note">
        纯文本不会解析 *、# 等符号为排版；换行将原样保留。
      </span>
    </div>
    <template v-if="isMarkdown">
      <div class="md-panel__preview-label">预览</div>
      <div class="md-panel__preview">
        <RichMarkdownDisplay :markdown="modelValue" variant="student" empty-text="（空）" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import RichMarkdownDisplay from '@/components/RichMarkdownDisplay.vue'
import { validateAttachmentFile } from '@/utils/attachments'

const props = defineProps({
  modelValue: { type: String, default: '' },
  /** `markdown` | `plain` — plain disables MD preview and toolbar. */
  contentFormat: { type: String, default: 'markdown' },
  placeholder: { type: String, default: '' },
  hint: { type: String, default: '' },
  minRows: { type: Number, default: 6 },
  maxRows: { type: Number, default: 22 },
  enableImageUpload: { type: Boolean, default: true },
  showFormatToggle: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  /** Optional for E2E / automation */
  dataTestid: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'update:contentFormat'])

const inputRef = ref(null)
const uploading = ref(false)

const isMarkdown = computed(() => (props.contentFormat || 'markdown') === 'markdown')

const effectivePlaceholder = computed(() => {
  if (!isMarkdown.value) {
    return props.placeholder || '输入正文（纯文本）'
  }
  return props.placeholder || ''
})

const getTextarea = () => inputRef.value?.textarea

const emitUpdate = v => emit('update:modelValue', v)

const insertAtCursor = snippet => {
  const ta = getTextarea()
  const cur = props.modelValue || ''
  if (!ta || typeof ta.selectionStart !== 'number') {
    emitUpdate((cur || '') + snippet)
    return
  }
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const next = cur.slice(0, start) + snippet + cur.slice(end)
  emitUpdate(next)
  const pos = start + snippet.length
  queueMicrotask(() => {
    const t2 = getTextarea()
    if (t2) {
      t2.focus()
      t2.selectionStart = t2.selectionEnd = pos
    }
  })
}

const insertHeading = prefix => insertAtCursor(`\n${prefix}`)
const insertBold = () => insertAtCursor('**加粗**')
const insertList = () => insertAtCursor('\n- 条目\n')
const insertCode = () => insertAtCursor('\n```\n代码\n```\n')

const onImagePick = async uploadFile => {
  const file = uploadFile.raw
  const result = validateAttachmentFile(file, { imageOnly: true })
  if (!result.valid) {
    ElMessage.error(result.message)
    return false
  }
  uploading.value = true
  try {
    const uploaded = await api.files.upload(file)
    const url = uploaded?.attachment_url || ''
    if (!url) {
      ElMessage.error('上传失败')
      return false
    }
    const name = (file.name || 'image').replace(/]/g, '')
    insertAtCursor(`\n![${name}](${url})\n`)
    ElMessage.success('已插入图片')
  } catch (e) {
    console.error(e)
  } finally {
    uploading.value = false
  }
  return false
}

const promptImageUrl = async () => {
  try {
    const { value } = await ElMessageBox.prompt('请输入图片 URL（https 推荐）', '插入图片链接', {
      confirmButtonText: '插入',
      cancelButtonText: '取消',
      inputPlaceholder: 'https://...'
    })
    const url = (value || '').trim()
    if (!url) {
      return
    }
    insertAtCursor(`\n![](${url})\n`)
  } catch {
    /* cancel */
  }
}

const onContentFormatChange = v => {
  const next = v === 'plain' ? 'plain' : 'markdown'
  if (next === 'plain' && (props.modelValue || '').trim()) {
    ElMessage.info('已切换为纯文本：正文将按字面显示，不再作为 Markdown 解析。')
  }
  emit('update:contentFormat', next)
}
</script>

<style scoped>
.md-panel {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}

.md-panel__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.md-panel__upload {
  display: inline-block;
}

.md-panel__input :deep(.el-textarea__inner) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 13px;
  border: none;
  box-shadow: none;
  border-radius: 0;
}

.md-panel__hint {
  padding: 6px 12px 0;
  font-size: 12px;
  color: #64748b;
}

.md-panel__format {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  padding: 8px 12px;
  border-top: 1px dashed #e2e8f0;
  background: #fafbfc;
}

.md-panel__format-label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.md-panel__format-note {
  flex: 1 1 220px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.45;
}

.md-panel__preview-label {
  padding: 8px 12px 0;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.md-panel__preview {
  padding: 8px 12px 12px;
  max-height: 280px;
  overflow-y: auto;
  border-top: 1px dashed #e2e8f0;
  margin-top: 6px;
  background: #fafbfc;
}
</style>
