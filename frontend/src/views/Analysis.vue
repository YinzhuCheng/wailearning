<template>
  <div class="analysis-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">学情分析</h1>
        <p class="page-subtitle">
          {{
            selectedCourse
              ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分配班级'}`
              : '请先选择课程后查看学情分析。'
          }}
        </p>
      </div>
      <div class="header-actions">
        <el-select v-model="semester" placeholder="选择学期" clearable style="width: 220px" @change="loadData">
          <el-option v-for="item in semesters" :key="item.id" :label="item.name" :value="item.name" />
        </el-select>
      </div>
    </div>

    <el-empty v-if="!selectedCourse" description="请先选择一门课程。" />

    <template v-else>
      <section class="analysis-section">
        <h2 class="section-title">考试成绩</h2>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>考试类型趋势</template>
              <div ref="trendChartRef" class="chart-box"></div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>课程成绩摘要</template>
              <el-table :data="subjectAnalysis">
                <el-table-column prop="subject_name" label="课程" />
                <el-table-column prop="avg_score" label="平均分" width="120" />
                <el-table-column prop="max_score" label="最高分" width="120" />
                <el-table-column prop="min_score" label="最低分" width="120" />
                <el-table-column prop="count" label="记录数" width="120" />
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </section>

      <section class="analysis-section">
        <h2 class="section-title">作业学情</h2>
        <p class="section-desc">
          基于历次作业的批改得分：上图展示全班各次作业均分走势；下图展示存在多次提交且均有得分的作业中，学生首末次得分的平均变化（正值表示多次提交后整体提升）。
        </p>
        <el-row v-loading="homeworkLoading" :gutter="20">
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>各次作业班级均分</template>
              <div ref="homeworkTrendChartRef" class="chart-box"></div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>多次提交：首末次均分变化</template>
              <div ref="resubmitLiftChartRef" class="chart-box"></div>
            </el-card>
          </el-col>
        </el-row>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

import api from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const semester = ref('')
const semesters = ref([])
const subjectAnalysis = ref([])
const homeworkLoading = ref(false)
const homeworkLearning = ref({ homework_trend: [], resubmit_lift: [] })

const trendChartRef = ref(null)
const homeworkTrendChartRef = ref(null)
const resubmitLiftChartRef = ref(null)

let trendChart = null
let homeworkTrendChart = null
let resubmitLiftChart = null

const selectedCourse = computed(() => userStore.selectedCourse)

const buildParams = () => ({
  semester: semester.value || undefined,
  subject_id: selectedCourse.value?.id
})

const truncateLabel = (s, maxLen = 10) => {
  if (!s) return ''
  return s.length <= maxLen ? s : `${s.slice(0, maxLen)}…`
}

const loadSemesters = async () => {
  semesters.value = await api.semesters.list()
}

const loadData = async () => {
  if (!selectedCourse.value) {
    subjectAnalysis.value = []
    homeworkLearning.value = { homework_trend: [], resubmit_lift: [] }
    updateTrendChart({})
    updateHomeworkCharts()
    return
  }
  homeworkLoading.value = true
  try {
    const [trends, analysis, hwLearning] = await Promise.all([
      api.dashboard.getTrends(buildParams()),
      api.dashboard.getSubjectAnalysis(buildParams()),
      api.dashboard.getHomeworkLearning(buildParams())
    ])
    subjectAnalysis.value = analysis || []
    homeworkLearning.value = hwLearning || { homework_trend: [], resubmit_lift: [] }
    updateTrendChart(trends || {})
    await nextTick()
    updateHomeworkCharts()
  } finally {
    homeworkLoading.value = false
  }
}

const updateTrendChart = data => {
  if (!trendChart) return
  const examTypes = Object.keys(data)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: examTypes
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: examTypes.map(key => data[key]?.avg || 0),
        areaStyle: {
          color: 'rgba(37, 99, 235, 0.12)'
        },
        lineStyle: {
          color: '#2563eb',
          width: 3
        },
        itemStyle: {
          color: '#2563eb'
        }
      }
    ]
  })
}

const updateHomeworkCharts = () => {
  const trend = homeworkLearning.value?.homework_trend || []
  const lift = homeworkLearning.value?.resubmit_lift || []

  if (homeworkTrendChart) {
    const titles = trend.map(row => truncateLabel(row.title))
    const fullTitles = trend.map(row => row.title)
    homeworkTrendChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter(params) {
          const p = params[0]
          const i = p?.dataIndex
          const full = fullTitles[i] || p?.name
          return `${full}<br/>均分：${p?.value ?? '-'}<br/>已批改：${trend[i]?.scored_count ?? 0} / 提交：${trend[i]?.submission_count ?? 0}`
        }
      },
      grid: { left: 48, right: 24, bottom: 72, top: 32 },
      xAxis: {
        type: 'category',
        data: titles,
        axisLabel: { rotate: 28, interval: 0, color: '#64748b' }
      },
      yAxis: { type: 'value', min: 0, max: 100, name: '分' },
      series: [
        {
          type: 'bar',
          data: trend.map(row => (row.scored_count > 0 ? row.avg_score : null)),
          itemStyle: { color: '#0d9488', borderRadius: [4, 4, 0, 0] },
          name: '班级均分'
        }
      ]
    })
  }

  if (resubmitLiftChart) {
    const labels = lift.map(row => truncateLabel(row.title))
    const fullTitles = lift.map(row => row.title)
    resubmitLiftChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter(params) {
          const p = params[0]
          const i = p?.dataIndex
          const row = lift[i]
          if (!row) return ''
          return `${fullTitles[i] || ''}<br/>学生数：${row.student_count}<br/>首次均分：${row.avg_first_score} → 末次均分：${row.avg_last_score}<br/>平均变化：${row.avg_lift > 0 ? '+' : ''}${row.avg_lift}`
        }
      },
      grid: { left: 48, right: 24, bottom: 72, top: 32 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { rotate: 28, interval: 0, color: '#64748b' }
      },
      yAxis: { type: 'value', name: '分差' },
      series: [
        {
          type: 'bar',
          data: lift.map(row => row.avg_lift),
          itemStyle: {
            color: params => (params.value >= 0 ? '#16a34a' : '#dc2626'),
            borderRadius: [4, 4, 0, 0]
          },
          name: '末次−首次'
        }
      ]
    })
  }
}

const initCharts = () => {
  if (trendChartRef.value && !trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  if (homeworkTrendChartRef.value && !homeworkTrendChart) {
    homeworkTrendChart = echarts.init(homeworkTrendChartRef.value)
  }
  if (resubmitLiftChartRef.value && !resubmitLiftChart) {
    resubmitLiftChart = echarts.init(resubmitLiftChartRef.value)
  }
}

const resizeAll = () => {
  trendChart?.resize()
  homeworkTrendChart?.resize()
  resubmitLiftChart?.resize()
}

onMounted(async () => {
  await loadSemesters()
  await nextTick()
  if (selectedCourse.value) {
    initCharts()
    await loadData()
  }
  window.addEventListener('resize', resizeAll)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeAll)
  trendChart?.dispose()
  homeworkTrendChart?.dispose()
  resubmitLiftChart?.dispose()
  trendChart = null
  homeworkTrendChart = null
  resubmitLiftChart = null
})

watch(selectedCourse, async () => {
  await nextTick()
  initCharts()
  await loadData()
})
</script>

<style scoped>
.analysis-page {
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
}

.analysis-section {
  margin-bottom: 32px;
}

.section-title {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
}

.section-desc {
  margin: 0 0 16px;
  font-size: 14px;
  line-height: 1.5;
  color: #64748b;
}

.chart-box {
  height: 360px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
