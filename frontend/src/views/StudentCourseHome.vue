<template>
  <div class="student-course-home">
    <div class="page-header">
      <div>
        <h1 class="page-title">课程主页</h1>
        <p class="page-subtitle">
          {{
            selectedCourse
              ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分配班级'}`
              : '请先从课程列表中选择一门课程。'
          }}
        </p>
      </div>
    </div>

    <el-empty v-if="!selectedCourse" description="请先选择一门课程。" />

    <template v-else>
      <!-- 课程信息：学期、教师、时间合并为一块，避免三格留白 -->
      <section class="course-meta-card">
        <div class="course-meta-card__head">
          <div>
            <h2 class="section-title">课程信息</h2>
            <p class="section-subtitle">学期、任课教师与上课安排</p>
          </div>
        </div>

        <div class="meta-chips">
          <div class="meta-chip">
            <el-icon class="meta-chip__icon" :size="18"><Calendar /></el-icon>
            <div class="meta-chip__text">
              <span class="meta-chip__label">学期</span>
              <span class="meta-chip__value">{{ selectedCourse.semester || '未设置' }}</span>
            </div>
          </div>
          <div class="meta-chip">
            <el-icon class="meta-chip__icon" :size="18"><User /></el-icon>
            <div class="meta-chip__text">
              <span class="meta-chip__label">任课老师</span>
              <span class="meta-chip__value">{{ selectedCourse.teacher_name || '未分配' }}</span>
            </div>
          </div>
        </div>

        <div class="schedule-block">
          <div class="schedule-block__label">课程时间</div>
          <div v-if="courseTimeCards.length" class="course-time-list">
            <div
              v-for="(courseTime, index) in courseTimeCards"
              :key="`${courseTime.dateRange}-${courseTime.weekday}-${index}`"
              class="course-time-row"
            >
              <span class="course-time-row__title">{{ formatCourseTimeTitle(courseTime) }}</span>
              <span v-if="courseTime.time" class="course-time-row__detail">{{ courseTime.time }}</span>
            </div>
          </div>
          <p v-else class="schedule-placeholder">未设置上课时间，可联系教师或教务。</p>
        </div>
      </section>

      <!-- 作业为主列，资料与通知次列堆叠 -->
      <div class="workspace-layout">
        <section class="workspace-panel workspace-panel--homework panel-homework">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">课程作业</h2>
              <p class="panel-desc">最近布置 · 点击跳转作业列表</p>
            </div>
            <el-button type="primary" link @click="router.push('/homework')">查看全部</el-button>
          </div>
          <el-skeleton :loading="loading" animated :rows="4">
            <div v-if="!homeworks.length" class="empty-inline">
              <el-icon class="empty-inline__icon" :size="22"><EditPen /></el-icon>
              <span>暂无作业</span>
              <el-button type="primary" link @click="router.push('/homework')">去作业页</el-button>
            </div>
            <div v-else class="item-list">
              <button
                v-for="item in homeworks"
                :key="item.id"
                class="item-card item-card--homework"
                type="button"
                @click="router.push('/homework')"
              >
                <strong>{{ item.title }}</strong>
                <span class="item-card__due">截止 {{ formatDate(item.due_date) }}</span>
              </button>
            </div>
          </el-skeleton>
        </section>

        <section class="workspace-panel panel-side panel-materials">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">课程资料</h2>
              <p class="panel-desc">最近发布</p>
            </div>
            <el-button text type="primary" @click="router.push('/materials')">全部</el-button>
          </div>
          <el-skeleton :loading="loading" animated :rows="3">
            <div v-if="!materials.length" class="empty-inline empty-inline--compact">
              <el-icon class="empty-inline__icon" :size="20"><Document /></el-icon>
              <span>暂无资料</span>
              <el-button text type="primary" @click="router.push('/materials')">去资料页</el-button>
            </div>
            <div v-else class="item-list item-list--compact">
              <button
                v-for="item in materials"
                :key="item.id"
                class="item-card item-card--side"
                type="button"
                @click="router.push('/materials')"
              >
                <strong>{{ item.title }}</strong>
                <span>{{ item.creator_name || '教师' }} · {{ formatDate(item.created_at) }}</span>
              </button>
            </div>
          </el-skeleton>
        </section>

        <section class="workspace-panel panel-side panel-notifications">
          <div class="panel-header">
            <div>
              <h2 class="panel-title">课程通知</h2>
              <p class="panel-desc">最近通知</p>
            </div>
            <el-button text type="primary" @click="router.push('/notifications')">全部</el-button>
          </div>
          <el-skeleton :loading="loading" animated :rows="3">
            <div v-if="!notifications.length" class="empty-inline empty-inline--compact">
              <el-icon class="empty-inline__icon" :size="20"><Bell /></el-icon>
              <span>暂无通知</span>
              <el-button text type="primary" @click="router.push('/notifications')">去通知页</el-button>
            </div>
            <div v-else class="item-list item-list--compact">
              <button
                v-for="item in notifications"
                :key="item.id"
                class="item-card item-card--side"
                type="button"
                @click="router.push('/notifications')"
              >
                <strong>{{ item.title }}</strong>
                <span>{{ priorityText(item.priority) }} · {{ formatDate(item.created_at) }}</span>
              </button>
            </div>
          </el-skeleton>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { Bell, Calendar, Document, EditPen, User } from '@element-plus/icons-vue'
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

const formatCourseTimeTitle = courseTime => [courseTime?.dateRange, courseTime?.weekday].filter(Boolean).join('，')

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
  --sch-accent-soft: rgba(37, 99, 235, 0.1);
  --sch-surface: #ffffff;
  --sch-border: #e2e8f0;
  --sch-muted: #64748b;
  --sch-text: #0f172a;
  --sch-radius-lg: 16px;
  --sch-radius-md: 12px;
  --sch-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 12px 32px rgba(15, 23, 42, 0.06);

  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px 40px;
}

.page-header {
  margin-bottom: 22px;
}

.page-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--sch-text);
}

.page-subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--sch-muted);
  line-height: 1.5;
}

.section-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--sch-text);
}

.section-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--sch-muted);
}

.course-meta-card {
  padding: 20px 22px 22px;
  margin-bottom: 22px;
  border: 1px solid var(--sch-border);
  border-radius: var(--sch-radius-lg);
  background: var(--sch-surface);
  box-shadow: var(--sch-shadow);
}

.course-meta-card__head {
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid #f1f5f9;
}

.meta-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 18px;
}

.meta-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 160px;
  padding: 10px 14px;
  border-radius: var(--sch-radius-md);
  background: #f8fafc;
  border: 1px solid #eef2f7;
}

.meta-chip__icon {
  color: var(--sch-accent);
  flex-shrink: 0;
}

.meta-chip__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.meta-chip__label {
  font-size: 12px;
  color: var(--sch-muted);
}

.meta-chip__value {
  font-size: 15px;
  font-weight: 600;
  color: var(--sch-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.schedule-block__label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--sch-muted);
  margin-bottom: 10px;
}

.course-time-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.course-time-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 14px;
  padding: 10px 14px;
  border-radius: var(--sch-radius-md);
  background: #f8fafc;
  border: 1px solid #eef2f7;
}

.course-time-row__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--sch-text);
}

.course-time-row__detail {
  font-size: 13px;
  color: var(--sch-muted);
}

.schedule-placeholder {
  margin: 0;
  font-size: 13px;
  color: var(--sch-muted);
}

/* 主：作业宽列；次：资料 + 通知堆叠 */
.workspace-layout {
  display: grid;
  gap: 18px;
  grid-template-columns: 1fr;
}

.workspace-panel {
  padding: 18px 20px 20px;
  border: 1px solid var(--sch-border);
  border-radius: var(--sch-radius-lg);
  background: var(--sch-surface);
  box-shadow: var(--sch-shadow);
}

.workspace-panel--homework {
  border-top: 3px solid var(--sch-accent);
  background: linear-gradient(180deg, var(--sch-accent-soft) 0%, #fff 48px);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--sch-text);
}

.panel-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--sch-muted);
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.item-list--compact {
  gap: 8px;
}

.item-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--sch-border);
  border-radius: var(--sch-radius-md);
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.item-card--homework {
  padding: 14px 16px;
  border-left: 4px solid var(--sch-accent);
  background: #fafbff;
}

.item-card--homework:hover {
  border-color: #bfdbfe;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.08);
  transform: translateY(-1px);
}

.item-card--side {
  padding: 10px 12px;
}

.item-card--side:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
}

.item-card strong {
  font-size: 15px;
  font-weight: 600;
  color: var(--sch-text);
  line-height: 1.4;
}

.item-card--side strong {
  font-size: 14px;
}

.item-card span {
  font-size: 12px;
  line-height: 1.5;
  color: var(--sch-muted);
}

.item-card__due {
  font-weight: 500;
  color: #1d4ed8;
}

.empty-inline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 16px 14px;
  border-radius: var(--sch-radius-md);
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  font-size: 13px;
  color: var(--sch-muted);
}

.empty-inline--compact {
  padding: 12px 12px;
  font-size: 12px;
}

.empty-inline__icon {
  color: #94a3b8;
  flex-shrink: 0;
}

@media (min-width: 900px) {
  .workspace-layout {
    grid-template-columns: minmax(0, 1.25fr) minmax(260px, 0.75fr);
    grid-template-rows: auto auto;
    align-items: stretch;
  }

  .panel-homework {
    grid-column: 1;
    grid-row: 1 / span 2;
  }

  .panel-materials {
    grid-column: 2;
    grid-row: 1;
  }

  .panel-notifications {
    grid-column: 2;
    grid-row: 2;
  }

  .panel-side {
    padding-bottom: 16px;
  }
}

@media (min-width: 600px) and (max-width: 899px) {
  .workspace-layout {
    grid-template-columns: 1fr 1fr;
  }

  .panel-homework {
    grid-column: 1 / -1;
  }

  .panel-materials {
    grid-column: 1;
  }

  .panel-notifications {
    grid-column: 2;
  }
}

@media (max-width: 599px) {
  .student-course-home {
    padding: 16px 14px 32px;
  }

  .page-title {
    font-size: 22px;
  }

  .meta-chips {
    flex-direction: column;
  }

  .meta-chip {
    min-width: 0;
  }
}
</style>
