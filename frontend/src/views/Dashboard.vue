<template>
  <div class="dashboard">
    <div class="page-header">
      <div>
        <h1 class="page-title">课程仪表盘</h1>
        <p class="page-subtitle">
          {{ selectedCourse ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分班级'}` : '请先选择一门课程。' }}
        </p>
      </div>
      <div v-if="showSemesterFilter" class="header-actions">
        <el-select v-model="semester" placeholder="选择学期" style="width: 220px" @change="loadAll">
          <el-option label="全部学期" value="" />
          <el-option v-for="item in semesters" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </div>
    </div>

    <el-empty
      v-if="!selectedCourse && isTeachingDashboard"
      description="请先选择一门课程。"
    />

    <div v-else class="dashboard-grid">
      <div class="metrics-grid">
        <button
          v-for="card in statCards"
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

      <div class="calendar-card">
        <TeachingCalendar :course="selectedCourse" />
      </div>

      <button
        type="button"
        class="score-card"
        @click="goTo('/scores')"
      >
        <div class="score-card__header">
          <h3>平均成绩</h3>
          <span class="score-card__link">前往成绩管理</span>
        </div>
        <div ref="scoreChartRef" class="chart-box"></div>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Bell, CollectionTag, Document, Histogram, User } from '@element-plus/icons-vue'

import api from '@/api'
import TeachingCalendar from '@/components/TeachingCalendar.vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const selectedCourse = computed(() => userStore.selectedCourse)
const isTeachingDashboard = computed(() => userStore.isTeacher || userStore.isClassTeacher)
const showSemesterFilter = computed(() => !isTeachingDashboard.value)

const semester = ref('')
const semesters = ref([])
const scoreChartRef = ref(null)

let scoreChart = null

const stats = reactive({
  total_students: 0,
  avg_score: 0
})

const resourceCounts = reactive({
  materials: 0,
  homeworks: 0,
  notifications: 0
})

const statCards = computed(() => [
  { label: '学生总数', value: stats.total_students, color: '#2563eb', icon: User, path: '/students' },
  { label: '资料数量', value: resourceCounts.materials, color: '#0f766e', icon: Document, path: '/materials' },
  { label: '作业数量', value: resourceCounts.homeworks, color: '#d97706', icon: CollectionTag, path: '/homework' },
  { label: '通知数量', value: resourceCounts.notifications, color: '#dc2626', icon: Bell, path: '/notifications' }
])

const buildQuery = () => ({
  semester: semester.value || undefined,
  subject_id: selectedCourse.value?.id
})

const resetStats = () => {
  stats.total_students = 0
  stats.avg_score = 0
  resourceCounts.materials = 0
  resourceCounts.homeworks = 0
  resourceCounts.notifications = 0
}

const loadSemesters = async () => {
  const data = await api.semesters.list()
  semesters.value = (data || []).map(item => ({
    label: item.name,
    value: item.name
  }))
}

const loadStats = async () => {
  const data = await api.dashboard.getStats(buildQuery())
  stats.total_students = Number(data?.total_students || 0)
  stats.avg_score = Number(data?.avg_score || 0)
}

const loadResourceCounts = async () => {
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

const ensureChart = async () => {
  await nextTick()

  if (scoreChartRef.value && !scoreChart) {
    scoreChart = echarts.init(scoreChartRef.value)
  }
}

const updateChart = () => {
  if (!scoreChart) {
    return
  }

  scoreChart.setOption({
    series: [{
      type: 'gauge',
      startAngle: 180,
      endAngle: 0,
      min: 0,
      max: 100,
      splitNumber: 8,
      axisLine: {
        lineStyle: {
          width: 8,
          color: [
            [0.4, '#67e8f9'],
            [0.7, '#38bdf8'],
            [1, '#2563eb']
          ]
        }
      },
      pointer: { itemStyle: { color: '#1d4ed8' } },
      axisTick: { show: false },
      splitLine: { length: 12, lineStyle: { width: 2, color: '#94a3b8' } },
      axisLabel: { color: '#64748b' },
      detail: {
        valueAnimation: true,
        formatter: '{value} 分',
        color: '#0f172a',
        fontSize: 26
      },
      data: [{ value: stats.avg_score || 0 }]
    }]
  })
}

const loadAll = async () => {
  if (isTeachingDashboard.value && !selectedCourse.value) {
    resetStats()
    return
  }

  await Promise.all([loadStats(), loadResourceCounts()])
  await ensureChart()
  updateChart()
}

const resizeChart = () => {
  scoreChart?.resize()
}

const goTo = path => {
  router.push(path)
}

onMounted(async () => {
  if (showSemesterFilter.value) {
    await loadSemesters()
  }

  await loadAll()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  scoreChart?.dispose()
})

watch(selectedCourse, async () => {
  await loadAll()
})
</script>

<style scoped>
.dashboard {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
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

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(520px, 2.1fr);
  gap: 20px;
  align-items: stretch;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  grid-column: 1;
  grid-row: 1 / span 2;
  align-self: start;
}

.metric-card,
.calendar-card,
.score-card {
  background: #fff;
  border: 0;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
}

.metric-card,
.score-card {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card:hover,
.score-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 34px rgba(37, 99, 235, 0.14);
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 128px;
  padding: 22px;
  text-align: left;
}

.metric-icon {
  width: 54px;
  height: 54px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
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
  grid-column: 2;
  grid-row: 1 / span 2;
  padding: 22px;
}

.score-card {
  grid-column: 1 / span 2;
  grid-row: 3;
  padding: 22px;
  text-align: left;
}

.score-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.chart-box {
  height: 320px;
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .metrics-grid,
  .calendar-card,
  .score-card {
    grid-column: auto;
    grid-row: auto;
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
