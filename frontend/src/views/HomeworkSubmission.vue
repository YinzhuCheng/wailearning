<template>
  <div class="submission-page" v-loading="loading">
    <div class="page-header">
      <div>
        <h1 class="page-title">提交作业</h1>
        <p class="page-subtitle">
          {{ homework ? `${homework.title} · ${homework.subject_name || selectedCourse?.name || '当前课程'}` : '查看作业要求并提交附件或说明。' }}
        </p>
      </div>
      <el-button @click="router.push('/homework')">返回作业列表</el-button>
    </div>

    <el-empty v-if="!homework && !loading" description="未找到作业信息" />

    <template v-else-if="homework">
      <el-card shadow="never" class="info-card">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="作业标题" :span="2">{{ homework.title }}</el-descriptions-item>
          <el-descriptions-item label="课程">{{ homework.subject_name || selectedCourse?.name || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="截止时间">{{ formatDate(homework.due_date) }}</el-descriptions-item>
          <el-descriptions-item label="发布时间">{{ formatDate(homework.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="发布人">{{ homework.creator_name || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="作业内容" :span="2">
            {{ homework.content || '暂无作业说明。' }}
          </el-descriptions-item>
          <el-descriptions-item label="作业附件" :span="2">
            <el-button v-if="homework.attachment_url" type="primary" link @click="openAttachment(homework.attachment_url)">
              {{ homework.attachment_name || '下载附件' }}
            </el-button>
            <span v-else class="muted-text">暂无附件</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>我的提交</span>
            <el-tag v-if="hasExistingSubmission" type="success">已保存</el-tag>
            <el-tag v-else type="info">未提交</el-tag>
          </div>
        </template>

        <el-form label-position="top" @submit.prevent>
          <el-form-item label="提交说明">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="6"
              placeholder="可填写作业说明、答题思路或补充信息。"
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
                v-if="!attachmentFile && form.attachment_url"
                type="primary"
                link
                @click="openAttachment(form.attachment_url)"
              >
                {{ attachmentDisplayName }}
              </el-button>
              <span v-else>{{ attachmentDisplayName }}</span>
              <el-button link type="danger" @click="removeAttachment">移除</el-button>
            </div>
          </el-form-item>

          <div class="form-actions">
            <el-button @click="router.push('/homework')">取消</el-button>
            <el-button type="primary" :loading="submitting" @click="submitForm">保存提交</el-button>
          </div>
        </el-form>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { attachmentHintText, validateAttachmentFile } from '@/utils/attachments'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const homework = ref(null)
const attachmentFile = ref(null)
const hasExistingSubmission = ref(false)

const selectedCourse = computed(() => userStore.selectedCourse)
const attachmentDisplayName = computed(() => attachmentFile.value?.name || form.attachment_name || '')

const form = reactive({
  content: '',
  attachment_name: '',
  attachment_url: '',
  remove_attachment: false
})

const applySubmission = submission => {
  hasExistingSubmission.value = Boolean(submission)
  form.content = submission?.content || ''
  form.attachment_name = submission?.attachment_name || ''
  form.attachment_url = submission?.attachment_url || ''
  form.remove_attachment = false
  attachmentFile.value = null
}

const loadPage = async () => {
  loading.value = true
  try {
    const [homeworkDetail, submission] = await Promise.all([
      api.homework.get(route.params.id),
      api.homework.getMySubmission(route.params.id)
    ])
    homework.value = homeworkDetail
    applySubmission(submission)
  } finally {
    loading.value = false
  }
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
  if (form.attachment_url) {
    form.remove_attachment = true
  }
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
  attachmentFile.value = null
  form.attachment_name = uploaded.attachment_name
  form.attachment_url = uploaded.attachment_url
  form.remove_attachment = false

  return {
    attachment_name: uploaded.attachment_name,
    attachment_url: uploaded.attachment_url
  }
}

const submitForm = async () => {
  submitting.value = true
  try {
    const attachment = await uploadAttachmentIfNeeded()
    await api.homework.submit(route.params.id, {
      content: form.content?.trim() || null,
      attachment_name: attachment.attachment_name,
      attachment_url: attachment.attachment_url,
      remove_attachment: form.remove_attachment
    })
    ElMessage.success('作业已提交')
    await loadPage()
  } finally {
    submitting.value = false
  }
}

const openAttachment = url => {
  if (!url) {
    return
  }
  window.open(url, '_blank', 'noopener')
}

const formatDate = value => {
  if (!value) {
    return '未设置'
  }
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(() => {
  loadPage()
})

watch(
  () => route.params.id,
  () => {
    loadPage()
  }
)
</script>

<style scoped>
.submission-page {
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

.info-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }

  .form-actions {
    width: 100%;
  }

  .form-actions :deep(.el-button) {
    flex: 1;
  }
}
</style>
