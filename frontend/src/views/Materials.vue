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
      <el-card shadow="never">
        <el-table :data="materials" v-loading="loading" @row-click="viewMaterial">
          <el-table-column prop="title" label="资料标题" min-width="220" />
          <el-table-column prop="subject_name" label="课程" width="160" />
          <el-table-column label="附件" width="140">
            <template #default="{ row }">
              <el-button
                v-if="row.attachment_url"
                type="primary"
                link
                @click.stop="openAttachment(row)"
              >
                下载附件
              </el-button>
              <span v-else class="muted-text">无</span>
            </template>
          </el-table-column>
          <el-table-column prop="creator_name" label="发布人" width="120" />
          <el-table-column prop="created_at" label="发布时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column v-if="!userStore.isStudent" label="操作" width="120">
            <template #default="{ row }">
              <el-button
                v-if="canDeleteMaterial(row)"
                type="danger"
                size="small"
                @click.stop="deleteMaterial(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-dialog v-model="dialogVisible" title="发布资料" width="900px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="资料标题" prop="title">
          <el-input v-model="form.title" />
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
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            :limit="1"
            :on-change="handleAttachmentChange"
          >
            <el-button>选择附件</el-button>
          </el-upload>
          <div class="attachment-help">{{ attachmentHintText }}</div>
          <div v-if="attachmentDisplayName" class="attachment-preview">
            <el-button
              v-if="form.attachment_url"
              type="primary"
              link
              @click="downloadFormAttachment"
            >
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

    <el-dialog v-model="detailVisible" title="资料详情" width="900px" destroy-on-close>
      <el-descriptions v-if="currentMaterial" :column="2" border>
        <el-descriptions-item label="资料标题" :span="2">{{ currentMaterial.title }}</el-descriptions-item>
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
const submitting = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentMaterial = ref(null)
const materials = ref([])
const formRef = ref(null)
const attachmentFile = ref(null)

const selectedCourse = computed(() => userStore.selectedCourse)
const attachmentDisplayName = computed(() => attachmentFile.value?.name || form.attachment_name || '')

const form = reactive({
  title: '',
  content: '',
  attachment_name: '',
  attachment_url: ''
})

const rules = {
  title: [{ required: true, message: '请输入资料标题', trigger: 'blur' }]
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
      page: 1,
      page_size: 100
    })
    materials.value = result?.data || []
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.title = ''
  form.content = ''
  form.attachment_name = ''
  form.attachment_url = ''
  attachmentFile.value = null
}

const openCreateDialog = () => {
  resetForm()
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
  return false
}

const removeAttachment = () => {
  attachmentFile.value = null
  form.attachment_name = ''
  form.attachment_url = ''
}

const uploadAttachmentIfNeeded = async () => {
  if (!attachmentFile.value) {
    return {
      attachment_name: form.attachment_name || null,
      attachment_url: form.attachment_url || null
    }
  }

  const uploaded = await api.files.upload(attachmentFile.value)
  form.attachment_name = uploaded.attachment_name
  form.attachment_url = uploaded.attachment_url
  attachmentFile.value = null

  return {
    attachment_name: uploaded.attachment_name,
    attachment_url: uploaded.attachment_url
  }
}

const submitForm = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    const attachment = await uploadAttachmentIfNeeded()
    await api.materials.create({
      title: form.title,
      content: form.content,
      attachment_name: attachment.attachment_name,
      attachment_url: attachment.attachment_url,
      class_id: selectedCourse.value.class_id,
      subject_id: selectedCourse.value.id
    })
    ElMessage.success('资料已发布')
    dialogVisible.value = false
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
  if (!row?.attachment_url) {
    return
  }
  await downloadAttachment(row.attachment_url, row.attachment_name)
}

const downloadFormAttachment = async () => {
  await downloadAttachment(form.attachment_url, attachmentDisplayName.value)
}

const canDeleteMaterial = row => userStore.isAdmin || row.created_by === userStore.userInfo?.id

const deleteMaterial = async row => {
  try {
    await ElMessageBox.confirm(`确认删除资料“${row.title}”吗？`, '删除资料', { type: 'warning' })
    await api.materials.delete(row.id)
    ElMessage.success('资料已删除')
    await loadMaterials()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除资料失败', error)
    }
  }
}

const formatDate = value => {
  if (!value) return '未设置'
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(() => {
  loadMaterials()
})

watch(selectedCourse, () => {
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

.attachment-help,
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

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
