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
        <el-button
          v-if="homework?.auto_grading_enabled"
          type="warning"
          data-testid="homework-submissions-batch-regrade"
          :disabled="!regradableSelection.length"
          :loading="batchRegrading"
          @click="batchRegradeSelected"
        >
          批量 LLM 重评
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
          <el-descriptions-item label="满分">{{ formatScore(homework.max_score) }}</el-descriptions-item>
          <el-descriptions-item label="自动评分">{{ homework.auto_grading_enabled ? '已启用' : '未启用' }}</el-descriptions-item>
          <el-descriptions-item label="评分规则" :span="2">{{ homework.grading_rule_hint }}</el-descriptions-item>
          <el-descriptions-item label="作业内容" :span="2">
            <RichMarkdownDisplay :markdown="homework.content" variant="teacher" empty-text="暂无作业说明。" />
          </el-descriptions-item>
          <el-descriptions-item label="评分要点" :span="2">
            <RichMarkdownDisplay :markdown="homework.rubric_text" variant="teacher" empty-text="未设置" />
          </el-descriptions-item>
          <el-descriptions-item label="参考答案" :span="2">
            <RichMarkdownDisplay :markdown="homework.reference_answer" variant="teacher" empty-text="未设置" />
          </el-descriptions-item>
          <el-descriptions-item label="作业附件" :span="2">
            <el-button v-if="homework.attachment_url" type="primary" link @click="openAttachment(homework.attachment_url, homework.attachment_name)">
              {{ homework.attachment_name || '下载附件' }}
            </el-button>
            <span v-else class="muted-text">暂无附件</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <CourseDiscussionPanel
        target-type="homework"
        :target-id="homework.id"
        :subject-id="homework.subject_id"
        :class-id="homework.class_id"
        :discussion-requires-context="homework.discussion_requires_context"
      />

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>提交情况</span>
            <el-text type="info">
              列表分页展示概要；点击「详情」查看完整说明与评语并评分。勾选行可用于批量下载或批量 LLM 重评。
            </el-text>
          </div>
        </template>

        <div class="table-toolbar">
          <el-pagination
            v-model:current-page="submissionPage"
            :page-size="submissionPageSize"
            :total="submissionTotal"
            layout="total, prev, pager, next"
            small
            @current-change="loadPage"
          />
        </div>

        <div class="table-wrapper">
          <el-table
            :data="submissions"
            :row-class-name="submissionRowClassName"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="52" :selectable="selectableForAnyBatchAction" />
            <el-table-column prop="student_name" label="学生姓名" min-width="140" />
            <el-table-column prop="student_no" label="学号" min-width="140" />
            <el-table-column label="提交状态" width="120">
              <template #default="{ row }">
                <el-tag :type="row.status === 'submitted' ? 'success' : 'warning'">
                  {{ row.status === 'submitted' ? '已提交' : '尚未提交' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="任务状态" min-width="220">
              <template #default="{ row }">
                <div class="task-cell">
                  <el-tooltip
                    v-if="row.latest_task_status === 'failed' && row.latest_task_error"
                    :content="taskFailureTooltip(row)"
                    placement="top"
                  >
                    <el-tag :type="taskTagType(row.latest_task_status)" size="small">
                      {{ formatTaskStatus(row.latest_task_status) }}
                    </el-tag>
                  </el-tooltip>
                  <el-tag
                    v-else-if="row.latest_task_status"
                    :type="taskTagType(row.latest_task_status)"
                    size="small"
                  >
                    {{ formatTaskStatus(row.latest_task_status) }}
                  </el-tag>
                  <span v-else class="muted-text">{{ row.status === 'submitted' ? '待评分' : '未提交' }}</span>
                  <span v-if="row.latest_attempt_is_late" class="late-tip">已标记迟交</span>
                  <el-button
                    v-if="row.latest_task_log?.length"
                    type="primary"
                    link
                    size="small"
                    :data-testid="`homework-submission-log-${row.student_no || row.student_id}`"
                    @click="openTaskLog(row)"
                  >
                    LLM 日志
                  </el-button>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="提交时间" min-width="180">
              <template #default="{ row }">
                {{ row.submitted_at ? formatDate(row.submitted_at) : '尚未提交' }}
              </template>
            </el-table-column>
            <el-table-column label="提交次数" width="100">
              <template #default="{ row }">
                {{ row.attempt_count || 0 }}
              </template>
            </el-table-column>
            <el-table-column label="大模型申报" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.used_llm_assist" type="warning" size="small" effect="plain">是</el-tag>
                <el-tag v-else-if="row.status === 'submitted'" type="info" size="small" effect="plain">否</el-tag>
                <span v-else class="muted-text">—</span>
              </template>
            </el-table-column>
            <el-table-column label="提交说明（缩略）" min-width="200">
              <template #default="{ row }">
                <span>{{ row.content_preview || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="评语（缩略）" min-width="160">
              <template #default="{ row }">
                <span>{{ row.comment_preview || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="申诉" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.appeal_status === 'pending'" type="warning" size="small">待处理</el-tag>
                <el-tag v-else-if="row.appeal_status === 'acknowledged'" type="info" size="small">已阅</el-tag>
                <el-tag v-else-if="row.appeal_status === 'resolved'" type="success" size="small">已处理</el-tag>
                <span v-else class="muted-text">—</span>
              </template>
            </el-table-column>
            <el-table-column label="分数" width="100">
              <template #default="{ row }">
                <template v-if="row.review_score !== null && row.review_score !== undefined">
                  <el-tag :type="scoreTag(row.review_score)" size="small">{{ formatScore(row.review_score) }}</el-tag>
                </template>
                <span v-else class="muted-text">—</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" link :data-testid="`homework-submission-detail-${row.student_no || row.student_id}`" @click="openDetail(row)">详情</el-button>
                <el-button
                  size="small"
                  :disabled="!row.submission_id"
                  :data-testid="`homework-submission-history-${row.student_no || row.student_id}`"
                  @click="openHistory(row)"
                >
                  历史
                </el-button>
                <el-button
                  v-if="homework.auto_grading_enabled"
                  size="small"
                  :data-testid="`homework-submission-regrade-${row.student_no || row.student_id}`"
                  type="primary"
                  :disabled="!row.submission_id"
                  :loading="row.regrading"
                  @click="regrade(row)"
                >
                  重评
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="table-toolbar table-toolbar--bottom">
          <el-pagination
            v-model:current-page="submissionPage"
            :page-size="submissionPageSize"
            :total="submissionTotal"
            layout="total, prev, pager, next"
            small
            @current-change="loadPage"
          />
        </div>
      </el-card>
    </template>

    <el-dialog v-model="detailVisible" title="提交详情与评分" width="720px" destroy-on-close @closed="detailRow = null">
      <template v-if="detailRow">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="学生">{{ detailRow.student_name }}（{{ detailRow.student_no || '无学号' }}）</el-descriptions-item>
          <el-descriptions-item label="申诉状态">
            <el-tag v-if="detailRow.appeal_status === 'pending'" type="warning" size="small">待处理</el-tag>
            <el-tag v-else-if="detailRow.appeal_status === 'acknowledged'" type="info" size="small">已阅</el-tag>
            <el-tag v-else-if="detailRow.appeal_status === 'resolved'" type="success" size="small">已处理</el-tag>
            <span v-else class="muted-text">—</span>
            <el-button
              v-if="detailRow.appeal_status === 'pending'"
              size="small"
              type="primary"
              link
              style="margin-left: 8px"
              :loading="detailAckLoading"
              @click="acknowledgeAppealForDetail"
            >
              标记已阅
            </el-button>
          </el-descriptions-item>
          <el-descriptions-item label="提交说明">
            <div class="detail-text">{{ detailRow.content || '无' }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="附件">
            <el-button
              v-if="detailRow.attachment_url"
              type="primary"
              link
              @click="openAttachment(detailRow.attachment_url, detailRow.attachment_name)"
            >
              {{ detailRow.attachment_name || '下载附件' }}
            </el-button>
            <span v-else class="muted-text">无附件</span>
          </el-descriptions-item>
          <el-descriptions-item label="任务状态">
            <span v-if="detailRow.latest_task_status">{{ formatTaskStatus(detailRow.latest_task_status) }}</span>
            <span v-else class="muted-text">—</span>
          </el-descriptions-item>
          <el-descriptions-item label="LLM 日志">
            <el-button
              v-if="detailRow.latest_task_log?.length"
              type="primary"
              link
              size="small"
              data-testid="btn-open-llm-log"
              @click="openTaskLog(detailRow)"
            >
              查看日志
            </el-button>
            <span v-else class="muted-text">无</span>
          </el-descriptions-item>
          <el-descriptions-item label="当前展示分">
            {{
              detailRow.review_score !== null && detailRow.review_score !== undefined
                ? formatScore(detailRow.review_score)
                : '—'
            }}
          </el-descriptions-item>
          <el-descriptions-item label="评语">
            <div v-if="detailRow.review_comment" class="feedback-inline">
              <FeedbackRichText :text="detailRow.review_comment" variant="teacher" />
            </div>
            <span v-else class="muted-text">暂无</span>
          </el-descriptions-item>
        </el-descriptions>
        <div class="detail-review-block">
          <div class="muted-text" style="margin-bottom: 8px">调整分数（作用于所选提交轮次，默认最新一轮）</div>
          <el-input
            v-model="detailRow.review_score_input"
            :placeholder="`分数 0-${formatScore(homework?.max_score)}`"
            class="review-score-input"
          />
          <el-input
            v-model="detailRow.review_comment_input"
            type="textarea"
            :rows="4"
            placeholder="评语（支持 Markdown）"
            class="review-comment-input"
          />
          <el-button type="primary" :loading="detailRow.saving_review" @click="saveReviewFromDetail">保存评分</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="historyVisible" title="提交与评分历史" width="860px" destroy-on-close>
      <div v-if="historyVisible && currentHistoryRow" class="history-header">
        <div>
          <strong>{{ currentHistoryRow.student_name }}</strong>
          <span class="muted-text"> · {{ currentHistoryRow.student_no || '未设置学号' }}</span>
        </div>
        <div class="history-meta">
          <span>主视图显示最高分及其评语</span>
        </div>
      </div>

      <el-empty v-if="historyVisible && !historyAttempts.length" description="暂无历史记录" />

      <el-timeline v-else>
        <el-timeline-item
          v-for="attempt in historyAttempts"
          :key="attempt.id"
          :timestamp="formatDate(attempt.submitted_at)"
          placement="top"
        >
          <div class="attempt-card">
            <div class="attempt-tags">
              <el-tag size="small" type="primary">提交 #{{ attempt.id }}</el-tag>
              <el-tag v-if="attempt.is_late" size="small" type="warning">迟交</el-tag>
              <el-tag v-if="attempt.used_llm_assist" size="small" type="warning" effect="plain">申报大模型</el-tag>
              <el-tag
                v-if="attempt.review_score !== null && attempt.review_score !== undefined"
                :type="scoreTag(attempt.review_score)"
                size="small"
              >
                {{ formatScore(attempt.review_score) }}
              </el-tag>
              <el-tooltip
                v-if="attempt.task_status === 'failed' && attempt.task_error"
                :content="attemptFailureTooltip(attempt)"
                placement="top"
              >
                <el-tag :type="taskTagType(attempt.task_status)" size="small">
                  {{ formatTaskStatus(attempt.task_status) }}
                </el-tag>
              </el-tooltip>
              <el-tag v-else-if="attempt.task_status" :type="taskTagType(attempt.task_status)" size="small">
                {{ formatTaskStatus(attempt.task_status) }}
              </el-tag>
              <el-button
                v-if="attempt.task_log?.length"
                type="primary"
                link
                size="small"
                data-testid="btn-open-llm-log-history"
                @click="openTaskLog(currentHistoryRow, attempt)"
              >
                LLM 日志
              </el-button>
              <el-tag v-if="attempt.score_source === 'teacher'" size="small" type="success">教师评分</el-tag>
              <el-tag v-else-if="attempt.score_source === 'auto'" size="small" type="info">自动评分</el-tag>
            </div>

            <div class="attempt-body">
              <div>{{ attempt.content || '无提交说明' }}</div>
              <div v-if="attempt.attachment_url" class="attempt-link">
                <el-button type="primary" link @click="openAttachment(attempt.attachment_url, attempt.attachment_name)">
                  {{ attempt.attachment_name || '下载附件' }}
                </el-button>
              </div>
              <div v-if="attempt.review_comment" class="attempt-feedback">
                <div class="muted-text" style="font-size: 12px; margin-bottom: 4px">评语</div>
                <FeedbackRichText :text="attempt.review_comment" variant="teacher" />
              </div>
              <div v-if="attempt.task_error" class="attempt-error">{{ attempt.task_error }}</div>
            </div>

            <div class="attempt-actions">
              <el-input
                v-model="attempt.review_score_input"
                :placeholder="`分数 0-${formatScore(homework?.max_score)}`"
                class="review-score-input"
              />
              <el-input
                v-model="attempt.review_comment_input"
                type="textarea"
                :rows="2"
                placeholder="该次提交的评语（支持 Markdown / LaTeX）"
                class="review-comment-input"
              />
              <el-button type="primary" :loading="attempt.saving_review" @click="saveReview(currentHistoryRow, attempt)">
                按此提交评分
              </el-button>
              <el-button
                v-if="homework?.auto_grading_enabled"
                :loading="attempt.regrading"
                @click="regrade(currentHistoryRow, attempt)"
              >
                重评此提交
              </el-button>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>

    <el-dialog v-model="logDialogVisible" :title="logDialogTitle" width="720px" destroy-on-close>
      <pre class="llm-log-pre" data-testid="dialog-llm-log-body">{{ logDialogBody }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import api from '@/api'
import CourseDiscussionPanel from '@/components/CourseDiscussionPanel.vue'
import FeedbackRichText from '@/components/FeedbackRichText.vue'
import RichMarkdownDisplay from '@/components/RichMarkdownDisplay.vue'
import { useUserStore } from '@/stores/user'
import { downloadAttachment } from '@/utils/attachments'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const downloading = ref(false)
const batchRegrading = ref(false)
const homework = ref(null)
const submissions = ref([])
const selectedRows = ref([])
const historyVisible = ref(false)
const currentHistoryRow = ref(null)
const historyAttempts = ref([])
const logDialogVisible = ref(false)
const logDialogTitle = ref('LLM 调用日志')
const logDialogBody = ref('')

const submissionPage = ref(1)
const submissionPageSize = 20
const submissionTotal = ref(0)
const filterStudentId = ref(
  route.query.student_id ? Number(route.query.student_id) : null
)

const detailVisible = ref(false)
const detailRow = ref(null)
const detailAckLoading = ref(false)

const selectedCourse = computed(() => userStore.selectedCourse)
const downloadableSelection = computed(() =>
  selectedRows.value.filter(row => row.submission_id && row.attachment_url)
)

const regradableSelection = computed(() =>
  selectedRows.value.filter(row => row.submission_id && row.status === 'submitted' && homework.value?.auto_grading_enabled)
)

const buildAttemptHistoryRow = row => ({
  ...row,
  review_score_input: row.review_score === null || row.review_score === undefined ? '' : String(row.review_score),
  review_comment_input: row.review_comment || '',
  saving_review: false,
  regrading: false,
  task_log: row.task_log || [],
  task_error_code: row.task_error_code || null
})

const buildSubmissionRow = row => ({
  ...row,
  review_score_input: row.review_score === null || row.review_score === undefined ? '' : String(row.review_score),
  review_comment_input: row.review_comment || '',
  saving_review: false,
  regrading: false,
  latest_task_log: row.latest_task_log || [],
  latest_task_error_code: row.latest_task_error_code || null
})

const syncDetailFromList = () => {
  if (!detailVisible.value || !detailRow.value?.submission_id) {
    return
  }
  const sid = detailRow.value.submission_id
  const found = submissions.value.find(r => r.submission_id === sid)
  if (found) {
    const saving = detailRow.value.saving_review
    Object.assign(detailRow.value, buildSubmissionRow(found))
    detailRow.value.saving_review = saving
  }
}

const loadPage = async () => {
  loading.value = true
  try {
    const [homeworkDetail, submissionResult] = await Promise.all([
      api.homework.get(route.params.id),
      api.homework.getSubmissions(route.params.id, {
        page: submissionPage.value,
        page_size: submissionPageSize
      })
    ])
    homework.value = homeworkDetail
    submissionTotal.value = Number(submissionResult?.total || 0)
    submissions.value = (submissionResult?.data || []).map(buildSubmissionRow)
    selectedRows.value = []
    syncDetailFromList()
    scrollToHighlight()
  } finally {
    loading.value = false
  }
}

const submissionRowClassName = ({ row }) => {
  if (filterStudentId.value && row.student_id === filterStudentId.value) {
    return 'row-highlight'
  }
  return ''
}

const scrollToHighlight = () => {
  if (!filterStudentId.value) return
  requestAnimationFrame(() => {
    const el = document.querySelector('.row-highlight')
    el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  })
}

const openDetail = row => {
  detailRow.value = buildSubmissionRow({ ...row })
  detailVisible.value = true
}

const acknowledgeAppealForDetail = async () => {
  if (!detailRow.value?.submission_id) return
  detailAckLoading.value = true
  try {
    await api.homework.acknowledgeAppeal(route.params.id, detailRow.value.submission_id)
    ElMessage.success('已标记已阅')
    await loadPage()
  } finally {
    detailAckLoading.value = false
  }
}

const saveReviewFromDetail = async () => {
  if (!detailRow.value?.submission_id) {
    return
  }
  await saveReview(detailRow.value, null)
}

const handleSelectionChange = rows => {
  selectedRows.value = rows
}

const selectableForAnyBatchAction = row =>
  Boolean(row.submission_id && (row.attachment_url || row.status === 'submitted'))
const canReviewSubmission = row => row?.submission_id !== null && row?.submission_id !== undefined
const hasSavedReview = row =>
  (row.review_score !== null && row.review_score !== undefined) || Boolean(row.review_comment)

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

const taskFailureTooltip = row => {
  const code = row.latest_task_error_code ? `错误码：${row.latest_task_error_code}\n` : ''
  return `${code}${row.latest_task_error || ''}`.trim()
}

const attemptFailureTooltip = attempt => {
  const code = attempt.task_error_code ? `错误码：${attempt.task_error_code}\n` : ''
  return `${code}${attempt.task_error || ''}`.trim()
}

const openTaskLog = (row, attempt = null) => {
  const log = attempt?.task_log || row?.latest_task_log
  logDialogTitle.value = attempt
    ? `LLM 日志 · ${row?.student_name || ''} · 提交 #${attempt.id}`
    : `LLM 日志 · ${row?.student_name || ''}`
  logDialogBody.value = JSON.stringify(log || [], null, 2)
  logDialogVisible.value = true
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

const batchRegradeSelected = async () => {
  if (!regradableSelection.value.length) {
    return
  }
  batchRegrading.value = true
  try {
    const res = await api.homework.batchRegrade(route.params.id, {
      submission_ids: regradableSelection.value.map(r => r.submission_id),
      only_latest_attempt: true
    })
    ElMessage.success(`已入队 ${res.queued} 条，跳过 ${res.skipped} 条`)
    await loadPage()
  } catch {
    /* http 拦截器已提示 */
  } finally {
    batchRegrading.value = false
  }
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

const validateReviewScore = rawValue => {
  const rawScore = `${rawValue ?? ''}`.trim()
  const score = Number(rawScore)
  const maxScore = Number(homework.value?.max_score || 100)
  if (!rawScore || !Number.isFinite(score) || score < 0 || score > maxScore) {
    ElMessage.error(`请输入 0 到 ${formatScore(maxScore)} 之间的数字分数`)
    return null
  }
  return score
}

const saveReview = async (row, attempt = null) => {
  if (!canReviewSubmission(row)) {
    ElMessage.error('未提交的作业不能评分')
    return
  }

  const target = attempt || row
  const score = validateReviewScore(target.review_score_input)
  if (score === null) {
    return
  }

  target.saving_review = true
  try {
    await api.homework.reviewSubmission(route.params.id, row.submission_id, {
      attempt_id: attempt?.id || null,
      review_score: score,
      review_comment: target.review_comment_input?.trim() || null
    })
    ElMessage.success('评分已保存')
    await loadPage()
    syncDetailFromList()
    if (historyVisible.value && currentHistoryRow.value?.submission_id === row.submission_id) {
      await openHistory(row)
    }
  } finally {
    target.saving_review = false
  }
}

const regrade = async (row, attempt = null) => {
  if (!row?.submission_id) {
    return
  }
  const target = attempt || row
  target.regrading = true
  try {
    await api.homework.regradeSubmission(route.params.id, row.submission_id, {
      attempt_id: attempt?.id || null
    })
    ElMessage.success('已加入重评队列')
    await loadPage()
    if (historyVisible.value && currentHistoryRow.value?.submission_id === row.submission_id) {
      await openHistory(row)
    }
  } finally {
    target.regrading = false
  }
}

const openHistory = async row => {
  if (!row?.submission_id) {
    return
  }
  currentHistoryRow.value = row
  const history = await api.homework.getSubmissionHistory(route.params.id, row.submission_id)
  historyAttempts.value = (history?.attempts || []).map(buildAttemptHistoryRow)
  historyVisible.value = true
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
    historyVisible.value = false
    currentHistoryRow.value = null
    historyAttempts.value = []
    submissionPage.value = 1
    filterStudentId.value = route.query.student_id ? Number(route.query.student_id) : null
    detailVisible.value = false
    detailRow.value = null
    loadPage()
  }
)

watch(
  () => route.query.student_id,
  val => {
    filterStudentId.value = val ? Number(val) : null
    scrollToHighlight()
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

.muted-text,
.late-tip,
.history-meta {
  color: #64748b;
}

.table-wrapper {
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
}

.table-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.table-toolbar--bottom {
  margin-bottom: 0;
  margin-top: 12px;
}

:deep(.row-highlight) {
  background-color: #fffbeb !important;
}

.detail-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.detail-review-block {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.review-cell,
.attempt-actions {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr) auto auto;
  gap: 8px;
  align-items: center;
}

.review-score-input {
  width: 96px;
}

.review-comment-input {
  min-width: 160px;
}

.review-result,
.task-cell {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #475569;
  font-size: 13px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.attempt-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  background: #fff;
}

.attempt-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.attempt-body {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #475569;
  white-space: pre-wrap;
}

.attempt-feedback {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #fafbfc;
}

.feedback-inline {
  margin-top: 8px;
}

.attempt-error {
  color: #dc2626;
  font-size: 13px;
}

.attempt-actions {
  margin-top: 12px;
}

:deep(.table-wrapper .el-table) {
  min-width: 1180px;
}

@media (max-width: 768px) {
  .page-header,
  .history-header {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions :deep(.el-button) {
    flex: 1;
  }

  .review-cell,
  .attempt-actions {
    grid-template-columns: 1fr;
  }

  .review-score-input {
    width: 100%;
  }
}
</style>

