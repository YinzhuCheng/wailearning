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
      <section class="overview-panel">
        <div class="overview-panel__head">
          <div>
            <h2 class="overview-panel__title">课程概览</h2>
            <p class="overview-panel__desc">学期、教师与上课时间</p>
          </div>
        </div>
        <div class="overview-meta">
          <span class="meta-chip">
            <el-icon class="meta-chip__icon"><Calendar /></el-icon>
            {{ selectedCourse.semester || '未设置学期' }}
          </span>
          <span class="meta-chip">
            <el-icon class="meta-chip__icon"><User /></el-icon>
            {{ selectedCourse.teacher_name || '未分配教师' }}
          </span>
        </div>
        <div class="overview-schedule">
          <div class="overview-schedule__head">
            <span class="overview-schedule__label">课程时间</span>
            <el-button
              v-if="courseTimeCards.length > 1"
              class="linkish"
              text
              type="primary"
              @click="scheduleExpanded = !scheduleExpanded"
            >
              {{ scheduleExpanded ? '收起' : `展开全部（${courseTimeCards.length}）` }}
            </el-button>
          </div>
          <div v-if="visibleCourseTimeCards.length" class="course-time-list course-time-list--compact">
            <div
              v-for="(courseTime, index) in visibleCourseTimeCards"
              :key="`${courseTime.dateRange}-${courseTime.weekday}-${index}`"
              class="course-time-card"
            >
              <strong class="course-time-card__title">{{ formatCourseTimeTitle(courseTime) }}</strong>
              <span v-if="courseTime.time" class="course-time-card__line">{{ courseTime.time }}</span>
            </div>
          </div>
          <p v-else class="overview-inline-muted">未设置课程时间</p>
        </div>
      </section>

      <el-row :gutter="20" class="workspace-grid">
        <el-col :xs="24" :lg="14">
          <section class="workspace-panel workspace-panel--primary">
            <div class="panel-header">
              <div>
                <h2 class="panel-title panel-title--accent">课程作业</h2>
                <p class="panel-sub">最近布置的作业 · 优先处理</p>
              </div>
              <el-button class="linkish" text type="primary" @click="router.push('/homework')">查看全部</el-button>
            </div>
            <el-skeleton :loading="loading" animated :rows="4">
              <div v-if="!displayHomeworks.length" class="panel-empty">
                <el-icon class="panel-empty__icon"><Document /></el-icon>
                <span>暂无作业</span>
                <el-button class="linkish" text type="primary" @click="router.push('/homework')">去作业列表</el-button>
              </div>
              <div v-else class="item-list">
                <button
                  v-for="item in displayHomeworks"
                  :key="item.id"
                  class="item-card item-card--homework"
                  type="button"
                  @click="router.push('/homework')"
                >
                  <strong>{{ item.title }}</strong>
                  <span class="item-card__due">截止：{{ formatDate(item.due_date) }}</span>
                </button>
              </div>
            </el-skeleton>
          </section>
        </el-col>

        <el-col :xs="24" :lg="5">
          <section class="workspace-panel workspace-panel--secondary">
            <div class="panel-header panel-header--tight">
              <div>
                <h2 class="panel-title">课程资料</h2>
                <p class="panel-sub">最近资料</p>
              </div>
              <el-button class="linkish" text type="primary" @click="router.push('/materials')">全部</el-button>
            </div>
            <el-skeleton :loading="loading" animated :rows="3">
              <div v-if="!displayMaterials.length" class="panel-empty panel-empty--compact">
                <el-icon class="panel-empty__icon"><FolderOpened /></el-icon>
                <span>暂无资料</span>
              </div>
              <div v-else class="item-list item-list--tight">
                <button
                  v-for="item in displayMaterials"
                  :key="item.id"
                  class="item-card item-card--compact"
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

        <el-col :xs="24" :lg="5">
          <section class="workspace-panel workspace-panel--secondary">
            <div class="panel-header panel-header--tight">
              <div>
                <h2 class="panel-title">课程通知</h2>
                <p class="panel-sub">最近通知</p>
              </div>
              <el-button class="linkish" text type="primary" @click="router.push('/notifications')">全部</el-button>
            </div>
            <el-skeleton :loading="loading" animated :rows="3">
              <div v-if="!displayNotifications.length" class="panel-empty panel-empty--compact">
                <el-icon class="panel-empty__icon"><Bell /></el-icon>
                <span>暂无通知</span>
              </div>
              <div v-else class="item-list item-list--tight">
                <button
                  v-for="item in displayNotifications"
                  :key="item.id"
                  class="item-card item-card--compact"
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
    </template>
  </div>
</template>

<script setup>
import { Bell, Calendar, Document, FolderOpened, User } from '@element-plus/icons-vue'
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

const PREVIEW_COUNT = 3

const displayMaterials = computed(() => materials.value.slice(0, PREVIEW_COUNT))
const displayHomeworks = computed(() => homeworks.value.slice(0, PREVIEW_COUNT))
const displayNotifications = computed(() => notifications.value.slice(0, PREVIEW_COUNT))

const scheduleExpanded = ref(false)

watch(
  courseTimeCards,
  cards => {
    scheduleExpanded.value = cards.length <= 1
  },
  { immediate: true }
)

const visibleCourseTimeCards = computed(() => {
  const cards = courseTimeCards.value
  if (!cards.length) {
    return []
  }
  if (scheduleExpanded.value || cards.length <= 1) {
    return cards
  }
  return [cards[0]]
})

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

onMounted(() => {
  loadWorkspace()
})

watch(selectedCourse, () => {
  loadWorkspace()
})
</script>

<style scoped>
.student-course-home {
  --sch-accent: #2563eb;
  --sch-accent-soft: rgba(37, 99, 235, 0.12);
  --sch-radius: 14px;
  --sch-radius-lg: 18px;
  --sch-border: #e2e8f0;
  --sch-text: #0f172a;
  --sch-muted: #64748b;
  --sch-surface: #fff;
  --sch-subtle-bg: #f8fafc;

  padding: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 28px;
  color: var(--sch-text);
}

.page-subtitle {
  margin: 8px 0 0;
  color: var(--sch-muted);
}

.overview-panel {
  margin-bottom: 20px;
  padding: 18px 20px;
  border: 1px solid var(--sch-border);
  border-radius: var(--sch-radius-lg);
  background: var(--sch-surface);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.05);
}

.overview-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.overview-panel__title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--sch-text);
}

.overview-panel__desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--sch-muted);
}

.overview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-bottom: 14px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--sch-text);
}

.meta-chip__icon {
  font-size: 16px;
  color: var(--sch-muted);
}

.overview-schedule__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.overview-schedule__label {
  font-size: 13px;
  font-weight: 600;
  color: var(--sch-muted);
}

.overview-inline-muted {
  margin: 0;
  font-size: 13px;
  color: var(--sch-muted);
}

.linkish {
  font-weight: 500;
}

.course-time-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.course-time-list--compact .course-time-card {
  padding: 10px 12px;
}

.course-time-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  border: 1px solid var(--sch-border);
  border-radius: var(--sch-radius);
  background: var(--sch-subtle-bg);
  text-align: left;
}

.course-time-card__line {
  font-size: 13px;
  line-height: 1.5;
  color: var(--sch-muted);
}

.course-time-card__title {
  font-size: 14px;
  line-height: 1.45;
  font-weight: 600;
  color: var(--sch-text);
}

.workspace-grid {
  align-items: stretch;
}

.workspace-panel {
  height: 100%;
  padding: 18px 18px 16px;
  border: 1px solid var(--sch-border);
  border-radius: var(--sch-radius-lg);
  background: var(--sch-surface);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.workspace-panel--primary {
  border-left: 4px solid var(--sch-accent);
  box-shadow: 0 14px 36px rgba(37, 99, 235, 0.07);
}

.workspace-panel--secondary {
  padding: 14px 14px 12px;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-header--tight {
  margin-bottom: 10px;
}

.panel-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--sch-text);
}

.panel-title--accent {
  font-size: 19px;
  color: var(--sch-text);
}

.panel-sub {
  margin: 4px 0 0;
  color: var(--sch-muted);
  font-size: 12px;
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.item-list--tight {
  gap: 8px;
}

.item-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--sch-border);
  border-radius: var(--sch-radius);
  background: var(--sch-subtle-bg);
  text-align: left;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}

.item-card--compact {
  padding: 10px 12px;
}

.item-card--homework {
  border-color: rgba(37, 99, 235, 0.22);
  background: #fff;
}

.item-card span {
  font-size: 12px;
  line-height: 1.5;
  color: var(--sch-muted);
}

.item-card__due {
  font-size: 13px;
  font-weight: 500;
  color: var(--sch-accent);
}

.item-card strong {
  font-size: 15px;
  line-height: 1.45;
  font-weight: 600;
  color: var(--sch-text);
}

.item-card--compact strong {
  font-size: 14px;
}

.item-card:hover {
  transform: translateY(-1px);
  border-color: #bfdbfe;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.08);
}

.panel-empty {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 12px 14px;
  border: 1px dashed #cbd5e1;
  border-radius: var(--sch-radius);
  background: var(--sch-subtle-bg);
  font-size: 13px;
  color: var(--sch-muted);
}

.panel-empty--compact {
  padding: 10px 12px;
  font-size: 12px;
}

.panel-empty__icon {
  font-size: 18px;
  color: #94a3b8;
}

@media (max-width: 1024px) {
  .workspace-panel {
    margin-bottom: 16px;
  }

  .workspace-panel--secondary {
    margin-bottom: 16px;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
