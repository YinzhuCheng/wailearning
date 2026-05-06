<template>
  <div class="teaching-calendar-page" v-loading="pageLoading">
    <div class="page-header">
      <h1 class="page-title">教学日历</h1>
      <p class="page-subtitle">{{ subtitle }}</p>
    </div>

    <template v-if="userStore.isClassTeacher">
      <el-empty v-if="!currentClassId" description="当前账号还没有绑定班级。" />
      <el-card v-else shadow="never" class="calendar-panel">
        <ClassSemesterCalendar :class-name="currentClassName" :courses="currentClassCourses" />
      </el-card>
    </template>

    <template v-else>
      <el-empty v-if="!selectedCourse" description="请先选择一门课程。" />
      <el-card v-else shadow="never" class="calendar-panel">
        <TeachingCalendar :course="selectedCourse" />
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import ClassSemesterCalendar from '@/components/ClassSemesterCalendar.vue'
import TeachingCalendar from '@/components/TeachingCalendar.vue'
import { useUserStore } from '@/stores/user'
import {
  filterCoursesByClassId,
  resolveClassTeacherClassId,
  resolveClassTeacherClassName
} from '@/utils/classTeacher'
import { onNotificationRefresh } from '@/utils/notificationSync'

const userStore = useUserStore()

const pageLoading = ref(false)
const classTeacherCoursePool = ref([])

const selectedCourse = computed(() => userStore.selectedCourse)
const currentClassId = computed(() => resolveClassTeacherClassId(userStore.userInfo, classTeacherCoursePool.value))
const currentClassName = computed(
  () => resolveClassTeacherClassName(userStore.userInfo, classTeacherCoursePool.value) || '未分配班级'
)
const currentClassCourses = computed(() => filterCoursesByClassId(classTeacherCoursePool.value, currentClassId.value))

const subtitle = computed(() => {
  if (userStore.isClassTeacher) {
    return currentClassId.value ? `当前班级：${currentClassName.value}` : '请先为班主任账号分配班级。'
  }
  if (selectedCourse.value) {
    return `${selectedCourse.value.name} · ${selectedCourse.value.class_name || '未分班级'}`
  }
  return '请先选择一门课程。'
})

const loadClassTeacherPool = async () => {
  pageLoading.value = true
  try {
    classTeacherCoursePool.value = await userStore.fetchTeachingCourses(true)
  } finally {
    pageLoading.value = false
  }
}

let unsubscribeNotificationRefresh = () => {}

onMounted(async () => {
  unsubscribeNotificationRefresh = onNotificationRefresh(async () => {
    if (userStore.isClassTeacher) {
      await loadClassTeacherPool()
    }
  })
  if (userStore.isClassTeacher) {
    await loadClassTeacherPool()
  }
})

watch(
  () => userStore.userInfo?.id,
  async () => {
    if (userStore.isClassTeacher) {
      await loadClassTeacherPool()
    }
  }
)

onBeforeUnmount(() => {
  unsubscribeNotificationRefresh()
})
</script>

<style scoped>
.teaching-calendar-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  margin: 0 0 8px;
  font-size: 22px;
  color: #0f172a;
}

.page-subtitle {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.calendar-panel {
  border-radius: var(--wa-radius-lg);
}
</style>
