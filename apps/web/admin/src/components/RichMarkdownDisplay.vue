<template>
  <div
    ref="rootRef"
    class="rich-md"
    :class="variant === 'teacher' ? 'rich-md--teacher' : 'rich-md--student'"
    v-html="renderedHtml"
  />
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import katex from 'katex'
import renderMathInElement from 'katex/contrib/auto-render'
import 'katex/dist/katex.min.css'

import { createCourseMarkdownIt } from '@/utils/markdownIt'

const props = defineProps({
  markdown: { type: String, default: '' },
  variant: { type: String, default: 'student' },
  emptyText: { type: String, default: '暂无内容' }
})

const rootRef = ref(null)
const md = createCourseMarkdownIt()

const renderedHtml = computed(() => {
  const raw = (props.markdown || '').trim()
  if (!raw) {
    return `<p class="rich-md__empty">${escapeHtml(props.emptyText)}</p>`
  }
  return md.render(raw)
})

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const applyMath = () => {
  const el = rootRef.value
  if (!el) return
  try {
    renderMathInElement(el, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '$', right: '$', display: false },
        { left: '\\(', right: '\\)', display: false },
        { left: '\\[', right: '\\]', display: true }
      ],
      throwOnError: false,
      trust: false,
      strict: 'ignore'
    })
  } catch {
    /* ignore */
  }
}

onMounted(async () => {
  await nextTick()
  applyMath()
})

watch(
  () => props.markdown,
  async () => {
    await nextTick()
    applyMath()
  },
  { immediate: true }
)
</script>

<style scoped>
.rich-md {
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
}

.rich-md--student {
  color: #334155;
}

.rich-md--teacher {
  color: #1e293b;
  font-size: 13px;
  line-height: 1.6;
}

.rich-md :deep(h1),
.rich-md :deep(h2),
.rich-md :deep(h3) {
  margin: 0.75em 0 0.35em;
  font-weight: 600;
  color: #0f172a;
}

.rich-md :deep(h1) {
  font-size: 1.15rem;
}
.rich-md :deep(h2) {
  font-size: 1.08rem;
}
.rich-md :deep(h3) {
  font-size: 1.02rem;
}

.rich-md :deep(p) {
  margin: 0.45em 0;
}

.rich-md :deep(ul),
.rich-md :deep(ol) {
  margin: 0.35em 0 0.5em 1.25em;
  padding: 0;
}

.rich-md :deep(li) {
  margin: 0.2em 0;
}

.rich-md :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.35em 0.75em;
  border-left: 3px solid #cbd5e1;
  background: #f8fafc;
  color: #475569;
}

.rich-md :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 0.9em;
  padding: 0.1em 0.35em;
  border-radius: 4px;
  background: #f1f5f9;
  color: #0f172a;
}

.rich-md :deep(pre) {
  margin: 0.5em 0;
  padding: 0.65em 0.85em;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  overflow-x: auto;
}

.rich-md :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
}

.rich-md :deep(a) {
  color: #2563eb;
  text-decoration: none;
}
.rich-md :deep(a:hover) {
  text-decoration: underline;
}

.rich-md :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  margin: 0.35em 0;
  vertical-align: middle;
}

.rich-md :deep(.katex-display) {
  margin: 0.65em 0;
  overflow-x: auto;
}

.rich-md__empty {
  margin: 0;
  color: #94a3b8;
  font-size: 13px;
}
</style>
