<template>
  <div class="homework-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">作业管理</h1>
        <p class="page-subtitle">
          {{ selectedCourse ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分配班级'}` : '请先选择课程后查看作业。' }}
        </p>
      </div>
      <div class="header-actions">
        <el-button v-if="!userStore.isStudent && selectedCourse" type="primary" @click="openCreateDialog">
          发布作业
        </el-button>
      </div>
    </div>

    <el-empty v-if="!selectedCourse" description="请先选择一门课程。" />

    <template v-else>
      <el-card shadow="never">
        <el-table :data="homeworks" v-loading="loading">
          <el-table-column prop="title" label="作业标题" min-width="200" />
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
          <el-table-column prop="due_date" label="截止时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.due_date) }}
            </template>
          </el-table-column>
          <el-table-column prop="creator_name" label="发布人" width="120" />
          <el-table-column prop="created_at" label="发布时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="viewHomework(row)">查看</el-button>
              <el-button
                v-if="userStore.isStudent"
                size="small"
                @click="goToSubmitPage(row)"
              >
                提交
              </el-button>
              <el-button
                v-else
                size="small"
                @click="goToSubmissionStatus(row)"
              >
                学生提交
              </el-button>
              <el-button
                v-if="!userStore.isStudent"
                size="small"
                type="danger"
                @click="deleteHomework(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-dialog v-model="dialogVisible" title="发布作业" width="620px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="作业标题" prop="title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="截止时间" prop="due_date">
          <el-date-picker
            v-model="form.due_date"
            type="datetime"
            placeholder="请选择截止时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="作业内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="6" />
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
            <span>{{ attachmentDisplayName }}</span>
            <el-button link type="danger" @click="removeAttachment">移除</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="作业详情" width="620px" destroy-on-close>
      <el-descriptions v-if="currentHomework" :column="2" border>
        <el-descriptions-item label="作业标题" :span="2">{{ currentHomework.title }}</el-descriptions-item>
        <el-descriptions-item label="课程">{{ currentHomework.subject_name || selectedCourse?.name }}</el-descriptions-item>
        <el-descriptions-item label="截止时间">{{ formatDate(currentHomework.due_date) }}</el-descriptions-item>
        <el-descriptions-item label="发布人">{{ currentHomework.creator_name }}</el-descriptions-item>
        <el-descriptions-item label="发布时间">{{ formatDate(currentHomework.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="作业内容" :span="2">{{ currentHomework.content || '暂无内容' }}</el-descriptions-item>
        <el-descriptions-item label="附件" :span="2">
          <el-button v-if="currentHomework.attachment_url" type="primary" link @click="openAttachment(currentHomework)">
            {{ currentHomework.attachment_name || '下载附件' }}
          </el-button>
          <span v-else class="muted-text">无附件</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { attachmentHintText, validateAttachmentFile } from '@/utils/attachments'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentHomework = ref(null)
const homeworks = ref([])
const formRef = ref(null)
const attachmentFile = ref(null)

const selectedCourse = computed(() => userStore.selectedCourse)
const attachmentDisplayName = computed(() => attachmentFile.value?.name || form.attachment_name || '')

const form = reactive({
  title: '',
  content: '',
  due_date: null,
  attachment_name: '',
  attachment_url: ''
})

const rules = {
  title: [{ required: true, message: '请输入作业标题', trigger: 'blur' }]
}

const buildParams = () => {
  if (!selectedCourse.value) {
    return {}
  }
  return {
    class_id: selectedCourse.value.class_id,
    subject_id: selectedCourse.value.id,
    page: 1,
    page_size: 100
  }
}

const loadHomeworks = async () => {
  if (!selectedCourse.value) {
    homeworks.value = []
    return
  }
  loading.value = true
  try {
    const result = await api.homework.list(buildParams())
    homeworks.value = result?.data || []
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  form.title = ''
  form.content = ''
  form.due_date = null
  form.attachment_name = ''
  form.attachment_url = ''
  attachmentFile.value = null
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
    await api.homework.create({
      title: form.title,
      content: form.content,
      attachment_name: attachment.attachment_name,
      attachment_url: attachment.attachment_url,
      due_date: form.due_date,
      class_id: selectedCourse.value.class_id,
      subject_id: selectedCourse.value.id
    })
    ElMessage.success('作业已发布')
    dialogVisible.value = false
    await loadHomeworks()
  } finally {
    submitting.value = false
  }
}

const viewHomework = async row => {
  currentHomework.value = await api.homework.get(row.id)
  detailVisible.value = true
}

const goToSubmitPage = row => {
  router.push(`/homework/${row.id}/submit`)
}

const goToSubmissionStatus = row => {
  router.push(`/homework/${row.id}/submissions`)
}

const openAttachment = row => {
  if (!row?.attachment_url) {
    return
  }
  window.open(row.attachment_url, '_blank', 'noopener')
}

const deleteHomework = async row => {
  try {
    await ElMessageBox.confirm(`确认删除作业“${row.title}”吗？`, '删除作业', { type: 'warning' })
    await api.homework.delete(row.id)
    ElMessage.success('作业已删除')
    await loadHomeworks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除作业失败', error)
    }
  }
}

const formatDate = value => {
  if (!value) return '未设置'
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(() => {
  loadHomeworks()
})

watch(selectedCourse, () => {
  loadHomeworks()
})
</script>

<style scoped>
.homework-page {
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
