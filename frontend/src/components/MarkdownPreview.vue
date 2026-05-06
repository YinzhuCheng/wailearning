<template>
  <div
    class="markdown-content"
    :class="{ 'markdown-content--compact': compact }"
    v-html="html"
  />
</template>

<script setup>
import { computed } from 'vue'

import { renderMarkdownToSafeHtml } from '@/utils/markdownRender'

const props = defineProps({
  source: {
    type: String,
    default: ''
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const html = computed(() => renderMarkdownToSafeHtml(props.source || ''))
</script>
