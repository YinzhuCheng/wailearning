<template>
  <div class="dashboard">
    <div class="page-header">
      <div>
        <h1 class="page-title">课程仪表盘</h1>
        <p class="page-subtitle">
          {{ selectedCourse ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分班级'}` : '请先选择一门课程。' }}
        </p>
        <p v-if="selectedCourse?.weekly_schedule || selectedCourse?.course_start_at || selectedCourse?.course_end_at" class="page-subtitle secondary-subtitle">
          {{ formatScheduleDisplay(selectedCourse?.weekly_schedule) || '未设置每周时间' }} · {{ formatDateRange(selectedCourse?.course_start_at, selectedCourse?.course_end_at) }}
        </p>
      </div>
      <div class="header-actions">
        <el-button v-if="userStore.isTeacher || userStore.isClassTeacher" type="primary" plain @click="router.push('/courses')">
          新建课程
        </el-button>
        <el-select v-model="semester" placeholder="选择学期" style="width: 220px" @change="loadAll">
          <el-option label="全部学期" value="" />
          <el-option v-for="item in semesters" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </div>
    </div>

    <el-empty
      v-if="!selectedCourse && !userStore.isAdmin"
      description="请先选择一门课程。"
    />

    <template v-else>
      <el-row :gutter="20" class="stats-row">
        <el-col :span="6" v-for="card in statCards" :key="card.label">
          <div class="stat-card">
            <div class="stat-icon" :style="{ background: card.color }">
              <el-icon :size="28"><component :is="card.icon" /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="20" class="charts-row">
        <el-col :span="12">
          <div class="chart-card">
            <h3>平均成绩</h3>
            <div ref="scoreChartRef" class="chart-box"></div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="chart-card">
            <h3>最近成绩</h3>
            <el-table :data="stats.recent_scores" max-height="320">
              <el-table-column prop="student_name" label="学生" />
              <el-table-column prop="subject_name" label="课程" />
              <el-table-column prop="score" label="成绩" width="90" />
              <el-table-column prop="exam_type" label="考试类型" width="120" />
            </el-table>
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="20" class="charts-row">
        <el-col :span="24">
          <div class="chart-card">
            <h3>班级平均成绩排名</h3>
            <div ref="rankingChartRef" class="chart-box"></div>
          </div>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Clock, Collection, School, User } from '@element-plus/icons-vue'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { formatScheduleValue } from '@/utils/courseSchedule'

const router = useRouter()
const userStore = useUserStore()
const selectedCourse = computed(() => userStore.selectedCourse)
const formatScheduleDisplay = value => formatScheduleValue(value) || value || ''

const semester = ref('')
const semesters = ref([])
const scoreChartRef = ref(null)
const rankingChartRef = ref(null)

let scoreChart = null
let rankingChart = null

const stats = reactive({
  total_students: 0,
  total_classes: 0,
  total_scores: 0,
  avg_score: 0,
  attendance_rate: 0,
  recent_scores: [],
  class_rankings: []
})

const statCards = computed(() => [
  { label: '学生总数', value: stats.total_students, color: '#2563eb', icon: User },
  { label: '关联班级', value: stats.total_classes, color: '#16a34a', icon: School },
  { label: '成绩记录', value: stats.total_scores, color: '#d97706', icon: Collection },
  { label: '最近一次考勤率', value: `${stats.attendance_rate}%`, color: '#dc2626', icon: Clock }
])

const buildQuery = () => ({
  semester: semester.value || undefined,
  subject_id: selectedCourse.value?.id
})

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

const formatDateRange = (startAt, endAt) => `${formatDate(startAt)} - ${formatDate(endAt)}`

const loadSemesters = async () => {
  const data = await api.semesters.list()
  semesters.value = (data || []).map(item => ({
    label: item.name,
    value: item.name
  }))
}

const loadStats = async () => {
  const data = await api.dashboard.getStats(buildQuery())
  Object.assign(stats, data || {})
}

const loadRankings = async () => {
  stats.class_rankings = await api.dashboard.getClassRankings(buildQuery())
}

const updateCharts = () => {
  if (scoreChart) {
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

  if (rankingChart) {
    rankingChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: (stats.class_rankings || []).map(item => item.class_name)
      },
      yAxis: { type: 'value', min: 0, max: 100 },
      series: [{
        data: (stats.class_rankings || []).map(item => item.avg_score),
        type: 'bar',
        itemStyle: {
          color: '#2563eb',
          borderRadius: [8, 8, 0, 0]
        }
      }]
    })
  }
}

const loadAll = async () => {
  await Promise.all([loadStats(), loadRankings()])
  updateCharts()
}

onMounted(async () => {
  await loadSemesters()
  scoreChart = echarts.init(scoreChartRef.value)
  rankingChart = echarts.init(rankingChartRef.value)
  await loadAll()
  window.addEventListener('resize', () => {
    scoreChart?.resize()
    rankingChart?.resize()
  })
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

.secondary-subtitle {
  margin-top: 6px;
}

.stats-row,
.charts-row {
  margin-top: 20px;
}

.stat-card,
.chart-card {
  background: #fff;
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 18px;
}

.stat-icon {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
}

.stat-label {
  color: #64748b;
  margin-top: 6px;
}

.chart-card h3 {
  margin: 0 0 16px;
  color: #0f172a;
}

.chart-box {
  height: 320px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
