<template>
  <div class="materials-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">课程资料</h1>
        <p class="page-subtitle">
          {{ selectedCourse ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分配班级'}` : '请先选择课程后查看资料。' }}
        </p>
      </div>
      <div class="header-actions">
        <el-button v-if="!userStore.isStudent && selectedCourse" type="primary" @click="openCreateDialog">
          发布资料
        </el-button>
      </div>
    </div>

    <el-empty v-if="!selectedCourse" description="请先选择一门课程。" />

    <template v-else>
      <div class="materials-layout">
        <aside class="chapter-sidebar" :class="{ 'chapter-sidebar--narrow': userStore.isStudent }">
          <div class="chapter-sidebar__head">
            <span class="chapter-sidebar__title">章节</span>
            <template v-if="canManageChapters">
              <el-button text type="primary" size="small" @click="openAddChapterDialog(null)">根章节</el-button>
            </template>
          </div>
          <el-skeleton v-if="treeLoading" :rows="6" animated />
          <el-tree
            v-else
            ref="treeRef"
            class="chapter-tree"
            :data="chapterTreeNodes"
            node-key="id"
            :props="{ label: 'title', children: 'children' }"
            highlight-current
            :expand-on-click-node="false"
            :draggable="canManageChapters"
            :allow-drop="allowChapterDrop"
            default-expand-all
            @node-click="handleChapterClick"
            @node-drop="handleChapterDrop"
          >
            <template #default="{ data }">
              <span class="tree-node-label">
                {{ data.title }}
                <el-tag v-if="data.is_uncategorized" size="small" type="info" class="tree-tag">默认</el-tag>
              </span>
              <span v-if="canManageChapters && !data.is_uncategorized" class="tree-node-actions" @click.stop>
                <el-button link type="primary" size="small" @click="openRenameChapterDialog(data)">重命名</el-button>
                <el-button link type="primary" size="small" @click="openAddChapterDialog(data.id)">子章节</el-button>
                <el-button link type="danger" size="small" @click="confirmDeleteChapter(data)">删除</el-button>
              </span>
            </template>
          </el-tree>
        </aside>

        <section class="materials-main">
          <div class="materials-toolbar">
            <span class="muted-text">
              当前章节：<strong>{{ currentChapterTitle }}</strong>
            </span>
          </div>

          <el-card shadow="never">
            <el-table
              :data="materials"
              v-loading="loading"
              row-key="id"
              @row-click="viewMaterial"
            >
              <el-table-column prop="title" label="资料标题" min-width="200" />
              <el-table-column v-if="showPlacementColumn" label="所在章节" min-width="180">
                <template #default="{ row }">
                  {{ placementSummary(row) }}
                </template>
              </el-table-column>
              <el-table-column label="附件" width="120">
                <template #default="{ row }">
                  <el-button v-if="row.attachment_url" type="primary" link @click.stop="openAttachment(row)">
                    下载
                  </el-button>
                  <span v-else class="muted-text">无</span>
                </template>
              </el-table-column>
              <el-table-column prop="creator_name" label="发布人" width="100" />
              <el-table-column prop="created_at" label="发布时间" width="170">
                <template #default="{ row }">
                  {{ formatDate(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column v-if="canManageChapters" label="排序" width="100">
                <template #default="{ row, $index }">
                  <el-button
                    link
                    type="primary"
                    size="small"
                    :disabled="$index === 0"
                    @click.stop="moveMaterial(row, -1)"
                  >
                    上移
                  </el-button>
                  <el-button
                    link
                    type="primary"
                    size="small"
                    :disabled="$index >= materials.length - 1"
                    @click.stop="moveMaterial(row, 1)"
                  >
                    下移
                  </el-button>
                </template>
              </el-table-column>
              <el-table-column v-if="!userStore.isStudent" label="操作" width="220">
                <template #default="{ row }">
                  <el-button
                    v-if="canEditMaterial(row)"
                    type="primary"
                    link
                    size="small"
                    @click.stop="openEditDialog(row)"
                  >
                    编辑
                  </el-button>
                  <el-button
                    v-if="canManageChapters"
                    type="primary"
                    link
                    size="small"
                    @click.stop="openPlacementDialog(row)"
                  >
                    引用
                  </el-button>
                  <el-button
                    v-if="canDeleteMaterial(row)"
                    type="danger"
                    link
                    size="small"
                    @click.stop="deleteMaterial(row)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </section>
      </div>
    </template>

    <!-- 发布 / 编辑 -->
    <el-dialog v-model="dialogVisible" :title="editingMaterial ? '编辑资料' : '发布资料'" width="900px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="资料标题" prop="title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="所属章节" prop="chapter_ids">
          <el-select
            v-model="form.chapter_ids"
            multiple
            filterable
            placeholder="可选择多个章节（引用）"
            style="width: 100%"
          >
            <el-option v-for="opt in flatChapterOptions" :key="opt.id" :label="opt.label" :value="opt.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="资料说明" prop="content">
          <MarkdownEditorPanel
            v-model="form.content"
            :min-rows="6"
            :max-rows="24"
            placeholder="支持 Markdown、LaTeX（$...$ / $$...$$）、本地上传或 URL 插图"
            hint="工具栏可插入格式；图片会插入为 Markdown，学生与教师预览一致。"
          />
        </el-form-item>
        <el-form-item label="附件">
          <el-upload :auto-upload="false" :show-file-list="false" :limit="1" :on-change="handleAttachmentChange">
            <el-button>选择附件</el-button>
          </el-upload>
          <div class="attachment-help">{{ attachmentHintText }}</div>
          <div v-if="attachmentDisplayName" class="attachment-preview">
            <el-button v-if="form.attachment_url" type="primary" link @click="downloadFormAttachment">
              {{ attachmentDisplayName }}
            </el-button>
            <span v-else>{{ attachmentDisplayName }}</span>
            <el-button link type="danger" @click="removeAttachment">移除</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情 -->
    <el-dialog v-model="detailVisible" title="资料详情" width="900px" destroy-on-close>
      <el-descriptions v-if="currentMaterial" :column="2" border>
        <el-descriptions-item label="资料标题" :span="2">{{ currentMaterial.title }}</el-descriptions-item>
        <el-descriptions-item label="章节" :span="2">
          {{ placementSummary(currentMaterial) }}
        </el-descriptions-item>
        <el-descriptions-item label="课程">{{ currentMaterial.subject_name || selectedCourse?.name }}</el-descriptions-item>
        <el-descriptions-item label="发布人">{{ currentMaterial.creator_name }}</el-descriptions-item>
        <el-descriptions-item label="发布时间">{{ formatDate(currentMaterial.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="资料说明" :span="2">
          <RichMarkdownDisplay :markdown="currentMaterial.content" variant="student" empty-text="暂无说明" />
        </el-descriptions-item>
        <el-descriptions-item label="附件" :span="2">
          <el-button v-if="currentMaterial.attachment_url" type="primary" link @click="openAttachment(currentMaterial)">
            {{ currentMaterial.attachment_name || '下载附件' }}
          </el-button>
          <span v-else class="muted-text">无附件</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 重命名章节 -->
    <el-dialog v-model="renameChapterVisible" title="重命名章节" width="420px" destroy-on-close>
      <el-input v-model="renameChapterTitle" maxlength="120" show-word-limit />
      <template #footer>
        <el-button @click="renameChapterVisible = false">取消</el-button>
        <el-button type="primary" :loading="renameChapterSubmitting" @click="submitRenameChapter">保存</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="chapterDialogVisible" :title="chapterParentId ? '新增子章节' : '新增根章节'" width="420px" destroy-on-close>
      <el-input v-model="newChapterTitle" placeholder="章节名称" maxlength="120" show-word-limit />
      <template #footer>
        <el-button @click="chapterDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="chapterSubmitting" @click="submitNewChapter">确定</el-button>
      </template>
    </el-dialog>

    <!-- 附加引用 -->
    <el-dialog v-model="placementDialogVisible" title="附加到其他章节" width="480px" destroy-on-close>
      <p class="muted-text">同一资料可出现在多个章节；此处为新增引用，不影响原有章节中的条目。</p>
      <el-select v-model="extraChapterId" placeholder="选择章节" filterable style="width: 100%">
        <el-option
          v-for="opt in placementExtraOptions"
          :key="opt.id"
          :label="opt.label"
          :value="opt.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="placementDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="placementSubmitting" @click="submitExtraPlacement">添加引用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import MarkdownEditorPanel from '@/components/MarkdownEditorPanel.vue'
import RichMarkdownDisplay from '@/components/RichMarkdownDisplay.vue'
import { useUserStore } from '@/stores/user'
import { attachmentHintText, downloadAttachment, validateAttachmentFile } from '@/utils/attachments'

const userStore = useUserStore()

const loading = ref(false)
const treeLoading = ref(false)
const submitting = ref(false)
const chapterSubmitting = ref(false)
const renameChapterSubmitting = ref(false)
const placementSubmitting = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const chapterDialogVisible = ref(false)
const renameChapterVisible = ref(false)
const placementDialogVisible = ref(false)
const currentMaterial = ref(null)
const editingMaterial = ref(null)
const materials = ref([])
const formRef = ref(null)
const attachmentFile = ref(null)
const chapterTreeNodes = ref([])
const selectedChapterId = ref(null)
const treeRef = ref(null)
const newChapterTitle = ref('')
const chapterParentId = ref(null)
const renameChapterId = ref(null)
const renameChapterTitle = ref('')
const placementTarget = ref(null)
const extraChapterId = ref(null)

const selectedCourse = computed(() => userStore.selectedCourse)
const attachmentDisplayName = computed(() => attachmentFile.value?.name || form.attachment_name || '')

const isCourseInstructor = computed(() => {
  const c = selectedCourse.value
  const uid = userStore.userInfo?.id
  if (!c || uid == null) return false
  return Number(c.teacher_id) === Number(uid)
})

const canManageChapters = computed(
  () => !userStore.isStudent && selectedCourse.value && (userStore.isAdmin || isCourseInstructor.value)
)

const showPlacementColumn = computed(() => !userStore.isStudent)

const form = reactive({
  title: '',
  content: '',
  attachment_name: '',
  attachment_url: '',
  remove_attachment: false,
  chapter_ids: []
})

const rules = {
  title: [{ required: true, message: '请输入资料标题', trigger: 'blur' }],
  chapter_ids: [{ required: true, message: '请选择至少一个章节', trigger: 'change' }]
}

const flattenTree = (nodes, depth = 0, acc = []) => {
  for (const n of nodes || []) {
    acc.push({ ...n, depth })
    if (n.children?.length) flattenTree(n.children, depth + 1, acc)
  }
  return acc
}

const flatChapterOptions = computed(() => {
  const flat = flattenTree(chapterTreeNodes.value)
  return flat.map(n => ({
    id: n.id,
    label: `${'　'.repeat(n.depth)}${n.title}`
  }))
})

const currentChapterTitle = computed(() => {
  const flat = flattenTree(chapterTreeNodes.value)
  const row = flat.find(x => x.id === selectedChapterId.value)
  return row?.title || '—'
})

const findUncategorizedId = nodes => {
  for (const n of nodes || []) {
    if (n.is_uncategorized) return n.id
    const inner = findUncategorizedId(n.children)
    if (inner) return inner
  }
  return null
}

const handleChapterClick = data => {
  selectedChapterId.value = data.id
}

const allowChapterDrop = (draggingNode, dropNode, type) => {
  if (draggingNode.data.is_uncategorized) return false
  if (type === 'inner' && dropNode.data.is_uncategorized) return false
  return true
}

const loadChapterTree = async () => {
  if (!selectedCourse.value) {
    chapterTreeNodes.value = []
    return
  }
  treeLoading.value = true
  try {
    const res = await api.materialChapters.tree({ subject_id: selectedCourse.value.id })
    chapterTreeNodes.value = res?.nodes || []
    if (!selectedChapterId.value) {
      selectedChapterId.value =
        findUncategorizedId(chapterTreeNodes.value) || chapterTreeNodes.value[0]?.id || null
    }
  } finally {
    treeLoading.value = false
  }
}

const loadMaterials = async () => {
  if (!selectedCourse.value) {
    materials.value = []
    return
  }

  loading.value = true
  try {
    const result = await api.materials.list({
      class_id: selectedCourse.value.class_id,
      subject_id: selectedCourse.value.id,
      chapter_id: selectedChapterId.value || undefined,
      page: 1,
      page_size: 200
    })
    materials.value = result?.data || []
  } finally {
    loading.value = false
  }
}

const handleChapterDrop = async (draggingNode, dropNode, dropType) => {
  if (!canManageChapters.value || !selectedCourse.value) return

  let parentNode = null
  if (dropType === 'inner') {
    parentNode = dropNode
  } else {
    parentNode = draggingNode.parent
  }

  const siblings = parentNode?.childNodes || []
  const orderedIds = siblings.map(cn => cn.data).filter(d => d && !d.is_uncategorized).map(d => d.id)
  const parentId =
    parentNode?.level === 0 || parentNode?.data == null ? null : parentNode?.data?.id ?? null

  if (!orderedIds.length) return

  try {
    await api.materialChapters.reorderChapters(selectedCourse.value.id, {
      parent_id: parentId,
      ordered_chapter_ids: orderedIds
    })
    ElMessage.success('章节顺序已更新')
    await loadChapterTree()
  } catch (e) {
    console.error(e)
    await loadChapterTree()
  }
}

const moveMaterial = async (row, delta) => {
  if (!canManageChapters.value || !selectedChapterId.value) return
  const idx = materials.value.findIndex(m => m.id === row.id)
  const nidx = idx + delta
  if (idx < 0 || nidx < 0 || nidx >= materials.value.length) return

  const list = [...materials.value]
  const [removed] = list.splice(idx, 1)
  list.splice(nidx, 0, removed)

  const orderedSectionIds = list
    .map(m => m.placements?.find(p => p.chapter_id === selectedChapterId.value)?.section_id)
    .filter(Boolean)
  if (orderedSectionIds.length !== list.length) {
    ElMessage.error('无法排序：缺少章节映射')
    return
  }

  try {
    await api.materialChapters.reorderSections(selectedCourse.value.id, {
      chapter_id: selectedChapterId.value,
      ordered_section_ids: orderedSectionIds
    })
    ElMessage.success('顺序已更新')
    await loadMaterials()
  } catch (e) {
    console.error(e)
    await loadMaterials()
  }
}

const placementSummary = row => {
  const ps = row?.placements || []
  if (!ps.length) return '—'
  return ps.map(p => p.chapter_title).join('、')
}

const resetForm = () => {
  form.title = ''
  form.content = ''
  form.attachment_name = ''
  form.attachment_url = ''
  form.remove_attachment = false
  form.chapter_ids = []
  attachmentFile.value = null
}

const openCreateDialog = () => {
  editingMaterial.value = null
  resetForm()
  const sid = selectedChapterId.value || findUncategorizedId(chapterTreeNodes.value)
  form.chapter_ids = sid ? [sid] : []
  dialogVisible.value = true
}

const openEditDialog = async row => {
  editingMaterial.value = row
  const full = await api.materials.get(row.id)
  resetForm()
  form.title = full.title
  form.content = full.content || ''
  form.attachment_name = full.attachment_name || ''
  form.attachment_url = full.attachment_url || ''
  form.chapter_ids =
    (full.chapter_ids && full.chapter_ids.length
      ? full.chapter_ids
      : full.placements?.map(p => p.chapter_id)) || []
  dialogVisible.value = true
}

const handleAttachmentChange = uploadFile => {
  const file = uploadFile.raw
  const result = validateAttachmentFile(file)
  if (!result.valid) {
    ElMessage.error(result.message)
    return false
  }
  attachmentFile.value = file
  form.attachment_name = file.name
  form.attachment_url = ''
  form.remove_attachment = false
  return false
}

const removeAttachment = () => {
  attachmentFile.value = null
  form.attachment_name = ''
  form.attachment_url = ''
  form.remove_attachment = true
}

const uploadAttachmentIfNeeded = async () => {
  if (!attachmentFile.value) {
    return {
      attachment_name: form.attachment_name || null,
      attachment_url: form.attachment_url || null,
      remove_attachment: form.remove_attachment
    }
  }
  const uploaded = await api.files.upload(attachmentFile.value)
  form.attachment_name = uploaded.attachment_name
  form.attachment_url = uploaded.attachment_url
  form.remove_attachment = false
  attachmentFile.value = null
  return {
    attachment_name: uploaded.attachment_name,
    attachment_url: uploaded.attachment_url,
    remove_attachment: false
  }
}

const submitForm = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    const attachment = await uploadAttachmentIfNeeded()
    const base = {
      title: form.title,
      content: form.content,
      chapter_ids: form.chapter_ids
    }
    if (editingMaterial.value) {
      await api.materials.update(editingMaterial.value.id, {
        ...base,
        attachment_name: attachment.attachment_name,
        attachment_url: attachment.attachment_url,
        remove_attachment: attachment.remove_attachment
      })
      ElMessage.success('资料已更新')
    } else {
      await api.materials.create({
        ...base,
        attachment_name: attachment.attachment_name,
        attachment_url: attachment.attachment_url,
        class_id: selectedCourse.value.class_id,
        subject_id: selectedCourse.value.id
      })
      ElMessage.success('资料已发布')
    }
    dialogVisible.value = false
    await loadChapterTree()
    await loadMaterials()
  } finally {
    submitting.value = false
  }
}

const viewMaterial = async row => {
  currentMaterial.value = await api.materials.get(row.id)
  detailVisible.value = true
}

const openAttachment = async row => {
  if (!row?.attachment_url) return
  await downloadAttachment(row.attachment_url, row.attachment_name)
}

const downloadFormAttachment = async () => {
  await downloadAttachment(form.attachment_url, attachmentDisplayName.value)
}

const canDeleteMaterial = row => userStore.isAdmin || row.created_by === userStore.userInfo?.id

const canEditMaterial = row => userStore.isAdmin || row.created_by === userStore.userInfo?.id

const deleteMaterial = async row => {
  try {
    await ElMessageBox.confirm(`确认删除资料“${row.title}”吗？`, '删除资料', { type: 'warning' })
    await api.materials.delete(row.id)
    ElMessage.success('资料已删除')
    await loadChapterTree()
    await loadMaterials()
  } catch (error) {
    if (error !== 'cancel') console.error('删除资料失败', error)
  }
}

const formatDate = value => {
  if (!value) return '未设置'
  return new Date(value).toLocaleString('zh-CN')
}

const openAddChapterDialog = parentId => {
  chapterParentId.value = parentId
  newChapterTitle.value = ''
  chapterDialogVisible.value = true
}

const openRenameChapterDialog = data => {
  renameChapterId.value = data.id
  renameChapterTitle.value = data.title
  renameChapterVisible.value = true
}

const submitRenameChapter = async () => {
  const t = renameChapterTitle.value.trim()
  if (!t) {
    ElMessage.warning('请输入章节名称')
    return
  }
  renameChapterSubmitting.value = true
  try {
    await api.materialChapters.update(renameChapterId.value, { title: t })
    ElMessage.success('已更新')
    renameChapterVisible.value = false
    await loadChapterTree()
  } finally {
    renameChapterSubmitting.value = false
  }
}

const submitNewChapter = async () => {
  const t = newChapterTitle.value.trim()
  if (!t) {
    ElMessage.warning('请输入章节名称')
    return
  }
  chapterSubmitting.value = true
  try {
    await api.materialChapters.create(selectedCourse.value.id, {
      title: t,
      parent_id: chapterParentId.value
    })
    ElMessage.success('章节已添加')
    chapterDialogVisible.value = false
    await loadChapterTree()
  } finally {
    chapterSubmitting.value = false
  }
}

const confirmDeleteChapter = async data => {
  try {
    await ElMessageBox.confirm(`删除章节「${data.title}」？资料将移至「未分类」。`, '删除章节', { type: 'warning' })
    const deletedId = data.id
    await api.materialChapters.delete(deletedId, selectedCourse.value.id)
    ElMessage.success('已删除')
    await loadChapterTree()
    if (selectedChapterId.value === deletedId) {
      selectedChapterId.value = findUncategorizedId(chapterTreeNodes.value)
    }
    await loadMaterials()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

const placementExtraOptions = computed(() => {
  const row = placementTarget.value
  const existing = new Set((row?.placements || []).map(p => p.chapter_id))
  return flatChapterOptions.value.filter(o => !existing.has(o.id))
})

const openPlacementDialog = row => {
  placementTarget.value = row
  extraChapterId.value = null
  placementDialogVisible.value = true
}

const submitExtraPlacement = async () => {
  if (!extraChapterId.value || !placementTarget.value) return
  placementSubmitting.value = true
  try {
    await api.materialChapters.addPlacement(placementTarget.value.id, selectedCourse.value.id, {
      chapter_id: extraChapterId.value
    })
    ElMessage.success('已添加引用')
    placementDialogVisible.value = false
    await loadMaterials()
  } finally {
    placementSubmitting.value = false
  }
}

onMounted(async () => {
  await loadChapterTree()
  await loadMaterials()
})

watch(selectedCourse, async () => {
  selectedChapterId.value = null
  await loadChapterTree()
  selectedChapterId.value = findUncategorizedId(chapterTreeNodes.value)
  await loadMaterials()
})

watch(selectedChapterId, () => {
  loadMaterials()
})
</script>

<style scoped>
.materials-page {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;
}

.page-title {
  margin: 0 0 8px;
  font-size: 28px;
  color: #0f172a;
}

.page-subtitle {
  margin: 0;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.materials-layout {
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.chapter-sidebar {
  border-radius: 12px;
  background: #fff;
  padding: 12px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.chapter-sidebar--narrow {
  grid-template-columns: 1fr;
}

.chapter-sidebar__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.chapter-sidebar__title {
  font-weight: 600;
  color: #0f172a;
}

.chapter-tree :deep(.el-tree-node__content) {
  height: auto;
  min-height: 32px;
  align-items: flex-start;
}

.tree-node-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding-right: 8px;
}

.tree-tag {
  transform: scale(0.9);
}

.tree-node-actions {
  margin-left: auto;
  display: inline-flex;
  flex-shrink: 0;
  gap: 2px;
}

.materials-toolbar {
  margin-bottom: 12px;
}

.materials-main :deep(.el-table__row) {
  cursor: pointer;
}

.muted-text {
  color: #64748b;
  font-size: 13px;
}

.attachment-help {
  margin-top: 8px;
}

.attachment-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  flex-wrap: wrap;
}

@media (max-width: 960px) {
  .materials-layout {
    grid-template-columns: 1fr;
  }
}
</style>
