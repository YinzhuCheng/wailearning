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
          <el-descriptions-item label="满分">{{ formatScore(homework.max_score) }}</el-descriptions-item>
          <el-descriptions-item label="自动评分">{{ homework.auto_grading_enabled ? '已启用' : '未启用' }}</el-descriptions-item>
          <el-descriptions-item label="评分规则" :span="2">{{ homework.grading_rule_hint }}</el-descriptions-item>
          <el-descriptions-item label="作业内容" :span="2">
            {{ homework.content || '暂无作业说明。' }}
          </el-descriptions-item>
          <el-descriptions-item label="作业附件" :span="2">
            <el-button v-if="homework.attachment_url" type="primary" link @click="openAttachment(homework.attachment_url, homework.attachment_name)">
              {{ homework.attachment_name || '下载附件' }}
            </el-button>
            <span v-else class="muted-text">暂无附件</span>
          </el-descriptions-item>
          <el-descriptions-item label="最高分评语" :span="2">
            <div v-if="summaryReviewText" class="best-review">
              <el-tag
                v-if="historySummary?.review_score !== null && historySummary?.review_score !== undefined"
                :type="scoreTag(historySummary.review_score)"
                size="small"
              >
                {{ formatScore(historySummary.review_score) }}
              </el-tag>
              <span>{{ summaryReviewText }}</span>
            </div>
            <span v-else class="muted-text">暂无评分</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" class="info-card">
        <template #header>
          <div class="card-header">
            <span>我的提交</span>
            <div class="card-header-tags">
              <el-tag v-if="hasExistingSubmission" type="success">已提交 {{ attempts.length }} 次</el-tag>
              <el-tag v-else type="info">未提交</el-tag>
              <el-tag v-if="latestTaskStatus" :type="taskTagType(latestTaskStatus)">{{ formatTaskStatus(latestTaskStatus) }}</el-tag>
            </div>
          </div>
        </template>

        <div class="submission-alerts">
          <el-alert
            v-if="latestTaskStatus === 'failed' && historySummary?.latest_task_error"
            type="error"
            :closable="false"
            :title="`自动评分失败：${historySummary.latest_task_error}`"
          />
          <el-alert
            v-else-if="latestTaskStatus && latestTaskStatus !== 'success'"
            type="info"
            :closable="false"
            :title="`自动评分任务状态：${formatTaskStatus(latestTaskStatus)}`"
          />
          <el-alert
            v-if="isPastDue && homework.allow_late_submission"
            type="warning"
            :closable="false"
            title="当前提交将被标记为迟交。默认是否影响评分由作业规则决定。"
          />
          <el-alert
            v-if="isSubmissionLocked"
            type="error"
            :closable="false"
            title="已超过截止时间且该作业不允许补交。"
          />
        </div>

        <el-form label-position="top" @submit.prevent>
          <el-form-item label="提交说明">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="6"
              :disabled="isSubmissionLocked"
              placeholder="可填写作业说明、答题思路或补充信息。"
            />
          </el-form-item>

          <el-form-item label="附件">
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              :limit="1"
              :disabled="isSubmissionLocked"
              :on-change="handleAttachmentChange"
            >
              <el-button :disabled="isSubmissionLocked">选择附件</el-button>
            </el-upload>
            <div class="attachment-help">{{ attachmentHintText }}</div>
            <div v-if="attachmentDisplayName" class="attachment-preview">
              <el-button
                v-if="!attachmentFile && form.attachment_url"
                type="primary"
                link
                @click="openAttachment(form.attachment_url, attachmentDisplayName)"
              >
                {{ attachmentDisplayName }}
              </el-button>
              <span v-else>{{ attachmentDisplayName }}</span>
              <el-button link type="danger" :disabled="isSubmissionLocked" @click="removeAttachment">移除</el-button>
            </div>
          </el-form-item>

          <div class="form-actions">
            <el-button @click="router.push('/homework')">取消</el-button>
            <el-button type="primary" :loading="submitting" :disabled="isSubmissionLocked" @click="submitForm">保存提交</el-button>
          </div>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>提交历史</span>
            <span class="muted-text">点击可下载历史附件，主界面始终显示最高分对应评语。</span>
          </div>
        </template>

        <el-empty v-if="!attempts.length" description="暂无提交历史" />

        <el-timeline v-else>
          <el-timeline-item
            v-for="attempt in attempts"
            :key="attempt.id"
            :timestamp="formatDate(attempt.submitted_at)"
            placement="top"
          >
            <div class="attempt-card">
              <div class="attempt-tags">
                <el-tag size="small" type="primary">第 {{ getAttemptLabel(attempt) }} 次提交</el-tag>
                <el-tag v-if="attempt.is_late" size="small" type="warning">迟交</el-tag>
                <el-tag
                  v-if="attempt.review_score !== null && attempt.review_score !== undefined"
                  :type="scoreTag(attempt.review_score)"
                  size="small"
                >
                  {{ formatScore(attempt.review_score) }}
                </el-tag>
                <el-tag v-if="attempt.task_status" :type="taskTagType(attempt.task_status)" size="small">
                  {{ formatTaskStatus(attempt.task_status) }}
                </el-tag>
              </div>
              <div class="attempt-body">
                <div>{{ attempt.content || '无提交说明' }}</div>
                <div v-if="attempt.attachment_url" class="attempt-link">
                  <el-button type="primary" link @click="openAttachment(attempt.attachment_url, attempt.attachment_name)">
                    {{ attempt.attachment_name || '下载附件' }}
                  </el-button>
                </div>
                <div v-if="attempt.review_comment" class="attempt-comment">{{ attempt.review_comment }}</div>
                <div v-if="attempt.task_error" class="attempt-error">{{ attempt.task_error }}</div>
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { attachmentHintText, downloadAttachment, validateAttachmentFile } from '@/utils/attachments'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const homework = ref(null)
const attachmentFile = ref(null)
const hasExistingSubmission = ref(false)
const historySummary = ref(null)
const attempts = ref([])
const currentTime = ref(Date.now())
let clockTimer = null

const selectedCourse = computed(() => userStore.selectedCourse)
const attachmentDisplayName = computed(() => attachmentFile.value?.name || form.attachment_name || '')
const latestTaskStatus = computed(() => historySummary.value?.latest_task_status || '')
const summaryReviewText = computed(() => historySummary.value?.review_comment || '')
const isPastDue = computed(() => {
  if (!homework.value?.due_date) {
    return false
  }
  const dueTime = new Date(homework.value.due_date).getTime()
  return Number.isFinite(dueTime) && currentTime.value > dueTime
})
const isSubmissionLocked = computed(() => {
  return isPastDue.value && !homework.value?.allow_late_submission
})

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

const applyHistory = history => {
  historySummary.value = history?.summary || null
  attempts.value = history?.attempts || []
}

const loadPage = async () => {
  loading.value = true
  try {
    const [homeworkDetail, submission, history] = await Promise.all([
      api.homework.get(route.params.id),
      api.homework.getMySubmission(route.params.id),
      api.homework.getMySubmissionHistory(route.params.id)
    ])
    homework.value = homeworkDetail
    applySubmission(submission)
    applyHistory(history)
  } finally {
    loading.value = false
  }
}

const handleAttachmentChange = uploadFile => {
  if (isSubmissionLocked.value) {
    return false
  }

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
  if (isSubmissionLocked.value) {
    return
  }

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
  if (isSubmissionLocked.value) {
    ElMessage.warning('已超过截止时间且当前作业不允许补交。')
    return
  }

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

const openAttachment = async (url, attachmentName) => {
  if (!url) {
    return
  }
  await downloadAttachment(url, attachmentName)
}

const formatScore = value => {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return '--'
  }
  return Number.isInteger(numericValue) ? `${numericValue}` : numericValue.toFixed(1)
}

const scoreTag = score => {
  const numericScore = Number(score)
  if (numericScore >= 90) return 'success'
  if (numericScore >= 60) return 'warning'
  return 'danger'
}

const formatTaskStatus = status => ({
  queued: '排队中',
  processing: '处理中',
  success: '评分成功',
  failed: '评分失败'
}[status] || status || '未知')

const taskTagType = status => ({
  queued: 'info',
  processing: 'warning',
  success: 'success',
  failed: 'danger'
}[status] || 'info')

const getAttemptLabel = attempt => {
  const index = attempts.value.findIndex(item => item.id === attempt.id)
  return index >= 0 ? attempts.value.length - index : '-'
}

const formatDate = value => {
  if (!value) {
    return '未设置'
  }
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(() => {
  currentTime.value = Date.now()
  clockTimer = window.setInterval(() => {
    currentTime.value = Date.now()
  }, 30000)
  loadPage()
})

onBeforeUnmount(() => {
  if (clockTimer) {
    window.clearInterval(clockTimer)
    clockTimer = null
  }
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

.submission-alerts {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 18px;
}

.deadline-warning {
  margin-top: 8px;
  color: #dc2626;
  font-size: 13px;
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

.card-header-tags,
.attempt-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.best-review {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.attempt-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  background: #fff;
}

.attempt-body {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #475569;
  white-space: pre-wrap;
}

.attempt-link {
  margin-top: 2px;
}

.attempt-comment {
  color: #0f172a;
}

.attempt-error {
  color: #dc2626;
  font-size: 13px;
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
