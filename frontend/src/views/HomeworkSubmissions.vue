<template>
  <div class="submissions-page" v-loading="loading">
    <div class="page-header">
      <div>
        <h1 class="page-title">学生提交</h1>
        <p class="page-subtitle">
          {{ homework ? `${homework.title} · ${homework.subject_name || selectedCourse?.name || '当前课程'}` : '查看当前作业的提交情况。' }}
        </p>
      </div>
      <div class="header-actions">
        <el-button @click="router.push('/homework')">返回作业管理</el-button>
        <el-button
          type="primary"
          :disabled="!downloadableSelection.length"
          :loading="downloading"
          @click="downloadSelected"
        >
          一键下载
        </el-button>
      </div>
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
          <el-descriptions-item label="作业附件" :span="2">
            <el-button v-if="homework.attachment_url" type="primary" link @click="openAttachment(homework.attachment_url, homework.attachment_name)">
              {{ homework.attachment_name || '下载附件' }}
            </el-button>
            <span v-else class="muted-text">暂无附件</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>提交情况</span>
            <el-text type="info">仅勾选已提交且带附件的学生，可用于批量下载。</el-text>
          </div>
        </template>

        <div class="table-wrapper">
          <el-table
            :data="submissions"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="52" :selectable="selectableRow" />
            <el-table-column prop="student_name" label="学生姓名" min-width="140" />
            <el-table-column prop="student_no" label="学号" min-width="140" />
            <el-table-column label="提交状态" width="120">
              <template #default="{ row }">
                <el-tag :type="row.status === 'submitted' ? 'success' : 'warning'">
                  {{ row.status === 'submitted' ? '已提交' : '尚未提交' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="提交时间" min-width="180">
              <template #default="{ row }">
                {{ row.submitted_at ? formatDate(row.submitted_at) : '尚未提交' }}
              </template>
            </el-table-column>
            <el-table-column label="提交说明" min-width="220">
              <template #default="{ row }">
                {{ row.content || '无' }}
              </template>
            </el-table-column>
            <el-table-column label="附件" min-width="180">
              <template #default="{ row }">
                <el-button
                  v-if="row.attachment_url"
                  type="primary"
                  link
                  @click="openAttachment(row.attachment_url, row.attachment_name)"
                >
                  {{ row.attachment_name || '下载附件' }}
                </el-button>
                <span v-else class="muted-text">无附件</span>
              </template>
            </el-table-column>
            <el-table-column label="评分" min-width="320">
              <template #default="{ row }">
                <div v-if="canReviewSubmission(row)" class="review-cell">
                  <el-input
                    v-model="row.review_score_input"
                    placeholder="分数 0-100"
                    class="review-score-input"
                  />
                  <el-input
                    v-model="row.review_comment_input"
                    placeholder="评论"
                    class="review-comment-input"
                  />
                  <el-button
                    type="primary"
                    size="small"
                    :loading="row.saving_review"
                    @click="saveReview(row)"
                  >
                    确定
                  </el-button>
                </div>
                <div v-if="hasSavedReview(row)" class="review-result">
                  <span v-if="row.review_score !== null && row.review_score !== undefined">当前分数：{{ formatScore(row.review_score) }}</span>
                  <span v-if="row.review_comment">评论：{{ row.review_comment }}</span>
                </div>
                <span v-else-if="!canReviewSubmission(row)" class="muted-text">未提交</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { downloadAttachment } from '@/utils/attachments'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const downloading = ref(false)
const homework = ref(null)
const submissions = ref([])
const selectedRows = ref([])

const selectedCourse = computed(() => userStore.selectedCourse)
const downloadableSelection = computed(() =>
  selectedRows.value.filter(row => row.submission_id && row.attachment_url)
)

const buildSubmissionRow = row => ({
  ...row,
  review_score_input:
    row.review_score === null || row.review_score === undefined ? '' : String(row.review_score),
  review_comment_input: row.review_comment || '',
  saving_review: false
})

const loadPage = async () => {
  loading.value = true
  try {
    const [homeworkDetail, submissionResult] = await Promise.all([
      api.homework.get(route.params.id),
      api.homework.getSubmissions(route.params.id)
    ])
    homework.value = homeworkDetail
    submissions.value = (submissionResult?.data || []).map(buildSubmissionRow)
    selectedRows.value = []
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = rows => {
  selectedRows.value = rows
}

const selectableRow = row => Boolean(row.submission_id && row.attachment_url)

const canReviewSubmission = row => row.submission_id !== null && row.submission_id !== undefined

const hasSavedReview = row =>
  row.review_score !== null && row.review_score !== undefined || Boolean(row.review_comment)

const formatScore = value => {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return '--'
  }
  return Number.isInteger(numericValue) ? `${numericValue}` : numericValue.toFixed(1)
}

const getTodayZipName = () => `${new Date().toLocaleDateString('sv-SE')}.zip`

const resolveDownloadFilename = headers => {
  const disposition = headers?.['content-disposition'] || headers?.['Content-Disposition'] || ''
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      return utf8Match[1]
    }
  }

  const plainMatch = disposition.match(/filename="?([^"]+)"?/i)
  if (plainMatch?.[1]) {
    return plainMatch[1]
  }

  return getTodayZipName()
}

const downloadSelected = async () => {
  if (!downloadableSelection.value.length) {
    return
  }

  downloading.value = true
  try {
    const response = await api.homework.downloadSubmissions(route.params.id, {
      submission_ids: downloadableSelection.value.map(row => row.submission_id)
    })
    const url = window.URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = resolveDownloadFilename(response.headers)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('已开始下载')
  } finally {
    downloading.value = false
  }
}

const saveReview = async row => {
  if (!canReviewSubmission(row)) {
    ElMessage.error('未提交的作业不能评分')
    return
  }

  const rawScore = `${row.review_score_input ?? ''}`.trim()
  const score = Number(rawScore)
  if (!rawScore || !Number.isFinite(score) || score < 0 || score > 100) {
    ElMessage.error('请输入 0 到 100 之间的数字分数')
    return
  }

  row.saving_review = true
  try {
    await api.homework.reviewSubmission(route.params.id, row.submission_id, {
      review_score: score,
      review_comment: row.review_comment_input?.trim() || null
    })
    ElMessage.success('评分已保存')
    await loadPage()
  } finally {
    row.saving_review = false
  }
}

const openAttachment = async (url, attachmentName) => {
  if (!url) {
    return
  }
  await downloadAttachment(url, attachmentName)
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
.submissions-page {
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
  flex-wrap: wrap;
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

.muted-text {
  color: #64748b;
}

.table-wrapper {
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
}

.review-cell {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
}

.review-score-input {
  width: 96px;
}

.review-comment-input {
  min-width: 140px;
}

.review-result {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #475569;
  font-size: 13px;
}

:deep(.table-wrapper .el-table) {
  min-width: 860px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions :deep(.el-button) {
    flex: 1;
  }
}
</style>
