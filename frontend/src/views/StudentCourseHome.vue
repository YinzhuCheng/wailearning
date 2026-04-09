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
        <article class="overview-card">
          <span class="overview-label">每周时间</span>
          <strong>{{ formatScheduleDisplay(selectedCourse.weekly_schedule) || '未设置' }}</strong>
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
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { formatScheduleValue } from '@/utils/courseSchedule'

const router = useRouter()
const userStore = useUserStore()

const selectedCourse = computed(() => userStore.selectedCourse)
const loading = ref(false)
const materials = ref([])
const homeworks = ref([])
const notifications = ref([])
const formatScheduleDisplay = value => formatScheduleValue(value) || value || ''

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

.overview-label {
  font-size: 13px;
  color: #64748b;
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
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  padding: 14px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #f8fafc;
  text-align: left;
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}

.item-card:hover {
  transform: translateY(-1px);
  border-color: #bfdbfe;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.08);
}

.item-card strong {
  color: #0f172a;
}

.item-card span {
  font-size: 13px;
  color: #64748b;
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
</style>
