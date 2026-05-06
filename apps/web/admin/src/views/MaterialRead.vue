<template>
  <div class="material-read-page" v-loading="loading">
    <div class="material-read-toolbar">
      <el-button @click="goBack">返回章节目录</el-button>
      <el-button :disabled="!prevEntry" @click="goPrev">上一篇</el-button>
      <el-button :disabled="!nextEntry" @click="goNext">下一篇</el-button>
    </div>

    <el-alert
      v-if="breadcrumb"
      class="material-read-breadcrumb"
      type="info"
      :closable="false"
      show-icon
      :title="breadcrumb"
    />

    <article v-if="material" class="material-read-body">
      <h1 class="material-read-title">{{ material.title }}</h1>
      <PlainOrMarkdownBlock
        :text="material.content"
        :format="material.content_format"
        variant="student"
        empty-text="暂无正文"
      />
      <div v-if="material.attachment_url" class="material-read-attach">
        <el-button type="primary" link @click="downloadAttach">
          {{ material.attachment_name || '下载附件' }}
        </el-button>
      </div>
    </article>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import api from '@/api'
import PlainOrMarkdownBlock from '@/components/PlainOrMarkdownBlock.vue'
import { useUserStore } from '@/stores/user'
import { downloadAttachment } from '@/utils/attachments'
import { normalizeContentFormat } from '@/utils/contentFormat'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const material = ref(null)
/** Flat navigation entries for this course: chapter DFS × materials sort order */
const sequence = ref([])

const flattenChaptersDfs = nodes => {
  const out = []
  const walk = list => {
    for (const n of list || []) {
      out.push({ id: n.id, title: n.title })
      if (n.children?.length) walk(n.children)
    }
  }
  walk(nodes || [])
  return out
}

const buildSequence = async () => {
  const course = userStore.selectedCourse
  if (!course?.id || !course.class_id) {
    sequence.value = []
    return
  }
  const treeRes = await api.materialChapters.tree({ subject_id: course.id })
  const chapters = flattenChaptersDfs(treeRes?.nodes || [])
  const seq = []
  for (const ch of chapters) {
    const res = await api.materials.list({
      class_id: course.class_id,
      subject_id: course.id,
      chapter_id: ch.id,
      page: 1,
      page_size: 200
    })
    for (const row of res?.data || []) {
      seq.push({
        id: row.id,
        title: row.title,
        chapterTitle: ch.title
      })
    }
  }
  sequence.value = seq
}

const currentIndex = computed(() => sequence.value.findIndex(x => String(x.id) === String(route.params.id)))

const prevEntry = computed(() => {
  const i = currentIndex.value
  return i > 0 ? sequence.value[i - 1] : null
})

const nextEntry = computed(() => {
  const i = currentIndex.value
  return i >= 0 && i < sequence.value.length - 1 ? sequence.value[i + 1] : null
})

const breadcrumb = computed(() => {
  if (!material.value) return ''
  const cur = sequence.value.find(x => String(x.id) === String(material.value.id))
  const ch = cur?.chapterTitle || '—'
  const pos = currentIndex.value >= 0 ? `${currentIndex.value + 1} / ${sequence.value.length}` : ''
  return `当前章节：${ch}${pos ? ` · 阅读顺序 ${pos}` : ''}`
})

const loadMaterial = async () => {
  const id = Number(route.params.id)
  if (!Number.isFinite(id)) {
    ElMessage.error('无效的资料 ID')
    router.push('/materials')
    return
  }
  loading.value = true
  try {
    await buildSequence()
    const row = await api.materials.get(id)
    const subjectId = row.subject_id != null ? Number(row.subject_id) : null
    if (subjectId && userStore.selectedCourse?.id !== subjectId) {
      ElMessage.warning('请先在顶部切换课程后再阅读该资料')
      router.push('/materials')
      return
    }
    material.value = {
      ...row,
      content_format: normalizeContentFormat(row.content_format)
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载资料失败')
    router.push('/materials')
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/materials')
}

const goPrev = () => {
  if (!prevEntry.value) return
  router.replace({ name: 'MaterialRead', params: { id: prevEntry.value.id } })
}

const goNext = () => {
  if (!nextEntry.value) return
  router.replace({ name: 'MaterialRead', params: { id: nextEntry.value.id } })
}

const downloadAttach = () => {
  if (!material.value?.attachment_url) return
  downloadAttachment(material.value.attachment_url, material.value.attachment_name)
}

watch(
  () => route.params.id,
  () => {
    loadMaterial()
  },
  { immediate: true }
)
</script>

<style scoped>
.material-read-page {
  padding: 24px;
  max-width: 920px;
  margin: 0 auto;
}

.material-read-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.material-read-breadcrumb {
  margin-bottom: 16px;
}

.material-read-body {
  padding: 24px 28px;
  border-radius: var(--wa-radius-lg);
  background: #fff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.material-read-title {
  margin: 0 0 16px;
  font-size: 1.65rem;
  font-weight: 700;
  color: #0f172a;
}

.material-read-attach {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed #e2e8f0;
}
</style>
