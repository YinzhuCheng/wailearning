<template>
  <div class="dashboard">
    <div class="page-header">
      <div>
        <h1 class="page-title">课程仪表盘</h1>
        <p class="page-subtitle">
          {{ dashboardSubtitle }}
        </p>
      </div>

      <div v-if="showSemesterFilter" class="header-actions">
        <el-select v-model="semester" placeholder="选择学期" style="width: 220px" @change="loadLegacyDashboard">
          <el-option label="全部学期" value="" />
          <el-option v-for="item in semesters" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </div>
    </div>

    <el-empty
      v-if="isClassTeacherDashboard && !currentClassId"
      description="当前账号还没有绑定班级。"
    />

    <div
      v-else-if="isClassTeacherDashboard"
      v-loading="classDashboardLoading"
      class="class-dashboard-layout"
    >
      <div class="class-dashboard-cards">
        <button
          v-for="card in classTeacherCards"
          :key="card.label"
          type="button"
          class="class-metric-card"
          @click="goTo(card.path)"
        >
          <div class="class-metric-card__icon" :style="{ background: card.color }">
            <el-icon :size="24"><component :is="card.icon" /></el-icon>
          </div>
          <div class="class-metric-card__content">
            <span class="class-metric-card__label">{{ card.label }}</span>
            <strong class="class-metric-card__value">{{ card.value }}</strong>
          </div>
        </button>
      </div>

      <el-card shadow="never" class="class-dashboard-calendar">
        <ClassSemesterCalendar
          :class-name="currentClassName"
          :courses="currentClassCourses"
        />
      </el-card>
    </div>

    <template v-else>
      <el-empty
        v-if="!selectedCourse && isTeachingDashboard"
        description="请先选择一门课程。"
      />

      <div v-else class="legacy-dashboard-layout">
        <div class="legacy-dashboard-left">
          <div class="metrics-grid">
            <button
              v-for="card in legacyStatCards"
              :key="card.label"
              type="button"
              class="metric-card"
              @click="goTo(card.path)"
            >
              <div class="metric-icon" :style="{ background: card.color }">
                <el-icon :size="24"><component :is="card.icon" /></el-icon>
              </div>
              <div class="metric-content">
                <div class="metric-value">{{ card.value }}</div>
                <div class="metric-label">{{ card.label }}</div>
              </div>
            </button>
          </div>

          <button type="button" class="score-card" @click="goTo('/scores')">
            <div class="score-card__header">
              <h3>成绩分析</h3>
              <span class="score-card__link">前往成绩管理</span>
            </div>
            <div class="score-analysis">
              <div class="score-kpis">
                <div class="score-kpi">
                  <span class="score-kpi__label">总平均分</span>
                  <strong class="score-kpi__value">{{ fmtScore(stats.avg_score) }}</strong>
                </div>
                <div class="score-kpi">
                  <span class="score-kpi__label">最高分</span>
                  <strong class="score-kpi__value">{{ stats.total_scores ? fmtScore(stats.max_score) : '—' }}</strong>
                </div>
                <div class="score-kpi">
                  <span class="score-kpi__label">最低分</span>
                  <strong class="score-kpi__value">{{ stats.total_scores ? fmtScore(stats.min_score) : '—' }}</strong>
                </div>
                <div class="score-kpi">
                  <span class="score-kpi__label">成绩条数</span>
                  <strong class="score-kpi__value">{{ stats.total_scores || '—' }}</strong>
                </div>
                <div class="score-kpi">
                  <span class="score-kpi__label">有成绩人数</span>
                  <strong class="score-kpi__value">{{ stats.students_with_scores || '—' }}</strong>
                </div>
                <div class="score-kpi">
                  <span class="score-kpi__label">考核类型数</span>
                  <strong class="score-kpi__value">{{ stats.distinct_exam_types || '—' }}</strong>
                </div>
              </div>
              <div ref="trendChartRef" class="trend-chart" />
              <div v-if="topStudents.length" class="score-top">
                <span class="score-top__title">均分领先（前 5）</span>
                <ol class="score-top__list">
                  <li v-for="row in topStudents" :key="row.student_id">
                    <span class="score-top__name">{{ row.rank }}. {{ row.student_name || '—' }}</span>
                    <span class="score-top__avg">{{ fmtScore(row.avg_score) }}</span>
                  </li>
                </ol>
              </div>
              <p v-else class="score-empty">暂无排名数据；录入成绩后将显示。</p>
            </div>
          </button>
        </div>

        <el-card shadow="never" class="calendar-card">
          <TeachingCalendar :course="selectedCourse" />
        </el-card>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Bell, CollectionTag, Document, Reading, User } from '@element-plus/icons-vue'

import api from '@/api'
import ClassSemesterCalendar from '@/components/ClassSemesterCalendar.vue'
import TeachingCalendar from '@/components/TeachingCalendar.vue'
import { useUserStore } from '@/stores/user'
import {
  filterCoursesByClassId,
  filterImportantNotifications,
  filterNotificationsForClass,
  resolveClassTeacherClassId,
  resolveClassTeacherClassName
} from '@/utils/classTeacher'
import { loadAllPages } from '@/utils/pagedFetch'
import { onNotificationRefresh } from '@/utils/notificationSync'

const router = useRouter()
const userStore = useUserStore()

const semester = ref('')
const semesters = ref([])
const classDashboardLoading = ref(false)
const classTeacherCoursePool = ref([])
const importantNotifications = ref([])

let unsubscribeNotificationRefresh = () => {}

const stats = reactive({
  total_students: 0,
  total_scores: 0,
  avg_score: 0,
  max_score: 0,
  min_score: 0,
  students_with_scores: 0,
  distinct_exam_types: 0
})

const scoreTrends = ref({})
const topStudents = ref([])
const trendChartRef = ref(null)
let trendChart = null

const resourceCounts = reactive({
  materials: 0,
  homeworks: 0,
  notifications: 0
})

const classTeacherSummary = reactive({
  studentCount: 0,
  courseCount: 0,
  notificationCount: 0
})

const selectedCourse = computed(() => userStore.selectedCourse)
const isTeachingDashboard = computed(() => userStore.isTeacher)
const isClassTeacherDashboard = computed(() => userStore.isClassTeacher)
const showSemesterFilter = computed(() => !isTeachingDashboard.value && !isClassTeacherDashboard.value)
const currentClassId = computed(() => resolveClassTeacherClassId(userStore.userInfo, classTeacherCoursePool.value))
const currentClassName = computed(() => resolveClassTeacherClassName(userStore.userInfo, classTeacherCoursePool.value) || '未分配班级')
const currentClassCourses = computed(() => filterCoursesByClassId(classTeacherCoursePool.value, currentClassId.value))

const dashboardSubtitle = computed(() => {
  if (isClassTeacherDashboard.value) {
    return currentClassId.value ? `当前班级：${currentClassName.value}` : '请先为班主任账号分配班级。'
  }

  if (selectedCourse.value) {
    return `${selectedCourse.value.name} · ${selectedCourse.value.class_name || '未分班级'}`
  }

  return '请先选择一门课程。'
})

const classTeacherCards = computed(() => [
  { label: '学生总数', value: classTeacherSummary.studentCount, color: '#2563eb', icon: User, path: '/students' },
  { label: '课程数量', value: classTeacherSummary.courseCount, color: '#0f766e', icon: Reading, path: '/subjects' },
  { label: '通知数量', value: classTeacherSummary.notificationCount, color: '#dc2626', icon: Bell, path: '/notifications' }
])

const legacyStatCards = computed(() => [
  { label: '学生总数', value: stats.total_students, color: '#2563eb', icon: User, path: '/students' },
  { label: '资料数量', value: resourceCounts.materials, color: '#0f766e', icon: Document, path: '/materials' },
  { label: '作业数量', value: resourceCounts.homeworks, color: '#d97706', icon: CollectionTag, path: '/homework' },
  { label: '通知数量', value: resourceCounts.notifications, color: '#dc2626', icon: Bell, path: '/notifications' }
])

const buildQuery = () => ({
  semester: semester.value || undefined,
  subject_id: selectedCourse.value?.id
})

const resetLegacyStats = () => {
  stats.total_students = 0
  stats.total_scores = 0
  stats.avg_score = 0
  stats.max_score = 0
  stats.min_score = 0
  stats.students_with_scores = 0
  stats.distinct_exam_types = 0
  resourceCounts.materials = 0
  resourceCounts.homeworks = 0
  resourceCounts.notifications = 0
  scoreTrends.value = {}
  topStudents.value = []
  if (trendChart) {
    trendChart.dispose()
    trendChart = null
  }
}

const loadSemesters = async () => {
  const data = await api.semesters.list()
  semesters.value = (data || []).map(item => ({
    label: item.name,
    value: item.name
  }))
}

const loadLegacyStats = async () => {
  const data = await api.dashboard.getStats(buildQuery())
  stats.total_students = Number(data?.total_students || 0)
  stats.total_scores = Number(data?.total_scores || 0)
  stats.avg_score = Number(data?.avg_score || 0)
  stats.max_score = Number(data?.max_score || 0)
  stats.min_score = Number(data?.min_score || 0)
  stats.students_with_scores = Number(data?.students_with_scores || 0)
  stats.distinct_exam_types = Number(data?.distinct_exam_types || 0)
}

const loadScoreAnalysis = async () => {
  if (!selectedCourse.value) {
    scoreTrends.value = {}
    topStudents.value = []
    if (trendChart) {
      trendChart.dispose()
      trendChart = null
    }
    return
  }

  const q = buildQuery()
  const [trends, rankings] = await Promise.all([
    api.dashboard.getTrends(q),
    api.dashboard.getStudentRankings({ ...q, limit: 5 })
  ])
  scoreTrends.value = trends && typeof trends === 'object' ? trends : {}
  topStudents.value = Array.isArray(rankings) ? rankings.slice(0, 5) : []
  await nextTick()
  updateTrendChart()
}

const fmtScore = v => {
  const n = Number(v)
  if (!Number.isFinite(n)) {
    return '—'
  }
  return n.toFixed(n % 1 === 0 ? 0 : 1)
}

const ensureTrendChart = async () => {
  await nextTick()
  if (trendChartRef.value && !trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
}

const updateTrendChart = async () => {
  const raw = scoreTrends.value || {}
  const entries = Object.entries(raw).filter(([, v]) => v && Number(v.count) > 0)
  if (!entries.length) {
    trendChart?.dispose()
    trendChart = null
    return
  }
  await ensureTrendChart()
  if (!trendChart) {
    return
  }
  const categories = entries.map(([k]) => k)
  const maxBar = Math.max(...entries.map(([, v]) => Number(v.avg) || 0), 0)
  const yMax = Math.min(150, Math.max(100, Math.ceil(maxBar * 1.08) || 100))
  trendChart.setOption(
    {
      color: ['#2563eb'],
      grid: { left: 6, right: 8, top: 22, bottom: 2, containLabel: true },
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          const p = params[0]
          const row = raw[p.name]
          if (!row) {
            return `${p.name}<br/>均分 ${p.value}`
          }
          return `${p.name}<br/>均分 ${row.avg} · 最高 ${row.max} · 最低 ${row.min} · ${row.count} 条`
        }
      },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: {
          fontSize: 11,
          color: '#64748b',
          interval: 0,
          rotate: categories.length > 4 ? 28 : 0
        },
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: yMax,
        splitNumber: 4,
        axisLabel: { fontSize: 11, color: '#94a3b8' },
        splitLine: { lineStyle: { color: '#f1f5f9' } }
      },
      series: [
        {
          name: '平均分',
          type: 'bar',
          data: entries.map(([, v]) => v.avg),
          barMaxWidth: 32,
          itemStyle: { borderRadius: [4, 4, 0, 0] }
        }
      ]
    },
    { notMerge: true }
  )
}

const loadLegacyResourceCounts = async () => {
  if (!selectedCourse.value) {
    resourceCounts.materials = 0
    resourceCounts.homeworks = 0
    resourceCounts.notifications = 0
    return
  }

  const params = {
    class_id: selectedCourse.value.class_id,
    subject_id: selectedCourse.value.id,
    page: 1,
    page_size: 1
  }

  const [materialsResult, homeworksResult, notificationsResult] = await Promise.all([
    api.materials.list(params),
    api.homework.list(params),
    api.notifications.list({
      subject_id: selectedCourse.value.id,
      page: 1,
      page_size: 1
    })
  ])

  resourceCounts.materials = Number(materialsResult?.total || 0)
  resourceCounts.homeworks = Number(homeworksResult?.total || 0)
  resourceCounts.notifications = Number(notificationsResult?.total || 0)
}

const loadLegacyDashboard = async () => {
  if (isTeachingDashboard.value && !selectedCourse.value) {
    resetLegacyStats()
    return
  }

  await Promise.all([loadLegacyStats(), loadLegacyResourceCounts(), loadScoreAnalysis()])
}

const loadClassTeacherDashboard = async () => {
  classDashboardLoading.value = true

  try {
    classTeacherCoursePool.value = await userStore.fetchTeachingCourses(true)
    const classId = resolveClassTeacherClassId(userStore.userInfo, classTeacherCoursePool.value)

    if (!classId) {
      classTeacherSummary.studentCount = 0
      classTeacherSummary.courseCount = 0
      classTeacherSummary.notificationCount = 0
      importantNotifications.value = []
      return
    }

    const classCourses = filterCoursesByClassId(classTeacherCoursePool.value, classId)
    const courseIds = new Set(classCourses.map(course => Number(course.id)))

    const [studentsResult, notificationRows] = await Promise.all([
      api.students.list({ class_id: classId, page: 1, page_size: 1 }),
      loadAllPages(params => api.notifications.list(params))
    ])

    importantNotifications.value = filterImportantNotifications(
      filterNotificationsForClass(notificationRows, classId, courseIds)
    )

    classTeacherSummary.studentCount = Number(studentsResult?.total || 0)
    classTeacherSummary.courseCount = classCourses.length
    classTeacherSummary.notificationCount = importantNotifications.value.length
  } finally {
    classDashboardLoading.value = false
  }
}

const resizeChart = () => {
  trendChart?.resize()
}

const goTo = path => {
  router.push(path)
}

onMounted(async () => {
  unsubscribeNotificationRefresh = onNotificationRefresh(async () => {
    if (isClassTeacherDashboard.value) {
      await loadClassTeacherDashboard()
    } else {
      await loadLegacyDashboard()
    }
  })

  if (isClassTeacherDashboard.value) {
    await loadClassTeacherDashboard()
  } else {
    if (showSemesterFilter.value) {
      await loadSemesters()
    }

    await loadLegacyDashboard()
    window.addEventListener('resize', resizeChart)
  }
})

onBeforeUnmount(() => {
  unsubscribeNotificationRefresh()
  window.removeEventListener('resize', resizeChart)
  trendChart?.dispose()
})

watch(
  () => userStore.userInfo?.id,
  async () => {
    if (isClassTeacherDashboard.value) {
      await loadClassTeacherDashboard()
    }
  }
)

watch(selectedCourse, async () => {
  if (!isClassTeacherDashboard.value) {
    await loadLegacyDashboard()
  }
})
</script>

<style scoped>
.dashboard {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
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

.class-dashboard-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 20px;
  align-items: stretch;
}

.class-dashboard-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.class-metric-card {
  display: flex;
  align-items: center;
  gap: 16px;
  border: 0;
  border-radius: 22px;
  background: #fff;
  padding: 24px 22px;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.class-metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 36px rgba(37, 99, 235, 0.14);
}

.class-metric-card__icon {
  display: flex;
  width: 56px;
  height: 56px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 18px;
  color: #fff;
}

.class-metric-card__content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.class-metric-card__label {
  color: #64748b;
  font-size: 14px;
}

.class-metric-card__value {
  font-size: 34px;
  color: #0f172a;
}

.class-dashboard-calendar {
  border-radius: 24px;
}

.legacy-dashboard-layout {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  align-items: stretch;
}

.legacy-dashboard-left {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 20px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.metric-card,
.score-card {
  border: 0;
  border-radius: 20px;
  background: #fff;
  cursor: pointer;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card:hover,
.score-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 34px rgba(37, 99, 235, 0.14);
}

.metric-card {
  display: flex;
  min-height: 128px;
  align-items: center;
  gap: 16px;
  padding: 22px;
  text-align: left;
}

.metric-icon {
  display: flex;
  width: 54px;
  height: 54px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 18px;
  color: #fff;
}

.metric-value {
  font-size: 30px;
  font-weight: 700;
  color: #0f172a;
}

.metric-label {
  margin-top: 6px;
  color: #64748b;
  font-size: 14px;
}

.calendar-card {
  min-width: 0;
  border-radius: 20px;
}

.score-card {
  padding: 22px;
  text-align: left;
}

.score-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.score-card__header h3 {
  margin: 0;
  color: #0f172a;
}

.score-card__link {
  font-size: 13px;
  color: #2563eb;
}

.score-analysis {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 4px;
}

.score-kpis {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px 12px;
}

.score-kpi {
  padding: 10px 12px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.score-kpi__label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.score-kpi__value {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.trend-chart {
  height: 168px;
  width: 100%;
}

.score-top__title {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 8px;
}

.score-top__list {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  font-size: 13px;
  line-height: 1.65;
}

.score-top__list li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding-right: 4px;
}

.score-top__avg {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: #2563eb;
}

.score-empty {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
}

@media (max-width: 768px) {
  .score-kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1200px) {
  .class-dashboard-layout,
  .legacy-dashboard-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .score-card__header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
