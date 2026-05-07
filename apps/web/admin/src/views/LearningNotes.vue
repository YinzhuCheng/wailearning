<template>
  <div class="learning-notes-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">学习笔记</h1>
        <p class="page-subtitle">
          新建笔记默认仅本人可见；公开且关联课程时同课程用户可查看，公开但未关联课程时全员可查看。
        </p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="openCreateDialog">新建笔记</el-button>
      </div>
    </div>

    <el-tabs v-model="activeScope" class="notes-tabs" @tab-change="loadNotes">
      <el-tab-pane label="我的笔记" name="mine" />
      <el-tab-pane label="公开笔记" name="public" />
    </el-tabs>

    <div class="notes-layout">
      <aside class="notes-list-panel">
        <div class="notes-filter">
          <el-select v-model="subjectFilter" clearable filterable placeholder="按课程筛选" @change="loadNotes">
            <el-option v-for="course in courseOptions" :key="course.id" :label="course.name" :value="course.id" />
          </el-select>
        </div>

        <el-skeleton v-if="loadingNotes" :rows="5" animated />
        <el-empty v-else-if="!notes.length" description="暂无学习笔记" />
        <article
          v-for="note in notes"
          v-else
          :key="note.id"
          class="note-card"
          :class="{ 'is-active': selectedNote?.id === note.id }"
          @click="selectNote(note)"
        >
          <div class="note-card__head">
            <h2>{{ note.title }}</h2>
            <el-tag size="small" :type="note.visibility === 'course' ? 'success' : 'info'">
              {{ noteVisibilityLabel(note) }}
            </el-tag>
          </div>
          <p>{{ note.description || '暂无说明' }}</p>
          <div class="note-card__meta">
            <span>{{ note.subject_name || '未关联课程' }}</span>
            <span>{{ note.owner_real_name || note.owner_username }}</span>
            <span>{{ formatDate(note.updated_at || note.created_at) }}</span>
          </div>
        </article>
      </aside>

      <section class="note-detail-panel">
        <el-empty v-if="!selectedNote" description="选择一条笔记查看详情" />
        <template v-else>
          <div class="note-detail-head">
            <div>
              <h2>{{ selectedNote.title }}</h2>
              <p>
                {{ selectedNote.subject_name || '未关联课程' }} ·
                {{ selectedNote.owner_real_name || selectedNote.owner_username }} ·
                {{ formatDate(selectedNote.created_at) }}
              </p>
            </div>
            <div class="note-detail-actions" v-if="canEditSelected">
              <el-button @click="openEditDialog">编辑信息</el-button>
              <el-button :type="selectedNote.visibility === 'course' ? 'warning' : 'success'" @click="toggleVisibility">
                {{ visibilityToggleLabel(selectedNote) }}
              </el-button>
              <el-button type="danger" plain @click="deleteSelectedNote">删除</el-button>
            </div>
          </div>

          <div class="note-body-grid">
            <aside class="note-outline">
              <div class="outline-head">
                <h3>笔记大纲</h3>
                <el-button v-if="canEditSelected" text type="primary" size="small" @click="openChapterDialog(null)">
                  添加章节
                </el-button>
              </div>
              <el-empty v-if="!selectedNote.chapters?.length && !selectedNote.loose_resources?.length" description="暂无大纲内容" />
              <div v-else class="outline-tree">
                <NoteChapterNode
                  v-for="chapter in selectedNote.chapters"
                  :key="chapter.id"
                  :node="chapter"
                  :can-edit="canEditSelected"
                  @add-child="openChapterDialog"
                  @edit-chapter="openChapterEditDialog"
                  @delete-chapter="deleteChapter"
                  @add-resource="openResourceDialog"
                  @edit-resource="openResourceEditDialog"
                  @delete-resource="deleteResource"
                />
                <div v-if="selectedNote.loose_resources?.length" class="loose-resource-block">
                  <h4>未归入章节</h4>
                  <div v-for="resource in selectedNote.loose_resources" :key="resource.id" class="resource-row">
                    <strong>{{ resource.title }}</strong>
                    <span>{{ resource.content || resource.attachment_name || '暂无内容' }}</span>
                    <div v-if="canEditSelected" class="row-actions">
                      <el-button link type="primary" @click="openResourceEditDialog(resource)">编辑</el-button>
                      <el-button link type="danger" @click="deleteResource(resource)">删除</el-button>
                    </div>
                  </div>
                </div>
              </div>
            </aside>

            <section class="note-discussion">
              <div class="discussion-head">
                <h3>讨论区</h3>
                <span>{{ discussionScopeLabel(selectedNote) }}</span>
              </div>
              <el-skeleton v-if="discussionLoading" :rows="4" animated />
              <div v-else class="discussion-list">
                <el-empty v-if="!discussionRows.length" description="暂无讨论" />
                <article v-for="row in discussionRows" :key="row.id" class="discussion-row" :class="{ 'is-assistant': row.message_kind === 'llm_assistant' }">
                  <div class="discussion-row__meta">
                    <strong>{{ row.message_kind === 'llm_assistant' ? '智能助教' : row.author_real_name || row.author_username }}</strong>
                    <span>{{ formatDate(row.created_at) }}</span>
                  </div>
                  <p>{{ row.body }}</p>
                </article>
              </div>
              <div class="discussion-compose">
                <el-input
                  v-model="discussionDraft"
                  type="textarea"
                  :rows="4"
                  maxlength="8000"
                  show-word-limit
                  placeholder="写下问题、补充或整理想法。以 @LLM 开头或勾选智能助教可请求回复。"
                />
                <div class="discussion-compose__actions">
                  <el-checkbox v-model="invokeLlm">请求智能助教回复</el-checkbox>
                  <el-button type="primary" :loading="discussionSubmitting" @click="submitDiscussion">发表</el-button>
                </div>
              </div>
            </section>
          </div>
        </template>
      </section>
    </div>

    <el-dialog v-model="noteDialogVisible" :title="editingNote ? '编辑笔记' : '新建学习笔记'" width="680px" destroy-on-close>
      <el-form label-width="112px">
        <el-form-item label="笔记名称">
          <el-input v-model="noteForm.title" maxlength="160" show-word-limit />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="noteForm.description" type="textarea" :rows="3" maxlength="4000" show-word-limit />
        </el-form-item>
        <el-form-item label="关联课程">
          <el-select v-model="noteForm.subject_id" clearable filterable placeholder="可选；未关联时公开笔记对全员可见">
            <el-option v-for="course in courseOptions" :key="course.id" :label="course.name" :value="course.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="可见性">
          <el-radio-group v-model="noteForm.visibility">
            <el-radio label="private">仅本人可见</el-radio>
            <el-radio label="course">公开</el-radio>
          </el-radio-group>
        </el-form-item>
        <template v-if="!editingNote">
          <el-form-item label="复制课程大纲">
            <el-select v-model="noteForm.copy_from_subject_id" clearable filterable placeholder="选择自己参加的课程">
              <el-option v-for="course in courseOptions" :key="course.id" :label="course.name" :value="course.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="复制内容">
            <el-checkbox v-model="noteForm.copy_chapters">复制章节树</el-checkbox>
            <el-checkbox v-model="noteForm.copy_materials" :disabled="!noteForm.copy_chapters">连同章节下资料引用一起复制</el-checkbox>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="noteDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="noteSubmitting" @click="submitNoteForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="chapterDialogVisible" :title="editingChapter ? '编辑章节' : '添加章节'" width="520px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="章节名称">
          <el-input v-model="chapterForm.title" maxlength="160" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chapterDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitChapterForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resourceDialogVisible" :title="editingResource ? '编辑资料' : '添加资料'" width="760px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="资料名称">
          <el-input v-model="resourceForm.title" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="resourceForm.content" type="textarea" :rows="8" />
        </el-form-item>
        <el-form-item label="附件名称">
          <el-input v-model="resourceForm.attachment_name" />
        </el-form-item>
        <el-form-item label="附件地址">
          <el-input v-model="resourceForm.attachment_url" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resourceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitResourceForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'

const NoteChapterNode = defineComponent({
  name: 'NoteChapterNode',
  props: {
    node: { type: Object, required: true },
    canEdit: { type: Boolean, default: false }
  },
  emits: ['add-child', 'edit-chapter', 'delete-chapter', 'add-resource', 'edit-resource', 'delete-resource'],
  setup(props, { emit }) {
    const renderResource = resource =>
      h('div', { class: 'resource-row' }, [
        h('strong', resource.title),
        h('span', resource.content || resource.attachment_name || '暂无内容'),
        props.canEdit
          ? h('div', { class: 'row-actions' }, [
              h('button', { type: 'button', onClick: () => emit('edit-resource', resource) }, '编辑'),
              h('button', { type: 'button', onClick: () => emit('delete-resource', resource) }, '删除')
            ])
          : null
      ])
    return () =>
      h('div', { class: 'chapter-node' }, [
        h('div', { class: 'chapter-node__title' }, [
          h('strong', props.node.title),
          props.canEdit
            ? h('div', { class: 'row-actions' }, [
                h('button', { type: 'button', onClick: () => emit('add-child', props.node.id) }, '子章节'),
                h('button', { type: 'button', onClick: () => emit('add-resource', props.node.id) }, '资料'),
                h('button', { type: 'button', onClick: () => emit('edit-chapter', props.node) }, '编辑'),
                h('button', { type: 'button', onClick: () => emit('delete-chapter', props.node) }, '删除')
              ])
            : null
        ]),
        ...(props.node.resources || []).map(renderResource),
        ...(props.node.children || []).map(child =>
          h(NoteChapterNode, {
            node: child,
            canEdit: props.canEdit,
            onAddChild: id => emit('add-child', id),
            onEditChapter: node => emit('edit-chapter', node),
            onDeleteChapter: node => emit('delete-chapter', node),
            onAddResource: id => emit('add-resource', id),
            onEditResource: resource => emit('edit-resource', resource),
            onDeleteResource: resource => emit('delete-resource', resource)
          })
        )
      ])
  }
})

const userStore = useUserStore()

const activeScope = ref('mine')
const subjectFilter = ref(null)
const notes = ref([])
const selectedNote = ref(null)
const loadingNotes = ref(false)
const discussionRows = ref([])
const discussionLoading = ref(false)
const discussionDraft = ref('')
const invokeLlm = ref(false)
const discussionSubmitting = ref(false)

const noteDialogVisible = ref(false)
const noteSubmitting = ref(false)
const editingNote = ref(null)
const noteForm = ref(defaultNoteForm())

const chapterDialogVisible = ref(false)
const editingChapter = ref(null)
const chapterParentId = ref(null)
const chapterForm = ref({ title: '' })

const resourceDialogVisible = ref(false)
const editingResource = ref(null)
const resourceChapterId = ref(null)
const resourceForm = ref(defaultResourceForm())

const courseOptions = computed(() => userStore.teachingCourses || [])
const canEditSelected = computed(() => selectedNote.value?.owner_user_id === userStore.userInfo?.id)

function noteVisibilityLabel(note) {
  if (note?.visibility !== 'course') return '仅本人可见'
  return note.subject_id ? '同课程公开' : '全员公开'
}

function visibilityToggleLabel(note) {
  if (note?.visibility === 'course') return '取消公开'
  return note?.subject_id ? '公开到同课程' : '公开给全员'
}

function discussionScopeLabel(note) {
  if (note?.visibility !== 'course') return '仅本人和智能助教'
  return note.subject_id ? '同课程用户可参与' : '全员可参与'
}

function defaultNoteForm() {
  return {
    title: '',
    description: '',
    subject_id: userStore.selectedCourse?.id || null,
    visibility: 'private',
    copy_from_subject_id: null,
    copy_chapters: false,
    copy_materials: false
  }
}

function defaultResourceForm() {
  return {
    title: '',
    content: '',
    content_format: 'markdown',
    attachment_name: '',
    attachment_url: ''
  }
}

const loadNotes = async () => {
  loadingNotes.value = true
  try {
    const result = await api.learningNotes.list({
      scope: activeScope.value,
      subject_id: subjectFilter.value || undefined,
      page: 1,
      page_size: 100
    })
    notes.value = result?.data || []
    if (selectedNote.value && !notes.value.some(item => item.id === selectedNote.value.id)) {
      selectedNote.value = null
    }
  } finally {
    loadingNotes.value = false
  }
}

const selectNote = async note => {
  selectedNote.value = await api.learningNotes.get(note.id)
  await loadDiscussion()
}

const reloadSelectedNote = async () => {
  if (!selectedNote.value) return
  selectedNote.value = await api.learningNotes.get(selectedNote.value.id)
  await loadNotes()
}

const loadDiscussion = async () => {
  if (!selectedNote.value) return
  discussionLoading.value = true
  try {
    const result = await api.learningNotes.discussion(selectedNote.value.id, { page: 1, page_size: 100 })
    discussionRows.value = result?.data || []
  } finally {
    discussionLoading.value = false
  }
}

const openCreateDialog = () => {
  editingNote.value = null
  noteForm.value = defaultNoteForm()
  noteDialogVisible.value = true
}

const openEditDialog = () => {
  if (!selectedNote.value) return
  editingNote.value = selectedNote.value
  noteForm.value = {
    title: selectedNote.value.title,
    description: selectedNote.value.description || '',
    subject_id: selectedNote.value.subject_id || null,
    visibility: selectedNote.value.visibility,
    copy_from_subject_id: null,
    copy_chapters: false,
    copy_materials: false
  }
  noteDialogVisible.value = true
}

const submitNoteForm = async () => {
  if (!noteForm.value.title.trim()) {
    ElMessage.warning('请填写笔记名称')
    return
  }
  noteSubmitting.value = true
  try {
    const payload = { ...noteForm.value }
    if (payload.copy_from_subject_id && !payload.subject_id) {
      payload.subject_id = payload.copy_from_subject_id
    }
    if (editingNote.value) {
      selectedNote.value = await api.learningNotes.update(editingNote.value.id, {
        title: payload.title,
        description: payload.description,
        subject_id: payload.subject_id,
        visibility: payload.visibility
      })
    } else {
      selectedNote.value = await api.learningNotes.create(payload)
      activeScope.value = 'mine'
    }
    noteDialogVisible.value = false
    await loadNotes()
    await loadDiscussion()
  } finally {
    noteSubmitting.value = false
  }
}

const toggleVisibility = async () => {
  if (!selectedNote.value) return
  const next = selectedNote.value.visibility === 'course' ? 'private' : 'course'
  selectedNote.value = await api.learningNotes.update(selectedNote.value.id, {
    visibility: next,
    subject_id: selectedNote.value.subject_id
  })
  await loadNotes()
}

const deleteSelectedNote = async () => {
  if (!selectedNote.value) return
  await ElMessageBox.confirm('删除后无法恢复，确认删除这条学习笔记？', '删除学习笔记', { type: 'warning' })
  await api.learningNotes.delete(selectedNote.value.id)
  selectedNote.value = null
  discussionRows.value = []
  await loadNotes()
}

const openChapterDialog = parentId => {
  editingChapter.value = null
  chapterParentId.value = parentId
  chapterForm.value = { title: '' }
  chapterDialogVisible.value = true
}

const openChapterEditDialog = chapter => {
  editingChapter.value = chapter
  chapterParentId.value = chapter.parent_id || null
  chapterForm.value = { title: chapter.title }
  chapterDialogVisible.value = true
}

const submitChapterForm = async () => {
  if (!selectedNote.value || !chapterForm.value.title.trim()) return
  if (editingChapter.value) {
    selectedNote.value = await api.learningNotes.updateChapter(selectedNote.value.id, editingChapter.value.id, {
      title: chapterForm.value.title
    })
  } else {
    await api.learningNotes.createChapter(selectedNote.value.id, {
      title: chapterForm.value.title,
      parent_id: chapterParentId.value
    })
    await reloadSelectedNote()
  }
  chapterDialogVisible.value = false
}

const deleteChapter = async chapter => {
  await ElMessageBox.confirm('删除章节后，章节下资料会变为未归入章节。确认继续？', '删除章节', { type: 'warning' })
  selectedNote.value = await api.learningNotes.deleteChapter(selectedNote.value.id, chapter.id)
}

const openResourceDialog = chapterId => {
  editingResource.value = null
  resourceChapterId.value = chapterId
  resourceForm.value = defaultResourceForm()
  resourceDialogVisible.value = true
}

const openResourceEditDialog = resource => {
  editingResource.value = resource
  resourceChapterId.value = resource.chapter_id || null
  resourceForm.value = {
    title: resource.title,
    content: resource.content || '',
    content_format: resource.content_format || 'markdown',
    attachment_name: resource.attachment_name || '',
    attachment_url: resource.attachment_url || ''
  }
  resourceDialogVisible.value = true
}

const submitResourceForm = async () => {
  if (!selectedNote.value || !resourceForm.value.title.trim()) return
  const payload = {
    ...resourceForm.value,
    chapter_id: resourceChapterId.value
  }
  if (editingResource.value) {
    selectedNote.value = await api.learningNotes.updateResource(selectedNote.value.id, editingResource.value.id, payload)
  } else {
    selectedNote.value = await api.learningNotes.createResource(selectedNote.value.id, payload)
  }
  resourceDialogVisible.value = false
}

const deleteResource = async resource => {
  await ElMessageBox.confirm('确认删除这条笔记资料？', '删除资料', { type: 'warning' })
  selectedNote.value = await api.learningNotes.deleteResource(selectedNote.value.id, resource.id)
}

const submitDiscussion = async () => {
  if (!selectedNote.value || !discussionDraft.value.trim()) return
  discussionSubmitting.value = true
  try {
    await api.learningNotes.createDiscussion(selectedNote.value.id, {
      body: discussionDraft.value,
      body_format: 'markdown',
      invoke_llm: invokeLlm.value || discussionDraft.value.trim().startsWith('@LLM')
    })
    discussionDraft.value = ''
    invokeLlm.value = false
    await loadDiscussion()
    ElMessage.success('已发表')
  } finally {
    discussionSubmitting.value = false
  }
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', { hour12: false })
}

watch(subjectFilter, loadNotes)

onMounted(async () => {
  await userStore.fetchTeachingCourses(true)
  await loadNotes()
})
</script>

<style scoped>
.learning-notes-page {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.page-header,
.note-detail-head,
.discussion-head,
.discussion-compose__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.notes-layout {
  display: grid;
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
  gap: 18px;
  min-width: 0;
}

.notes-list-panel,
.note-detail-panel,
.note-outline,
.note-discussion {
  min-width: 0;
  border: 1px solid #dbe4f0;
  border-radius: var(--wa-radius-lg, 12px);
  background: #fff;
}

.notes-list-panel {
  display: grid;
  gap: 10px;
  align-content: start;
  padding: 12px;
}

.notes-filter :deep(.el-select) {
  width: 100%;
}

.note-card {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: var(--wa-radius-md, 8px);
  cursor: pointer;
}

.note-card.is-active,
.note-card:hover {
  border-color: #2563eb;
  background: #eff6ff;
}

.note-card__head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.note-card h2,
.note-detail-head h2,
.outline-head h3,
.discussion-head h3 {
  margin: 0;
}

.note-card p,
.note-detail-head p {
  margin: 0;
  color: #64748b;
}

.note-card__meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  color: #64748b;
  font-size: 12px;
}

.note-detail-panel {
  padding: 16px;
}

.note-body-grid {
  display: grid;
  grid-template-columns: minmax(260px, 420px) minmax(0, 1fr);
  gap: 16px;
  margin-top: 16px;
}

.note-outline,
.note-discussion {
  padding: 14px;
}

.outline-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.outline-tree,
.chapter-node {
  display: grid;
  gap: 10px;
}

.chapter-node {
  padding-left: 12px;
  border-left: 2px solid #dbeafe;
}

.chapter-node__title,
.resource-row {
  display: grid;
  gap: 6px;
  padding: 8px;
  border-radius: var(--wa-radius-sm, 6px);
  background: #f8fafc;
}

.resource-row span,
.discussion-row p {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.row-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.row-actions button {
  border: 0;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
  padding: 0;
}

.discussion-list {
  display: grid;
  gap: 10px;
  max-height: 440px;
  overflow: auto;
  margin: 12px 0;
}

.discussion-row {
  padding: 10px;
  border-radius: var(--wa-radius-md, 8px);
  background: #f8fafc;
}

.discussion-row.is-assistant {
  background: #ecfeff;
}

.discussion-row__meta {
  display: flex;
  gap: 10px;
  color: #64748b;
  font-size: 12px;
}

.discussion-compose {
  display: grid;
  gap: 10px;
}

@media (max-width: 960px) {
  .notes-layout,
  .note-body-grid {
    grid-template-columns: 1fr;
  }
}
</style>
