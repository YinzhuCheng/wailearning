<template>
  <div class="material-read-page" :class="`material-read-page--${materialPresentationStyle}`" v-loading="loading">
    <div class="material-read-layout" v-if="material">
      <aside class="material-read-outline">
        <div class="material-read-outline__head">
          <span class="material-read-outline__eyebrow">教材目录</span>
          <strong>{{ currentChapterTitle }}</strong>
        </div>
        <div class="material-read-outline__list">
          <section
            v-for="chapter in outlineTree"
            :key="chapter.id"
            class="material-read-outline__chapter"
          >
            <div
              class="material-read-outline__chapter-title"
              :style="{ paddingLeft: `${chapter.depth * 14}px` }"
            >
              {{ chapter.title }}
            </div>
            <div class="material-read-outline__entries">
              <button
                v-for="entry in chapter.entries"
                :key="entry.id"
                type="button"
                class="material-read-outline__item"
                :class="{ 'material-read-outline__item--active': String(entry.id) === String(route.params.id) }"
                :style="{ marginLeft: `${chapter.depth * 14}px` }"
                @click="goEntry(entry.id)"
              >
                <span class="material-read-outline__index">{{ entry.indexLabel }}</span>
                <span class="material-read-outline__title">{{ entry.title }}</span>
              </button>
            </div>
          </section>
        </div>
      </aside>

      <section class="material-read-main">
        <div class="material-read-toolbar">
          <el-button @click="goBack">返回目录</el-button>
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

        <article class="material-read-body">
          <h1 class="material-read-title">{{ material.title }}</h1>
          <div class="material-read-actions">
            <button type="button" class="material-read-actions__link" @click="scrollToDiscussion">
              进入讨论区
            </button>
            <span class="material-read-actions__divider" aria-hidden="true" />
            <span class="material-read-actions__hint">讨论区在正文下方，可边读边提问。</span>
            <el-button
              v-if="material.attachment_url"
              class="material-read-actions__attachment"
              type="primary"
              link
              size="small"
              @click="downloadAttach"
            >
              {{ material.attachment_name || '下载附件' }}
            </el-button>
          </div>
          <div v-if="breadcrumb" class="material-read-meta">{{ breadcrumb }}</div>
          <div class="material-read-prose">
            <PlainOrMarkdownBlock
              :text="material.content"
              :format="material.content_format"
              variant="student"
              empty-text="暂无正文"
            />
          </div>
        </article>

        <section v-if="material.attachment_url" class="material-read-note" aria-label="配套附件">
          <strong class="material-read-note__title">配套附件</strong>
          <p class="material-read-note__body">如需原始讲义、PDF、课件或表格文件，可从这里下载。</p>
          <el-button class="material-read-actions__attachment" type="primary" link size="small" @click="downloadAttach">
            {{ material.attachment_name || '下载附件' }}
          </el-button>
        </section>

        <section ref="discussionSection" class="material-read-discussion" aria-label="资料讨论区">
          <CourseDiscussionPanel
            target-type="material"
            :target-id="material.id"
            :subject-id="material.subject_id"
            :class-id="material.class_id"
            :discussion-requires-context="material.discussion_requires_context"
            :is-student="userStore.isStudent"
          />
        </section>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import api from '@/api'
import CourseDiscussionPanel from '@/components/CourseDiscussionPanel.vue'
import PlainOrMarkdownBlock from '@/components/PlainOrMarkdownBlock.vue'
import { useUserStore } from '@/stores/user'
import { downloadAttachment } from '@/utils/attachments'
import { normalizeContentFormat } from '@/utils/contentFormat'
import { loadAllPages } from '@/utils/pagedFetch'
import {
  getMaterialPresentationStyle,
  MATERIAL_PRESENTATION_EVENT
} from '@/utils/materialPresentation'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const material = ref(null)
/** Flat navigation entries for this course: chapter DFS × materials sort order */
const sequence = ref([])
const materialPresentationStyle = ref(getMaterialPresentationStyle())
const outlineTree = ref([])
const discussionSection = ref(null)

const flattenChaptersDfs = (nodes, depth = 0) => {
  const out = []
  const walk = (list, level) => {
    for (const n of list || []) {
      out.push({ id: n.id, title: n.title, is_uncategorized: Boolean(n.is_uncategorized), depth: level })
      if (n.children?.length) walk(n.children, level + 1)
    }
  }
  walk(nodes || [], depth)
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
  const outline = []
  for (const ch of chapters) {
    const rows = await loadAllPages(pager =>
      api.materials.list({
        class_id: course.class_id,
        subject_id: course.id,
        chapter_id: ch.id,
        ...pager
      })
    )
    const entries = []
    let index = 0
    for (const row of rows || []) {
      index += 1
      const entry = {
        id: row.id,
        title: row.title,
        chapterTitle: ch.title,
        chapterId: ch.id,
        indexLabel: `${index}`.padStart(2, '0')
      }
      seq.push({
        ...entry
      })
      entries.push(entry)
    }
    if (entries.length) {
      outline.push({
        id: ch.id,
        title: ch.is_uncategorized ? '资料库 / 未归档' : ch.title,
        depth: ch.depth || 0,
        entries
      })
    }
  }
  sequence.value = seq
  outlineTree.value = outline
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

const currentChapterTitle = computed(() => {
  const cur = sequence.value.find(x => String(x.id) === String(material.value?.id))
  return cur?.chapterTitle || '当前章节'
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
    const row = await api.materials.get(id)
    const subjectId = row.subject_id != null ? Number(row.subject_id) : null
    // Deep links (and Playwright flows that clear localStorage) may not have selected_course
    // matching this material; sync from teaching/enrollment list when possible.
    if (subjectId && Number(userStore.selectedCourse?.id) !== subjectId) {
      await userStore.fetchTeachingCourses(true)
      const match = userStore.teachingCourses.find(c => Number(c.id) === subjectId)
      if (!match) {
        ElMessage.warning('无法在您的可选课程列表中找到该资料所属课程，请从课程入口打开。')
        router.push('/materials')
        return
      }
      userStore.setSelectedCourse(match)
    }
    material.value = {
      ...row,
      content_format: normalizeContentFormat(row.content_format)
    }
    try {
      await buildSequence()
    } catch (seqErr) {
      console.error(seqErr)
      ElMessage.warning('章节导航加载失败，仍可阅读正文')
      sequence.value = []
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

const goEntry = id => {
  router.replace({ name: 'MaterialRead', params: { id } })
}

const downloadAttach = () => {
  if (!material.value?.attachment_url) return
  downloadAttachment(material.value.attachment_url, material.value.attachment_name)
}

const scrollToDiscussion = () => {
  discussionSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

watch(
  () => route.params.id,
  () => {
    loadMaterial()
  },
  { immediate: true }
)

const handleMaterialPresentationStyleChange = event => {
  materialPresentationStyle.value = event?.detail || getMaterialPresentationStyle()
}

onMounted(() => {
  if (typeof window !== 'undefined') {
    window.addEventListener(MATERIAL_PRESENTATION_EVENT, handleMaterialPresentationStyleChange)
  }
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener(MATERIAL_PRESENTATION_EVENT, handleMaterialPresentationStyleChange)
  }
})
</script>

<style scoped>
.material-read-page {
  padding: 24px;
}

.material-read-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 24px;
  max-width: 1560px;
  margin: 0 auto;
}

.material-read-outline {
  position: sticky;
  top: 20px;
  align-self: start;
  max-height: calc(100vh - 40px);
  overflow: auto;
  padding: 18px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.material-read-outline__head {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 14px;
}

.material-read-outline__eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #64748b;
}

.material-read-outline__list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.material-read-outline__chapter {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.material-read-outline__chapter-title {
  padding: 0 4px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #64748b;
}

.material-read-outline__item {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  width: 100%;
  padding: 10px 12px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #334155;
  text-align: left;
  cursor: pointer;
}

.material-read-outline__item:hover {
  background: rgba(37, 99, 235, 0.06);
}

.material-read-outline__item--active {
  background: rgba(37, 99, 235, 0.1);
  color: #0f172a;
}

.material-read-outline__index {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.material-read-outline__title {
  line-height: 1.55;
}

.material-read-main {
  min-width: 0;
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
  line-height: 1.3;
}

.material-read-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin: 0 0 18px;
}

.material-read-actions__link {
  border: none;
  background: transparent;
  padding: 0;
  color: #1d4ed8;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.material-read-actions__divider {
  width: 1px;
  height: 14px;
  background: #cbd5e1;
}

.material-read-actions__hint {
  color: #64748b;
  font-size: 13px;
}

.material-read-actions__attachment {
  margin-left: auto;
}

.material-read-meta {
  margin: 0 0 18px;
  color: #64748b;
  font-size: 13px;
}

.material-read-prose {
  color: #0f172a;
  font-size: 16px;
  line-height: 1.9;
}

.material-read-prose :deep(h1),
.material-read-prose :deep(h2),
.material-read-prose :deep(h3),
.material-read-prose :deep(h4) {
  font-family: "Noto Serif SC", "Source Han Serif SC", "Songti SC", serif;
  line-height: 1.45;
}

.material-read-prose :deep(p),
.material-read-prose :deep(li),
.material-read-prose :deep(blockquote) {
  line-height: 1.9;
}

.material-read-prose :deep(ul),
.material-read-prose :deep(ol) {
  padding-left: 1.4em;
}

.material-read-prose :deep(blockquote) {
  margin: 1.2em 0;
  padding: 0.85em 1em;
  border-left: 3px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
}

.material-read-note {
  margin-top: 18px;
  padding: 16px 18px;
  border: 1px dashed #dbe3ee;
  border-radius: 14px;
  background: #fbfdff;
}

.material-read-note__title {
  display: block;
  margin-bottom: 6px;
  color: #0f172a;
}

.material-read-note__body {
  margin: 0 0 8px;
  color: #64748b;
  font-size: 14px;
}

.material-read-discussion {
  margin-top: 24px;
  scroll-margin-top: 24px;
}

.material-read-page--reader .material-read-body {
  border-radius: 22px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.04);
}

.material-read-page--reader .material-read-title,
.material-read-page--reader .material-read-outline__title {
  font-family: "Noto Serif SC", "Source Han Serif SC", "Songti SC", serif;
}

.material-read-page--compact .material-read-layout {
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 18px;
  max-width: 1440px;
}

.material-read-page--compact .material-read-outline {
  padding: 14px 12px;
}

.material-read-page--compact .material-read-body {
  padding: 20px 22px;
}

.material-read-page--compact .material-read-prose {
  font-size: 15px;
  line-height: 1.75;
}

@media (max-width: 960px) {
  .material-read-layout {
    grid-template-columns: 1fr;
  }

  .material-read-outline {
    position: static;
    max-height: none;
  }
}
</style>
