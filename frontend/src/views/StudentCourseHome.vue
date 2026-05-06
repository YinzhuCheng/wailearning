<template>
  <div class="student-course-home">
    <div class="page-header">
      <div>
        <h1 class="page-title">课程主页</h1>
        <p class="page-subtitle">
          {{ selectedCourse ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分配班级'}` : '请先从课程列表中选择一门课程。' }}
        </p>
      </div>
    </div>

    <el-empty v-if="!selectedCourse" description="请先选择一门课程。" />

    <template v-else>
      <section class="course-overview">
        <article class="overview-card">
          <span class="overview-label">学期</span>
          <strong>{{ selectedCourse.semester || '未设置' }}</strong>
        </article>
        <article class="overview-card">
          <span class="overview-label">任课老师</span>
          <strong>{{ selectedCourse.teacher_name || '未分配' }}</strong>
        </article>
        <article class="overview-card overview-card-schedule">
          <span class="overview-label">课程时间</span>
          <div v-if="courseTimeCards.length" class="course-time-list">
            <div
              v-for="(courseTime, index) in courseTimeCards"
              :key="`${courseTime.dateRange}-${courseTime.weekday}-${index}`"
              class="course-time-card"
            >
              <strong class="course-time-card__title">{{ formatCourseTimeTitle(courseTime) }}</strong>
              <span v-if="courseTime.time" class="course-time-card__line">{{ courseTime.time }}</span>
            </div>
          </div>
          <strong v-else>未设置</strong>
        </article>
      </section>

      <el-row :gutter="20" class="workspace-grid">
        <el-col :xs="24" :lg="8">
          <section class="workspace-panel">
            <div class="panel-header">
              <div>
                <h2>课程资料</h2>
                <p>最近发布的资料</p>
              </div>
              <el-button text @click="router.push('/materials')">查看全部</el-button>
            </div>
            <el-skeleton :loading="loading" animated :rows="4">
              <el-empty v-if="!materials.length" description="暂无课程资料" />
              <div v-else class="item-list">
                <button
                  v-for="item in materials"
                  :key="item.id"
                  class="item-card"
                  type="button"
                  @click="router.push('/materials')"
                >
                  <strong>{{ item.title }}</strong>
                  <span>{{ item.creator_name || '教师' }} · {{ formatDate(item.created_at) }}</span>
                </button>
              </div>
            </el-skeleton>
          </section>
        </el-col>

        <el-col :xs="24" :lg="8">
          <section class="workspace-panel">
            <div class="panel-header">
              <div>
                <h2>课程作业</h2>
                <p>最近布置的作业</p>
              </div>
              <el-button text @click="router.push('/homework')">查看全部</el-button>
            </div>
            <el-skeleton :loading="loading" animated :rows="4">
              <el-empty v-if="!homeworks.length" description="暂无课程作业" />
              <div v-else class="item-list">
                <button
                  v-for="item in homeworks"
                  :key="item.id"
                  class="item-card"
                  type="button"
                  @click="router.push('/homework')"
                >
                  <strong>{{ item.title }}</strong>
                  <span>截止：{{ formatDate(item.due_date) }}</span>
                </button>
              </div>
            </el-skeleton>
          </section>
        </el-col>

        <el-col :xs="24" :lg="8">
          <section class="workspace-panel">
            <div class="panel-header">
              <div>
                <h2>课程通知</h2>
                <p>最近收到的通知</p>
              </div>
              <el-button text @click="router.push('/notifications')">查看全部</el-button>
            </div>
            <el-skeleton :loading="loading" animated :rows="4">
              <el-empty v-if="!notifications.length" description="暂无课程通知" />
              <div v-else class="item-list">
                <button
                  v-for="item in notifications"
                  :key="item.id"
                  class="item-card"
                  type="button"
                  @click="router.push('/notifications')"
                >
                  <strong>{{ item.title }}</strong>
                  <span>{{ priorityText(item.priority) }} · {{ formatDate(item.created_at) }}</span>
                </button>
              </div>
            </el-skeleton>
          </section>
        </el-col>
      </el-row>

      <section v-if="userStore.isStudent && selectedCourse" class="assistant-panel">
        <h2>智能助教</h2>
        <p class="assistant-hint">与课程级 LLM 策略一致；若学校尚未配置可用端点或本课未启用 LLM，将无法对话。</p>
        <el-alert v-if="assistantReason" type="warning" :closable="false" :title="assistantReason" class="assistant-blocked" />
        <template v-else>
          <el-input
            v-model="assistantInput"
            type="textarea"
            :rows="3"
            placeholder="输入问题后发送（实验性）"
            :disabled="assistantSending"
          />
          <el-button type="primary" class="assistant-send" :loading="assistantSending" :disabled="!assistantInput.trim()" @click="sendAssistant">
            发送
          </el-button>
          <div v-if="assistantReply" class="assistant-reply">{{ assistantReply }}</div>
        </template>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { buildCourseTimeCards } from '@/utils/courseTimes'

const router = useRouter()
const userStore = useUserStore()

const selectedCourse = computed(() => userStore.selectedCourse)
const courseTimeCards = computed(() => buildCourseTimeCards(selectedCourse.value))
const loading = ref(false)
const materials = ref([])
const homeworks = ref([])
const notifications = ref([])

const assistantReason = ref('')
const assistantInput = ref('')
const assistantReply = ref('')
const assistantSending = ref(false)

const loadAssistantGate = async () => {
  assistantReason.value = ''
  assistantReply.value = ''
  if (!userStore.isStudent || !selectedCourse.value) {
    return
  }
  try {
    const r = await api.llmSettings.getAssistantAvailability(selectedCourse.value.id)
    if (!r?.can_chat) {
      const map = {
        NO_VALIDATED_LLM_IN_SYSTEM: '系统尚无已通过视觉校验的 LLM 端点，智能助教不可用。',
        COURSE_LLM_NOT_ENABLED: '本课程未启用 LLM，请在教师端课程管理中开启。'
      }
      assistantReason.value = map[r?.reason_code] || '当前无法使用智能助教。'
    }
  } catch {
    assistantReason.value = '无法获取智能助教状态。'
  }
}

const sendAssistant = async () => {
  if (!selectedCourse.value || !assistantInput.value.trim()) {
    return
  }
  assistantSending.value = true
  assistantReply.value = ''
  try {
    const res = await api.llmSettings.postAssistantChat(selectedCourse.value.id, {
      message: assistantInput.value.trim()
    })
    assistantReply.value = res?.reply || ''
  } catch (e) {
    assistantReply.value = '请求失败，请稍后再试。'
  } finally {
    assistantSending.value = false
  }
}

const formatCourseTimeTitle = courseTime =>
  [courseTime?.dateRange, courseTime?.weekday].filter(Boolean).join('，')

const formatDate = value => {
  if (!value) {
    return '未设置'
  }

  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const priorityText = priority => {
  const map = {
    normal: '普通',
    important: '重要',
    urgent: '紧急'
  }
  return map[priority] || '普通'
}

const loadWorkspace = async () => {
  if (!selectedCourse.value) {
    materials.value = []
    homeworks.value = []
    notifications.value = []
    assistantReason.value = ''
    assistantReply.value = ''
    return
  }

  loading.value = true

  try {
    const [materialsResult, homeworksResult, notificationsResult] = await Promise.all([
      api.materials.list({
        class_id: selectedCourse.value.class_id,
        subject_id: selectedCourse.value.id,
        page: 1,
        page_size: 5
      }),
      api.homework.list({
        class_id: selectedCourse.value.class_id,
        subject_id: selectedCourse.value.id,
        page: 1,
        page_size: 5
      }),
      api.notifications.list({
        subject_id: selectedCourse.value.id,
        page: 1,
        page_size: 5
      })
    ])

    materials.value = materialsResult?.data || []
    homeworks.value = homeworksResult?.data || []
    notifications.value = notificationsResult?.data || []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadWorkspace()
  await loadAssistantGate()
})

watch(selectedCourse, async () => {
  await loadWorkspace()
  await loadAssistantGate()
})
</script>

<style scoped>
.student-course-home {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  font-size: 28px;
  color: #0f172a;
}

.page-subtitle {
  margin: 8px 0 0;
  color: #64748b;
}

.course-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 24px;
  align-items: stretch;
}

.overview-card,
.workspace-panel {
  padding: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.overview-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.overview-card-schedule {
  gap: 12px;
}

.overview-label {
  font-size: 13px;
  color: #64748b;
}

.course-time-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.course-time-card,
.item-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  padding: 14px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #f8fafc;
  text-align: left;
}

.course-time-card__line,
.item-card span {
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.course-time-card__title,
.item-card strong {
  font-size: 16px;
  line-height: 1.5;
  font-weight: 700;
  color: #0f172a;
}

.workspace-grid {
  margin-top: 0;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.panel-header h2 {
  margin: 0;
  font-size: 20px;
  color: #0f172a;
}

.panel-header p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item-card {
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}

.item-card:hover {
  transform: translateY(-1px);
  border-color: #bfdbfe;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.08);
}

@media (max-width: 1024px) {
  .course-overview {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }
}

.assistant-panel {
  margin-top: 28px;
  padding: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.assistant-panel h2 {
  margin: 0 0 8px;
  font-size: 20px;
  color: #0f172a;
}

.assistant-hint {
  margin: 0 0 14px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.assistant-blocked {
  margin-top: 4px;
}

.assistant-send {
  margin-top: 12px;
}

.assistant-reply {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f1f5f9;
  color: #0f172a;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>
