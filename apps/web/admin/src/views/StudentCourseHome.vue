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
      <!-- 统一：标题行 + 内容区 -->
      <section class="panel-card panel-card--overview">
        <header class="panel-header">
          <div class="panel-header__titles">
            <h2 class="panel-title">课程概览</h2>
            <p class="panel-desc">学期、任课教师与上课时间</p>
          </div>
        </header>
        <div class="overview-body">
          <div class="overview-meta">
            <span class="meta-item">
              <el-icon class="meta-icon"><Calendar /></el-icon>
              <span class="meta-label">学期</span>
              <span class="meta-value">{{ selectedCourse.semester || '未设置' }}</span>
            </span>
            <span class="meta-divider" aria-hidden="true" />
            <span class="meta-item">
              <el-icon class="meta-icon"><User /></el-icon>
              <span class="meta-label">任课老师</span>
              <span class="meta-value">{{ selectedCourse.teacher_name || '未分配' }}</span>
            </span>
          </div>
          <div class="overview-schedule">
            <div class="schedule-head">
              <span class="schedule-label">
                <el-icon><Clock /></el-icon>
                课程时间
              </span>
              <el-button
                v-if="courseTimeCards.length > 1"
                text
                type="primary"
                class="panel-link"
                @click="scheduleExpanded = !scheduleExpanded"
              >
                {{ scheduleExpanded ? '收起' : `展开全部（${courseTimeCards.length} 条）` }}
              </el-button>
            </div>
            <template v-if="visibleCourseTimes.length">
              <ul class="schedule-list">
                <li
                  v-for="(courseTime, index) in visibleCourseTimes"
                  :key="`${courseTime.dateRange}-${courseTime.weekday}-${index}`"
                  class="schedule-row"
                >
                  <span class="schedule-row__title">{{ formatCourseTimeTitle(courseTime) }}</span>
                  <span v-if="courseTime.time" class="schedule-row__time">{{ courseTime.time }}</span>
                </li>
              </ul>
            </template>
            <p v-else class="empty-inline">未设置上课时间</p>
          </div>
        </div>
      </section>

      <!-- 主区：作业优先全宽 -->
      <section class="panel-card panel-card--homework">
        <header class="panel-header">
          <div class="panel-header__titles">
            <h2 class="panel-title">课程作业</h2>
            <p class="panel-desc">最近布置的作业</p>
          </div>
          <el-button text type="primary" class="panel-link panel-link--strong" @click="router.push('/homework')">
            查看全部
          </el-button>
        </header>
        <el-skeleton :loading="loading" animated :rows="3">
          <template v-if="!homeworks.length">
            <p class="empty-inline">暂无作业。有新作业时会显示在这里；也可点击上方「查看全部」进入作业列表。</p>
          </template>
          <ul v-else class="item-list item-list--homework">
            <li v-for="item in homeworksPreview" :key="item.id">
              <button class="item-row item-row--homework" type="button" @click="router.push('/homework')">
                <el-icon class="item-row__icon"><EditPen /></el-icon>
                <span class="item-row__main">
                  <span class="item-row__title">{{ item.title }}</span>
                  <span class="item-row__meta item-row__meta--accent">截止 {{ formatDate(item.due_date) }}</span>
                </span>
              </button>
            </li>
          </ul>
        </el-skeleton>
      </section>

      <!-- 次要：资料 + 通知并排 -->
      <el-row :gutter="16" class="secondary-row">
        <el-col :xs="24" :md="12">
          <section class="panel-card">
            <header class="panel-header">
              <div class="panel-header__titles">
                <h2 class="panel-title">课程资料</h2>
                <p class="panel-desc">最近发布的资料</p>
              </div>
              <el-button text type="primary" class="panel-link" @click="router.push('/materials')">查看全部</el-button>
            </header>
            <el-skeleton :loading="loading" animated :rows="2">
              <template v-if="!materials.length">
                <p class="empty-inline">暂无资料。</p>
                <el-button text type="primary" size="small" class="empty-cta empty-cta--text" @click="router.push('/materials')">
                  去资料库
                </el-button>
              </template>
              <ul v-else class="item-list">
                <li v-for="item in materialsPreview" :key="item.id">
                  <button class="item-row" type="button" @click="router.push('/materials')">
                    <el-icon class="item-row__icon item-row__icon--muted"><Document /></el-icon>
                    <span class="item-row__main">
                      <span class="item-row__title">{{ item.title }}</span>
                      <span class="item-row__meta">{{ item.creator_name || '教师' }} · {{ formatDate(item.created_at) }}</span>
                    </span>
                  </button>
                </li>
              </ul>
            </el-skeleton>
          </section>
        </el-col>
        <el-col :xs="24" :md="12">
          <section class="panel-card">
            <header class="panel-header">
              <div class="panel-header__titles">
                <h2 class="panel-title">课程通知</h2>
                <p class="panel-desc">最近收到的通知</p>
              </div>
              <el-button text type="primary" class="panel-link" @click="router.push('/notifications')">查看全部</el-button>
            </header>
            <el-skeleton :loading="loading" animated :rows="2">
              <template v-if="!notifications.length">
                <p class="empty-inline">暂无通知。</p>
                <el-button text type="primary" size="small" class="empty-cta empty-cta--text" @click="router.push('/notifications')">
                  去通知中心
                </el-button>
              </template>
              <ul v-else class="item-list">
                <li v-for="item in notificationsPreview" :key="item.id">
                  <button class="item-row" type="button" @click="router.push('/notifications')">
                    <el-icon class="item-row__icon item-row__icon--muted"><Bell /></el-icon>
                    <span class="item-row__main">
                      <span class="item-row__title">{{ item.title }}</span>
                      <span class="item-row__meta">{{ priorityText(item.priority) }} · {{ formatDate(item.created_at) }}</span>
                    </span>
                  </button>
                </li>
              </ul>
            </el-skeleton>
          </section>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup>
import { Bell, Calendar, Clock, Document, EditPen, User } from '@element-plus/icons-vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { buildCourseTimeCards } from '@/utils/courseTimes'
import { onNotificationRefresh } from '@/utils/notificationSync'

const router = useRouter()
const userStore = useUserStore()

const PREVIEW_COUNT = 3

const selectedCourse = computed(() => userStore.selectedCourse)
const courseTimeCards = computed(() => buildCourseTimeCards(selectedCourse.value))
const scheduleExpanded = ref(false)

const visibleCourseTimes = computed(() => {
  const cards = courseTimeCards.value || []
  if (scheduleExpanded.value || cards.length <= 1) {
    return cards
  }
  return cards.slice(0, 1)
})

const loading = ref(false)
const materials = ref([])
const homeworks = ref([])
const notifications = ref([])

const materialsPreview = computed(() => (materials.value || []).slice(0, PREVIEW_COUNT))
const homeworksPreview = computed(() => (homeworks.value || []).slice(0, PREVIEW_COUNT))
const notificationsPreview = computed(() => (notifications.value || []).slice(0, PREVIEW_COUNT))

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

  scheduleExpanded.value = false
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

let unsubscribeNotificationRefresh = () => {}

onMounted(() => {
  loadWorkspace()
  unsubscribeNotificationRefresh = onNotificationRefresh(() => {
    loadWorkspace()
  })
})

onBeforeUnmount(() => {
  unsubscribeNotificationRefresh()
})

watch(selectedCourse, () => {
  loadWorkspace()
})
</script>

<style scoped>
.student-course-home {
  --sch-radius: 12px;
  --sch-radius-sm: 8px;
  --sch-gap: 16px;
  --sch-border: var(--wa-border-subtle);
  --sch-surface: var(--wa-color-surface);
  --sch-muted: var(--wa-color-text-muted);
  --sch-text: var(--wa-color-text);
  --sch-accent: var(--wa-color-primary-600);
  --sch-accent-soft: var(--wa-color-primary-50);
  --sch-row-bg: var(--wa-color-bg-soft);

  padding: 24px;
  max-width: 1100px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sch-gap);
  margin-bottom: var(--sch-gap);
}

.page-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: var(--sch-text);
  letter-spacing: -0.02em;
}

.page-subtitle {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--sch-muted);
  line-height: 1.5;
}

/* 统一卡片外壳 */
.panel-card {
  padding: 18px 20px;
  border: 1px solid var(--sch-border);
  border-radius: var(--sch-radius);
  background: var(--sch-surface);
  margin-bottom: var(--sch-gap);
}

.panel-card--overview {
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.panel-card--homework {
  border-color: #bfdbfe;
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.06);
  background: linear-gradient(180deg, #fafbff 0%, #fff 48%);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-header__titles {
  min-width: 0;
}

.panel-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--sch-text);
  line-height: 1.35;
}

.panel-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--sch-muted);
  line-height: 1.45;
}

.panel-link {
  flex-shrink: 0;
  font-weight: 500;
}

.panel-link--strong {
  font-weight: 600;
}

/* 概览：高密度 meta + 时间表 */
.overview-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.overview-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 16px;
  padding: 10px 12px;
  background: var(--sch-row-bg);
  border-radius: var(--sch-radius-sm);
  border: 1px solid #f1f5f9;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.meta-icon {
  font-size: 16px;
  color: var(--sch-muted);
}

.meta-label {
  color: var(--sch-muted);
}

.meta-value {
  font-weight: 600;
  color: var(--sch-text);
}

.meta-divider {
  width: 1px;
  height: 18px;
  background: var(--sch-border);
}

.overview-schedule {
  padding-top: 2px;
}

.schedule-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.schedule-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--sch-text);
}

.schedule-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.schedule-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: var(--sch-radius-sm);
  background: var(--sch-row-bg);
  border: 1px solid #f1f5f9;
}

.schedule-row__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--sch-text);
}

.schedule-row__time {
  font-size: 13px;
  color: var(--sch-muted);
}

/* 列表行 */
.item-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--sch-border);
  border-radius: var(--sch-radius-sm);
  background: var(--sch-surface);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.item-row:hover {
  border-color: #cbd5e1;
  background: #fafbfc;
}

.item-row--homework {
  border-color: #dbeafe;
  background: var(--sch-accent-soft);
}

.item-row--homework:hover {
  border-color: #93c5fd;
  background: #eff6ff;
}

.item-row__icon {
  flex-shrink: 0;
  margin-top: 2px;
  font-size: 18px;
  color: var(--sch-accent);
}

.item-row__icon--muted {
  color: #94a3b8;
}

.item-row__main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.item-row__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--sch-text);
  line-height: 1.4;
}

.item-row__meta {
  font-size: 12px;
  color: var(--sch-muted);
}

.item-row__meta--accent {
  color: #1d4ed8;
  font-weight: 500;
}

.empty-inline {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--sch-muted);
  line-height: 1.5;
}

.empty-cta {
  margin-top: 2px;
}

.empty-cta--text {
  padding-left: 0;
  height: auto;
}

.secondary-row {
  margin-top: 0;
}

@media (max-width: 768px) {
  .student-course-home {
    padding: 16px;
  }

  .meta-divider {
    display: none;
  }

  .overview-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
