<template>
  <div class="learning-notes-page" :class="`learning-notes-page--${materialPresentationStyle}`">
    <section class="notes-hero">
      <div>
        <p class="notes-hero__eyebrow">课程知识库</p>
        <h1>学习笔记</h1>
        <p>
          私有笔记只对本人可见；公开笔记可以面向同课程成员，未关联课程的公开笔记面向所有登录用户。
        </p>
      </div>
      <el-button type="primary" @click="openCreateDialog">新建笔记</el-button>
    </section>

    <div class="notes-workspace">
      <aside class="notes-library" aria-label="笔记列表">
        <div class="notes-library__toolbar">
          <el-tabs
            v-model="activeScope"
            class="notes-library__scope"
            @tab-change="loadNotes"
          >
            <el-tab-pane label="我的笔记" name="mine" />
            <el-tab-pane label="公开笔记" name="public" />
          </el-tabs>
          <el-select v-model="subjectFilter" clearable filterable placeholder="按课程筛选">
            <el-option v-for="course in courseOptions" :key="course.id" :label="course.name" :value="course.id" />
          </el-select>
        </div>

        <el-skeleton v-if="loadingNotes" :rows="6" animated />
        <el-empty v-else-if="!notes.length" description="暂无学习笔记" />
        <div v-else class="notes-list">
          <button
            v-for="note in notes"
            :key="note.id"
            type="button"
            class="note-card"
            :class="{ 'note-card--active': selectedNote?.id === note.id }"
            @click="selectNote(note)"
          >
            <span class="note-card__visibility">{{ noteVisibilityLabel(note) }}</span>
            <strong>{{ note.title }}</strong>
            <span class="note-card__desc">{{ note.description || '暂无说明' }}</span>
            <span class="note-card__meta">
              {{ note.subject_name || '未关联课程' }} · {{ formatDate(note.updated_at || note.created_at) }}
            </span>
          </button>
        </div>
      </aside>

      <template v-if="selectedNote">
        <aside class="notes-outline" aria-label="笔记大纲">
          <div class="notes-outline__head">
            <div>
              <span>笔记大纲</span>
              <strong>{{ selectedNote.title }}</strong>
            </div>
            <el-dropdown v-if="canEditSelected" trigger="click">
              <el-button text type="primary" size="small">添加</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openChapterDialog(null)">顶层章节</el-dropdown-item>
                  <el-dropdown-item :disabled="!activeChapterId" @click="openChapterDialog(activeChapterId)">
                    子章节
                  </el-dropdown-item>
                  <el-dropdown-item @click="openResourceDialog(activeChapterId)">资料条目</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <el-empty
            v-if="!outlineRows.length"
            description="暂无大纲内容"
            class="notes-outline__empty"
          />
          <div v-else class="notes-outline__list">
            <div
              v-for="row in outlineRows"
              :key="row.key"
              class="outline-row"
              :class="[
                `outline-row--${row.type}`,
                { 'outline-row--active': row.type === 'resource' && selectedResourceId === row.id }
              ]"
              :style="{ paddingLeft: `${12 + row.depth * 18}px` }"
            >
              <button
                v-if="row.type === 'resource'"
                type="button"
                class="outline-row__main"
                @click="selectResource(row.id)"
              >
                <span class="outline-row__index">{{ row.indexLabel }}</span>
                <span class="outline-row__title">{{ row.title }}</span>
              </button>
              <div v-else class="outline-row__chapter">
                <span class="outline-row__title">{{ row.title }}</span>
                <span class="outline-row__count">{{ row.resourceCount }} 条</span>
              </div>

              <el-dropdown v-if="canEditSelected" trigger="click" class="outline-row__menu">
                <button type="button" class="icon-text-button">操作</button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <template v-if="row.type === 'chapter'">
                      <el-dropdown-item @click="openChapterDialog(row.id)">添加子章节</el-dropdown-item>
                      <el-dropdown-item @click="openResourceDialog(row.id)">添加资料</el-dropdown-item>
                      <el-dropdown-item @click="openChapterEditDialog(row.raw)">重命名</el-dropdown-item>
                      <el-dropdown-item divided @click="deleteChapter(row.raw)">删除章节</el-dropdown-item>
                    </template>
                    <template v-else>
                      <el-dropdown-item @click="openResourceEditDialog(row.raw)">编辑资料</el-dropdown-item>
                      <el-dropdown-item divided @click="deleteResource(row.raw)">删除资料</el-dropdown-item>
                    </template>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </aside>

        <main class="note-reader">
          <header class="note-reader__head">
            <div>
              <p class="note-reader__course">
                {{ selectedNote.subject_name || '未关联课程' }} ·
                {{ selectedNote.owner_real_name || selectedNote.owner_username }} ·
                {{ formatDate(selectedNote.created_at) }}
              </p>
              <h2>{{ selectedNote.title }}</h2>
              <p v-if="selectedNote.description" class="note-reader__description">{{ selectedNote.description }}</p>
            </div>
            <div class="note-reader__actions">
              <el-button v-if="canEditSelected" @click="openEditDialog">编辑信息</el-button>
              <el-button
                v-if="canEditSelected"
                :type="selectedNote.visibility === 'course' ? 'warning' : 'success'"
                plain
                @click="toggleVisibility"
              >
                {{ visibilityToggleLabel(selectedNote) }}
              </el-button>
              <el-button v-if="canEditSelected" type="danger" plain @click="deleteSelectedNote">删除</el-button>
            </div>
          </header>

          <article class="note-article">
            <template v-if="selectedResource">
              <div class="note-article__nav">
                <el-button :disabled="!prevResource" @click="goResource(prevResource?.id)">上一篇</el-button>
                <el-button :disabled="!nextResource" @click="goResource(nextResource?.id)">下一篇</el-button>
                <el-button v-if="canEditSelected" type="primary" plain @click="openResourceEditDialog(selectedResource)">
                  编辑正文
                </el-button>
              </div>
              <p v-if="selectedResourcePath" class="note-article__breadcrumb">{{ selectedResourcePath }}</p>
              <h1>{{ selectedResource.title }}</h1>
              <div class="note-article__body">
                <PlainOrMarkdownBlock
                  :text="selectedResourceBody"
                  :format="selectedResource.content_format || 'markdown'"
                  variant="student"
                  empty-text="暂无正文"
                />
              </div>
              <section v-if="selectedResource.attachment_url" class="note-attachment">
                <div>
                  <strong>配套附件</strong>
                  <span>{{ selectedResource.attachment_name || '附件' }}</span>
                </div>
                <el-button type="primary" link @click="downloadNoteAttachment(selectedResource)">
                  下载附件
                </el-button>
              </section>
            </template>
            <el-empty
              v-else
              description="选择或添加一个资料条目后开始阅读"
              class="note-article__empty"
            >
              <el-button v-if="canEditSelected" type="primary" @click="openResourceDialog(activeChapterId)">
                添加资料条目
              </el-button>
            </el-empty>
          </article>

          <section class="note-discussion" aria-label="笔记讨论区">
            <div class="note-discussion__head">
              <div>
                <span>笔记讨论</span>
                <strong>{{ discussionScopeLabel(selectedNote) }}</strong>
              </div>
              <el-button text type="primary" @click="discussionComposerOpen = !discussionComposerOpen">
                {{ discussionComposerOpen ? '收起输入' : '发表讨论' }}
              </el-button>
            </div>

            <div v-if="discussionComposerOpen" class="note-discussion__composer">
              <div class="discussion-compose-tabs">
                <el-radio-group v-model="discussionDraftFormat" size="small">
                  <el-radio-button label="markdown">Markdown</el-radio-button>
                  <el-radio-button label="plain">纯文本</el-radio-button>
                </el-radio-group>
                <el-radio-group v-model="discussionComposeMode" size="small">
                  <el-radio-button label="edit">编辑</el-radio-button>
                  <el-radio-button label="preview" :disabled="discussionDraftFormat !== 'markdown'">预览</el-radio-button>
                </el-radio-group>
              </div>
              <PlainOrMarkdownBlock
                v-if="discussionComposeMode === 'preview' && discussionDraftFormat === 'markdown'"
                :text="discussionDraft"
                format="markdown"
                variant="student"
                empty-text="（空）"
                class="discussion-preview"
              />
              <el-input
                v-else
                v-model="discussionDraft"
                type="textarea"
                :autosize="{ minRows: 4, maxRows: 10 }"
                maxlength="8000"
                show-word-limit
                placeholder="写下问题、补充或整理想法。使用标准 Markdown/LaTeX 语法可渲染公式。"
              />
              <div class="note-discussion__composer-actions">
                <el-checkbox v-model="invokeLlm">请求智能助教回复</el-checkbox>
                <el-button type="primary" :loading="discussionSubmitting" @click="submitDiscussion">发表</el-button>
              </div>
            </div>

            <el-skeleton v-if="discussionLoading" :rows="4" animated />
            <div v-else class="note-discussion__list">
              <el-empty v-if="!discussionRows.length" description="暂无讨论" />
              <article
                v-for="row in discussionRows"
                :key="row.id"
                class="discussion-row"
                :class="{ 'discussion-row--assistant': row.message_kind === 'llm_assistant' }"
              >
                <div class="discussion-row__meta">
                  <strong>{{ row.message_kind === 'llm_assistant' ? '智能助教' : row.author_real_name || row.author_username }}</strong>
                  <span>{{ formatDate(row.created_at) }}</span>
                </div>
                <PlainOrMarkdownBlock
                  :text="row.body"
                  :format="row.body_format || 'markdown'"
                  variant="student"
                  empty-text="（空）"
                />
              </article>
            </div>
          </section>
        </main>
      </template>

      <section v-else class="note-reader note-reader--empty">
        <el-empty description="选择一条笔记查看正文、大纲和讨论" />
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
            <el-checkbox v-model="noteForm.copy_materials" :disabled="!noteForm.copy_chapters">
              连同章节下资料引用一起复制
            </el-checkbox>
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

    <el-dialog v-model="resourceDialogVisible" :title="editingResource ? '编辑资料' : '添加资料'" width="860px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="资料名称">
          <el-input v-model="resourceForm.title" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="正文">
          <MarkdownEditorPanel
            v-model="resourceForm.content"
            v-model:content-format="resourceForm.content_format"
            :show-format-toggle="true"
            :compact-demo="true"
            :min-rows="7"
            :max-rows="18"
            placeholder="支持 Markdown、LaTeX（$...$ / $$...$$ / \\(...\\) / \\[...\\]）、图片和代码块"
            hint="保存后正文会在笔记阅读区按同样规则渲染。"
          />
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import MarkdownEditorPanel from '@/components/MarkdownEditorPanel.vue'
import PlainOrMarkdownBlock from '@/components/PlainOrMarkdownBlock.vue'
import { downloadAttachment } from '@/utils/attachments'
import {
  getMaterialPresentationStyle,
  MATERIAL_PRESENTATION_EVENT
} from '@/utils/materialPresentation'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const activeScope = ref('mine')
const subjectFilter = ref(null)
const notes = ref([])
const selectedNote = ref(null)
const selectedResourceId = ref(null)
const loadingNotes = ref(false)
const discussionRows = ref([])
const discussionLoading = ref(false)
const discussionDraft = ref('')
const discussionDraftFormat = ref('markdown')
const discussionComposeMode = ref('edit')
const discussionComposerOpen = ref(false)
const invokeLlm = ref(false)
const discussionSubmitting = ref(false)
const materialPresentationStyle = ref(getMaterialPresentationStyle())

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

const outlineRows = computed(() => buildOutlineRows(selectedNote.value))
const resourceRows = computed(() => outlineRows.value.filter(row => row.type === 'resource'))
const selectedResource = computed(() => resourceRows.value.find(row => row.id === selectedResourceId.value)?.raw || null)
const selectedResourceRow = computed(() => resourceRows.value.find(row => row.id === selectedResourceId.value) || null)
const selectedResourcePath = computed(() => selectedResourceRow.value?.path || '')
const selectedResourceBody = computed(() => stripDuplicateMarkdownTitle(selectedResource.value))
const activeChapterId = computed(() => selectedResourceRow.value?.chapterId || firstChapterId(selectedNote.value))

const currentResourceIndex = computed(() => resourceRows.value.findIndex(row => row.id === selectedResourceId.value))
const prevResource = computed(() => (currentResourceIndex.value > 0 ? resourceRows.value[currentResourceIndex.value - 1] : null))
const nextResource = computed(() =>
  currentResourceIndex.value >= 0 && currentResourceIndex.value < resourceRows.value.length - 1
    ? resourceRows.value[currentResourceIndex.value + 1]
    : null
)

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

function stripDuplicateMarkdownTitle(resource) {
  if (!resource?.content || resource.content_format === 'plain') return resource?.content || ''
  const title = (resource.title || '').trim()
  if (!title) return resource.content
  const lines = String(resource.content).split(/\r?\n/)
  let index = 0
  while (index < lines.length && !lines[index].trim()) index += 1
  const first = lines[index]?.trim() || ''
  if (first === `# ${title}`) {
    return [...lines.slice(0, index), ...lines.slice(index + 1)].join('\n').replace(/^\s+/, '')
  }
  return resource.content
}

function buildOutlineRows(note) {
  if (!note) return []
  const rows = []
  let resourceIndex = 0

  const walk = (chapters, depth = 0, path = []) => {
    for (const chapter of chapters || []) {
      const chapterPath = [...path, chapter.title]
      rows.push({
        key: `chapter-${chapter.id}`,
        type: 'chapter',
        id: chapter.id,
        raw: chapter,
        title: chapter.title,
        depth,
        path: chapterPath.join(' / '),
        resourceCount: countResources(chapter)
      })
      for (const resource of chapter.resources || []) {
        resourceIndex += 1
        rows.push({
          key: `resource-${resource.id}`,
          type: 'resource',
          id: resource.id,
          raw: resource,
          title: resource.title,
          depth: depth + 1,
          chapterId: chapter.id,
          path: chapterPath.join(' / '),
          indexLabel: String(resourceIndex).padStart(2, '0')
        })
      }
      walk(chapter.children || [], depth + 1, chapterPath)
    }
  }

  walk(note.chapters || [])

  for (const resource of note.loose_resources || []) {
    resourceIndex += 1
    rows.push({
      key: `resource-${resource.id}`,
      type: 'resource',
      id: resource.id,
      raw: resource,
      title: resource.title,
      depth: 0,
      chapterId: null,
      path: '未归入章节',
      indexLabel: String(resourceIndex).padStart(2, '0')
    })
  }

  return rows
}

function countResources(chapter) {
  let count = (chapter.resources || []).length
  for (const child of chapter.children || []) {
    count += countResources(child)
  }
  return count
}

function firstChapterId(note) {
  const first = (note?.chapters || [])[0]
  return first?.id || null
}

function ensureResourceSelection(preferredId = selectedResourceId.value) {
  const rows = resourceRows.value
  if (!rows.length) {
    selectedResourceId.value = null
    return
  }
  if (preferredId && rows.some(row => row.id === preferredId)) {
    selectedResourceId.value = preferredId
    return
  }
  selectedResourceId.value = rows[0].id
}

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
      selectedResourceId.value = null
      discussionRows.value = []
    }
  } finally {
    loadingNotes.value = false
  }
}

const selectNote = async note => {
  selectedNote.value = await api.learningNotes.get(note.id)
  ensureResourceSelection()
  discussionComposerOpen.value = false
  await loadDiscussion()
}

const reloadSelectedNote = async (preferredResourceId = selectedResourceId.value) => {
  if (!selectedNote.value) return
  selectedNote.value = await api.learningNotes.get(selectedNote.value.id)
  ensureResourceSelection(preferredResourceId)
  await loadNotes()
}

const selectResource = id => {
  selectedResourceId.value = id
}

const goResource = id => {
  if (!id) return
  selectResource(id)
}

const loadDiscussion = async () => {
  if (!selectedNote.value) return
  discussionLoading.value = true
  try {
    const result = await api.learningNotes.discussion(selectedNote.value.id, { page: 1, page_size: 20 })
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
    ensureResourceSelection()
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
  selectedResourceId.value = null
  discussionRows.value = []
  await loadNotes()
}

const openChapterDialog = parentId => {
  editingChapter.value = null
  chapterParentId.value = parentId || null
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
    ensureResourceSelection()
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
  ensureResourceSelection()
}

const openResourceDialog = chapterId => {
  editingResource.value = null
  resourceChapterId.value = chapterId || null
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
  if (!selectedNote.value || !resourceForm.value.title.trim()) {
    ElMessage.warning('请填写资料名称')
    return
  }
  const payload = {
    ...resourceForm.value,
    chapter_id: resourceChapterId.value
  }
  if (editingResource.value) {
    selectedNote.value = await api.learningNotes.updateResource(selectedNote.value.id, editingResource.value.id, payload)
    ensureResourceSelection(editingResource.value.id)
  } else {
    const beforeIds = new Set(resourceRows.value.map(row => row.id))
    selectedNote.value = await api.learningNotes.createResource(selectedNote.value.id, payload)
    const nextRows = buildOutlineRows(selectedNote.value).filter(row => row.type === 'resource')
    const created = nextRows.find(row => !beforeIds.has(row.id))
    ensureResourceSelection(created?.id)
  }
  resourceDialogVisible.value = false
}

const deleteResource = async resource => {
  await ElMessageBox.confirm('确认删除这条笔记资料？', '删除资料', { type: 'warning' })
  selectedNote.value = await api.learningNotes.deleteResource(selectedNote.value.id, resource.id)
  ensureResourceSelection()
}

const submitDiscussion = async () => {
  if (!selectedNote.value || !discussionDraft.value.trim()) return
  discussionSubmitting.value = true
  try {
    await api.learningNotes.createDiscussion(selectedNote.value.id, {
      body: discussionDraft.value,
      body_format: discussionDraftFormat.value,
      invoke_llm: invokeLlm.value || discussionDraft.value.trim().startsWith('@LLM')
    })
    discussionDraft.value = ''
    discussionDraftFormat.value = 'markdown'
    discussionComposeMode.value = 'edit'
    invokeLlm.value = false
    discussionComposerOpen.value = false
    await loadDiscussion()
    ElMessage.success('已发表')
  } finally {
    discussionSubmitting.value = false
  }
}

const downloadNoteAttachment = resource => {
  if (!resource?.attachment_url) return
  downloadAttachment(resource.attachment_url, resource.attachment_name)
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', { hour12: false })
}

watch(subjectFilter, loadNotes)

watch(discussionDraftFormat, value => {
  if (value !== 'markdown') {
    discussionComposeMode.value = 'edit'
  }
})

const handleMaterialPresentationStyleChange = event => {
  materialPresentationStyle.value = event?.detail || getMaterialPresentationStyle()
}

onMounted(async () => {
  if (typeof window !== 'undefined') {
    window.addEventListener(MATERIAL_PRESENTATION_EVENT, handleMaterialPresentationStyleChange)
  }
  await userStore.fetchTeachingCourses(true)
  await loadNotes()
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener(MATERIAL_PRESENTATION_EVENT, handleMaterialPresentationStyleChange)
  }
})
</script>

<style scoped>
.learning-notes-page {
  display: grid;
  gap: 18px;
  min-width: 0;
  color: #172033;
}

.notes-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 20px 24px;
  border: 1px solid #dbe4f0;
  border-radius: 18px;
  background: linear-gradient(135deg, #ffffff 0%, #f7fbff 100%);
}

.notes-hero__eyebrow,
.note-reader__course,
.notes-outline__head span,
.note-discussion__head span {
  margin: 0;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}

.notes-hero h1 {
  margin: 4px 0 8px;
  font-size: 24px;
  line-height: 1.25;
}

.notes-hero p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.notes-workspace {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(220px, 280px) minmax(470px, 1fr);
  gap: 18px;
  align-items: start;
  min-width: 0;
}

.notes-library,
.notes-outline,
.note-reader {
  min-width: 0;
  border: 1px solid #dbe4f0;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.04);
}

.notes-library,
.notes-outline {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 118px);
  overflow: auto;
}

.notes-library {
  padding: 14px;
}

.notes-library__toolbar {
  display: grid;
  gap: 10px;
  margin-bottom: 12px;
}

.notes-library__toolbar :deep(.el-select),
.notes-library__scope {
  width: 100%;
}

.notes-library__scope :deep(.el-tabs__header) {
  margin: 0;
}

.notes-list {
  display: grid;
  gap: 10px;
}

.note-card {
  display: grid;
  gap: 7px;
  width: 100%;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.16s ease, background 0.16s ease, transform 0.16s ease;
}

.note-card:hover,
.note-card--active {
  border-color: #2563eb;
  background: #f1f6ff;
}

.note-card:hover {
  transform: translateY(-1px);
}

.note-card strong {
  font-size: 15px;
  line-height: 1.35;
}

.note-card__visibility {
  justify-self: start;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
}

.note-card__desc,
.note-card__meta {
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

.notes-outline {
  padding: 14px;
}

.notes-outline__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.notes-outline__head strong {
  display: block;
  margin-top: 4px;
  line-height: 1.35;
}

.notes-outline__empty {
  padding: 28px 0;
}

.notes-outline__list {
  display: grid;
  gap: 4px;
}

.outline-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding-top: 4px;
  padding-right: 8px;
  padding-bottom: 4px;
  border-radius: 10px;
}

.outline-row--chapter {
  color: #475569;
}

.outline-row--resource:hover,
.outline-row--active {
  background: #eff6ff;
}

.outline-row__main,
.outline-row__chapter {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
}

.outline-row__main {
  cursor: pointer;
}

.outline-row__index {
  flex: 0 0 auto;
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
}

.outline-row__title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  line-height: 1.5;
}

.outline-row--chapter .outline-row__title {
  font-weight: 800;
}

.outline-row__count {
  flex: 0 0 auto;
  color: #94a3b8;
  font-size: 11px;
}

.outline-row__menu {
  opacity: 0;
  transition: opacity 0.16s ease;
}

.outline-row:hover .outline-row__menu {
  opacity: 1;
}

.icon-text-button {
  border: 0;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
  font-size: 12px;
}

.note-reader {
  display: grid;
  gap: 16px;
  padding: 18px;
}

.note-reader--empty {
  min-height: 440px;
  place-items: center;
}

.note-reader__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.note-reader__head h2 {
  margin: 6px 0;
  font-size: 24px;
  line-height: 1.25;
}

.note-reader__description {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.note-reader__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.note-article {
  display: grid;
  gap: 14px;
  min-height: 360px;
}

.note-article__nav {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.note-article__breadcrumb {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.note-article h1 {
  margin: 0;
  color: #0f172a;
  font-size: 28px;
  line-height: 1.25;
}

.note-article__body {
  width: min(100%, 860px);
  color: #243044;
  font-size: 16px;
  line-height: 1.8;
}

.note-article__body :deep(.rich-md) {
  font-size: 16px;
  line-height: 1.85;
}

.note-article__body :deep(.rich-md h1),
.note-article__body :deep(.rich-md h2),
.note-article__body :deep(.rich-md h3) {
  margin-top: 1.1em;
}

.note-article__body :deep(.katex-display) {
  padding: 8px 0;
}

.note-article__empty {
  align-self: center;
}

.note-attachment {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  width: min(100%, 860px);
  padding: 14px 16px;
  border: 1px solid #bfdbfe;
  border-radius: 14px;
  background: #eff6ff;
}

.note-attachment div {
  display: grid;
  gap: 4px;
}

.note-attachment span {
  color: #64748b;
  font-size: 13px;
}

.note-discussion {
  display: grid;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.note-discussion__head,
.note-discussion__composer-actions,
.discussion-row__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.note-discussion__head strong {
  display: block;
  margin-top: 4px;
  color: #475569;
  font-size: 13px;
}

.note-discussion__composer {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid #dbe4f0;
  border-radius: 14px;
  background: #f8fafc;
}

.discussion-compose-tabs {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.discussion-preview {
  min-height: 120px;
  padding: 12px;
  border: 1px solid #dbe4f0;
  border-radius: 10px;
  background: #fff;
}

.note-discussion__list {
  display: grid;
  gap: 10px;
}

.discussion-row {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
}

.discussion-row--assistant {
  border-color: #a5f3fc;
  background: #ecfeff;
}

.discussion-row__meta {
  justify-content: flex-start;
  color: #64748b;
  font-size: 12px;
}

.learning-notes-page--reader .note-article h1,
.learning-notes-page--reader .note-reader__head h2,
.learning-notes-page--reader .notes-outline__head strong {
  font-family: "Noto Serif SC", "Source Han Serif SC", "Songti SC", serif;
}

.learning-notes-page--compact .notes-workspace {
  gap: 14px;
}

.learning-notes-page--compact .note-article__body,
.learning-notes-page--compact .note-article__body :deep(.rich-md) {
  font-size: 15px;
}

@media (max-width: 1180px) {
  .notes-workspace {
    grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
  }

  .notes-outline {
    position: static;
    grid-column: 1 / -1;
    max-height: none;
  }
}

@media (max-width: 1380px) and (min-width: 1181px) {
  .note-reader__head {
    flex-direction: column;
  }

  .note-reader__actions {
    justify-content: flex-start;
  }
}

@media (max-width: 860px) {
  .notes-hero,
  .note-reader__head {
    flex-direction: column;
  }

  .notes-workspace {
    grid-template-columns: 1fr;
  }

  .notes-library,
  .notes-outline {
    position: static;
    max-height: none;
  }

  .note-article h1 {
    font-size: 23px;
  }
}
</style>
