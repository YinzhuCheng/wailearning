<template>
  <el-card shadow="never" class="discussion-card">
    <template #header>
      <div class="discussion-head">
        <span>讨论区</span>
        <el-text v-if="canUseDiscussion" type="info" size="small">
          实名讨论，每页 {{ effectivePageSize }} 条回复
        </el-text>
      </div>
    </template>

    <el-alert
      v-if="!canUseDiscussion"
      type="warning"
      :closable="false"
      title="该条目未关联课程，无法在课程实例下讨论。请从课程内打开或联系管理员关联课程与班级。"
      show-icon
    />

    <template v-else>
      <div v-loading="loading" class="discussion-body">
        <div v-if="!entries.length && !loading" class="muted-text">暂无讨论，发表第一条回复吧。</div>
        <div v-for="row in entries" :key="row.id" class="discussion-row">
          <div class="discussion-row__meta">
            <span class="discussion-row__name">{{ row.author_real_name }}</span>
            <el-tag size="small" effect="plain">{{ roleLabel(row.author_role) }}</el-tag>
            <span class="discussion-row__time">{{ formatTime(row.created_at) }}</span>
          </div>
          <div
            class="discussion-row__body"
            :class="{
              'discussion-row__body--clickable': isTruncated(row.body) && !isExpanded(row.id)
            }"
            @click="onBodyClick(row)"
          >
            <span class="discussion-row__text">{{ displayBody(row) }}</span>
            <button
              v-if="isTruncated(row.body) && isExpanded(row.id)"
              type="button"
              class="discussion-row__collapse-btn"
              @click.stop="collapseRow(row.id)"
            >
              收起
            </button>
          </div>
          <div v-if="canDelete(row)" class="discussion-row__actions">
            <el-button type="danger" link size="small" @click="removeEntry(row)">删除</el-button>
          </div>
        </div>

        <el-pagination
          v-if="total > effectivePageSize"
          v-model:current-page="page"
          class="discussion-pager"
          :page-size="effectivePageSize"
          :total="total"
          layout="total, prev, pager, next"
          small
          @current-change="loadList"
        />

        <el-input
          v-model="draft"
          type="textarea"
          :rows="3"
          maxlength="8000"
          show-word-limit
          placeholder="输入讨论内容（需登录，不支持匿名）"
          class="discussion-input"
        />
        <el-button type="primary" :loading="posting" :disabled="!draft.trim()" @click="submit">
          发表回复
        </el-button>
      </div>
    </template>
  </el-card>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'

/** Each segment renders as one logical line: a text line (may be empty) or one image. */
const PREVIEW_LINE_LIMIT = 3

/** Markdown ![alt](url) or HTML <img ...> each counts as one line. */
const INLINE_IMAGE_RE = /!\[[^\]]*\]\([^)]+\)|<img\b[^>]*>/gi

const props = defineProps({
  targetType: {
    type: String,
    required: true,
    validator: v => v === 'homework' || v === 'material'
  },
  targetId: { type: Number, required: true },
  /** When set, used for API scope (course instance). */
  subjectId: { type: Number, default: null },
  classId: { type: Number, default: null },
  /** Backend hint: homework/material not linked to a subject. */
  discussionRequiresContext: { type: Boolean, default: false }
})

const userStore = useUserStore()

const selectedCourse = computed(() => userStore.selectedCourse)

const resolvedSubjectId = computed(() => {
  if (props.subjectId != null && props.subjectId !== '') return Number(props.subjectId)
  const c = selectedCourse.value
  return c?.id != null ? Number(c.id) : null
})

const resolvedClassId = computed(() => {
  if (props.classId != null && props.classId !== '') return Number(props.classId)
  const c = selectedCourse.value
  return c?.class_id != null ? Number(c.class_id) : null
})

const canUseDiscussion = computed(() => {
  if (props.discussionRequiresContext) return false
  return resolvedSubjectId.value != null && resolvedClassId.value != null
})

const effectivePageSize = computed(() => {
  const raw = userStore.userInfo?.discussion_page_size
  const n = raw != null ? Number(raw) : 10
  if (Number.isFinite(n) && n >= 5 && n <= 50) return n
  return 10
})

const loading = ref(false)
const posting = ref(false)
const page = ref(1)
const total = ref(0)
const entries = ref([])
const draft = ref('')
/** entry id -> expanded full body */
const expandedEntryIds = ref(new Set())

const roleLabel = role =>
  ({ admin: '管理员', class_teacher: '班主任', teacher: '教师', student: '学生' }[role] || role || '—')

const formatTime = v => {
  if (!v) return ''
  try {
    return new Date(v).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return String(v)
  }
}

const canDelete = row => {
  const uid = userStore.userInfo?.id
  if (uid != null && Number(row.author_user_id) === Number(uid)) return true
  if (userStore.isAdmin) return true
  if (userStore.isStudent) return false
  return userStore.canManageTeaching
}

/** Markdown ![alt](url) or HTML <img ...> each counts as one line. */
const INLINE_IMAGE_RE = /!\[[^\]]*\]\([^)]+\)|<img\b[^>]*>/gi

/**
 * Split body into line-sized segments: each `\\n`-split text line is one segment;
 * each markdown image and each HTML <img> tag is one segment (in order).
 */
function lineSegmentsFromBody(body) {
  const raw = body == null ? '' : String(body)
  const segments = []
  let last = 0
  let m
  const re = new RegExp(INLINE_IMAGE_RE.source, 'gi')
  while ((m = re.exec(raw)) !== null) {
    if (m.index > last) {
      const chunk = raw.slice(last, m.index)
      for (const line of chunk.split('\n')) {
        segments.push({ kind: 'text', value: line })
      }
    }
    segments.push({ kind: 'image', value: m[0] })
    last = m.index + m[0].length
  }
  if (last < raw.length) {
    for (const line of raw.slice(last).split('\n')) {
      segments.push({ kind: 'text', value: line })
    }
  }
  if (!segments.length) {
    segments.push({ kind: 'text', value: '' })
  }
  return segments
}

/** Rebuild original string from segments (inverse of lineSegmentsFromBody). */
function joinSegments(parts) {
  let s = ''
  for (let i = 0; i < parts.length; i += 1) {
    const seg = parts[i]
    if (seg.kind === 'text' && i > 0 && parts[i - 1].kind === 'text') {
      s += '\n'
    }
    s += seg.value
  }
  return s
}

function isTruncated(body) {
  return lineSegmentsFromBody(body).length > PREVIEW_LINE_LIMIT
}

function isExpanded(id) {
  return expandedEntryIds.value.has(id)
}

function previewText(body) {
  const segs = lineSegmentsFromBody(body)
  if (segs.length <= PREVIEW_LINE_LIMIT) {
    return joinSegments(segs)
  }
  const head = segs.slice(0, PREVIEW_LINE_LIMIT)
  return `${joinSegments(head)}...`
}

function displayBody(row) {
  const body = row?.body ?? ''
  if (isExpanded(row.id)) {
    return body
  }
  return previewText(body)
}

function onBodyClick(row) {
  if (!isTruncated(row.body) || isExpanded(row.id)) {
    return
  }
  const next = new Set(expandedEntryIds.value)
  next.add(row.id)
  expandedEntryIds.value = next
}

function collapseRow(id) {
  const next = new Set(expandedEntryIds.value)
  next.delete(id)
  expandedEntryIds.value = next
}

const loadList = async () => {
  if (!canUseDiscussion.value) return
  loading.value = true
  try {
    const res = await api.discussions.list({
      target_type: props.targetType,
      target_id: props.targetId,
      subject_id: resolvedSubjectId.value,
      class_id: resolvedClassId.value,
      page: page.value,
      page_size: effectivePageSize.value
    })
    total.value = res?.total ?? 0
    entries.value = res?.data ?? []
    expandedEntryIds.value = new Set()
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || '加载讨论失败')
  } finally {
    loading.value = false
  }
}

const submit = async () => {
  const text = draft.value.trim()
  if (!text || !canUseDiscussion.value) return
  posting.value = true
  try {
    await api.discussions.create({
      target_type: props.targetType,
      target_id: props.targetId,
      subject_id: resolvedSubjectId.value,
      class_id: resolvedClassId.value,
      body: text
    })
    draft.value = ''
    const lastPage = Math.max(1, Math.ceil((total.value + 1) / effectivePageSize.value))
    page.value = lastPage
    await loadList()
    ElMessage.success('已发表')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '发表失败')
  } finally {
    posting.value = false
  }
}

const removeEntry = async row => {
  try {
    await ElMessageBox.confirm('确定删除这条讨论吗？', '确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.discussions.delete(row.id)
    ElMessage.success('已删除')
    await loadList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

watch(
  () => [props.targetId, props.targetType, props.subjectId, props.classId, props.discussionRequiresContext],
  () => {
    page.value = 1
    loadList()
  }
)

watch(
  () => userStore.userInfo?.discussion_page_size,
  () => {
    page.value = 1
    loadList()
  }
)

watch(
  () => [resolvedSubjectId.value, resolvedClassId.value],
  () => {
    page.value = 1
    loadList()
  }
)

loadList()
</script>

<style scoped>
.discussion-card {
  margin-top: 16px;
  border-radius: 12px;
}

.discussion-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.discussion-body {
  min-height: 80px;
}

.discussion-row {
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.discussion-row:last-of-type {
  border-bottom: none;
}

.discussion-row__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
}

.discussion-row__name {
  font-weight: 600;
  color: #0f172a;
}

.discussion-row__time {
  color: #94a3b8;
  font-size: 12px;
}

.discussion-row__body {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.55;
  color: #334155;
}

.discussion-row__body--clickable {
  cursor: pointer;
}

.discussion-row__body--clickable:hover .discussion-row__text {
  color: #2563eb;
}

.discussion-row__text {
  display: inline;
  vertical-align: baseline;
}

.discussion-row__collapse-btn {
  margin-left: 8px;
  padding: 0;
  border: none;
  background: none;
  color: var(--el-color-primary);
  font-size: 13px;
  cursor: pointer;
  text-decoration: underline;
  vertical-align: baseline;
}

.discussion-row__collapse-btn:hover {
  color: var(--el-color-primary-light-3);
}

.discussion-row__actions {
  margin-top: 6px;
}

.discussion-pager {
  margin: 12px 0;
  justify-content: flex-end;
}

.discussion-input {
  margin: 12px 0;
}

.muted-text {
  color: #94a3b8;
  font-size: 14px;
}
</style>
