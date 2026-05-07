<template>
  <el-avatar
    :size="size"
    :src="avatarSrc || undefined"
    class="discussion-author-avatar"
    :style="{ backgroundColor: fallbackColor }"
  >
    {{ fallbackText }}
  </el-avatar>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { fetchAttachmentBlobUrl } from '@/utils/attachments'

const props = defineProps({
  avatarUrl: { type: String, default: '' },
  name: { type: String, default: '' },
  role: { type: String, default: '' },
  messageKind: { type: String, default: 'human' },
  size: { type: Number, default: 36 },
})

const avatarSrc = ref('')
let avatarBlobUrl = ''

const fallbackText = computed(() => {
  if (props.messageKind === 'llm_assistant') return '助'
  const name = (props.name || '').trim()
  if (name) return name.charAt(0)
  return ({ admin: '管', class_teacher: '班', teacher: '师', student: '学' }[props.role] || '人')
})

const fallbackColor = computed(() => {
  if (props.messageKind === 'llm_assistant') return '#16a34a'
  return (
    {
      admin: '#7c3aed',
      class_teacher: '#0d9488',
      teacher: '#2563eb',
      student: '#f59e0b',
    }[props.role] || '#64748b'
  )
})

const revokeBlob = () => {
  if (avatarBlobUrl) {
    URL.revokeObjectURL(avatarBlobUrl)
    avatarBlobUrl = ''
  }
  avatarSrc.value = ''
}

const loadAvatar = async () => {
  revokeBlob()
  if (!props.avatarUrl) {
    return
  }
  try {
    avatarBlobUrl = await fetchAttachmentBlobUrl(props.avatarUrl)
    avatarSrc.value = avatarBlobUrl
  } catch {
    revokeBlob()
  }
}

watch(
  () => props.avatarUrl,
  () => {
    loadAvatar()
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  revokeBlob()
})
</script>

<style scoped>
.discussion-author-avatar {
  flex-shrink: 0;
  color: #fff;
  font-weight: 700;
}
</style>
