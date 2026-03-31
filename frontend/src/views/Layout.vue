<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapsed ? '72px' : '240px'" class="sidebar">
      <div class="logo">
        <div class="logo-main">
          <div class="logo-icon">
            <el-icon :size="22"><School /></el-icon>
          </div>
          <div v-if="!isCollapsed" class="logo-texts">
            <h2>{{ userStore.systemSettings?.system_name || 'BIMSA-CLASS' }}</h2>
            <p>大学教学管理系统</p>
          </div>
        </div>
        <el-button
          class="collapse-btn"
          :icon="isCollapsed ? Expand : Fold"
          circle
          size="small"
          @click="isCollapsed = !isCollapsed"
        />
      </div>

      <el-menu
        :default-active="route.path"
        :collapse="isCollapsed"
        router
        class="sidebar-menu"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.label }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: homePath }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentRouteName }}</el-breadcrumb-item>
          </el-breadcrumb>
          <div v-if="showCourseContext" class="course-chip">
            <span class="course-chip-label">当前课程</span>
            <div class="course-chip-meta">
              <strong>{{ selectedCourse?.name }}</strong>
              <span>{{ selectedCourse?.semester || '未设置学期' }}</span>
            </div>
            <el-tag size="small" type="primary">
              {{ selectedCourse?.course_type === 'elective' ? '选修课' : '必修课' }}
            </el-tag>
          </div>
        </div>

        <div class="header-right">
          <el-dropdown v-if="showCourseSwitcher" trigger="click" @command="handleCourseSwitch">
            <el-button text>
              切换课程
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu class="course-dropdown-menu">
                <el-dropdown-item
                  v-for="course in availableCourses"
                  :key="course.id"
                  :command="course.id"
                  :class="{ 'is-current-course': selectedCourse?.id === course.id }"
                >
                  <div class="course-option">
                    <strong>{{ course.name }}</strong>
                    <span>{{ course.semester || '未设置学期' }}</span>
                  </div>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-dropdown @command="handleCommand">
            <div class="user-box">
              <el-avatar :size="34">{{ userStore.userInfo?.real_name?.charAt(0) || 'U' }}</el-avatar>
              <div v-if="!isCollapsed" class="user-meta">
                <strong>{{ userStore.userInfo?.real_name }}</strong>
                <span>{{ roleText(userStore.userInfo?.role) }}</span>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="change-password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>

      <el-footer class="footer">
        {{ userStore.systemSettings?.copyright || '(c) 2026 BIMSA-CLASS' }}
      </el-footer>

      <el-dialog
        v-model="passwordDialogVisible"
        title="修改密码"
        width="420px"
        destroy-on-close
      >
        <el-form label-position="top" @submit.prevent>
          <input
            :value="userStore.userInfo?.username || ''"
            type="text"
            name="username"
            autocomplete="username"
            readonly
            tabindex="-1"
            aria-hidden="true"
            style="position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; pointer-events: none;"
          />
          <el-form-item label="当前密码">
            <el-input
              v-model="passwordForm.current_password"
              type="password"
              show-password
              autocomplete="current-password"
            />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input
              v-model="passwordForm.new_password"
              type="password"
              show-password
              autocomplete="new-password"
            />
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input
              v-model="passwordForm.confirm_password"
              type="password"
              show-password
              autocomplete="new-password"
              @keyup.enter="submitChangePassword"
            />
          </el-form-item>
          <el-text type="info">新密码需要 8 到 72 个字符，保存后立即生效。</el-text>
        </el-form>
        <template #footer>
          <span>
            <el-button @click="closeChangePasswordDialog">取消</el-button>
            <el-button type="primary" :loading="passwordSubmitting" @click="submitChangePassword">
              保存密码
            </el-button>
          </span>
        </template>
      </el-dialog>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  Bell,
  Calendar,
  Coin,
  Collection,
  DataAnalysis,
  Expand,
  Fold,
  Reading,
  School,
  Setting,
  TrendCharts,
  User,
  UserFilled
} from '@element-plus/icons-vue'

import api from '@/api'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const adminHomePath = '/students'
const mobileBreakpoint = 768
const isCollapsed = ref(false)
const passwordDialogVisible = ref(false)
const passwordSubmitting = ref(false)
const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: ''
})

const selectedCourse = computed(() => userStore.selectedCourse)
const availableCourses = computed(() => userStore.teachingCourses || [])
const homePath = computed(() => {
  if (userStore.isAdmin) {
    return adminHomePath
  }

  return userStore.isStudent ? '/homework' : '/dashboard'
})
const showCourseContext = computed(() => !userStore.isAdmin && !!selectedCourse.value)
const showCourseSwitcher = computed(() => !userStore.isAdmin && availableCourses.value.length > 0)

const currentRouteName = computed(() => {
  if (route.meta?.title) {
    return route.meta.title
  }

  const routeMap = {
    '/courses': '我的课程',
    '/dashboard': '课程仪表盘',
    '/classes': '班级管理',
    '/students': '学生管理',
    '/scores': '成绩管理',
    '/attendance': '考勤管理',
    '/rankings': '班级排名',
    '/analysis': '数据分析',
    '/users': '用户管理',
    '/subjects': '课程管理',
    '/semesters': '学期管理',
    '/logs': '操作日志',
    '/points': '积分系统',
    '/points-display': '积分展示',
    '/settings': '系统设置',
    '/materials': '课程资料',
    '/homework': '作业管理',
    '/notifications': '通知中心'
  }
  return routeMap[route.path] || '页面'
})

const studentBaseMenu = [
  { path: '/courses', label: '我的课程', icon: Reading }
]

const teacherMenu = [
  { path: '/dashboard', label: '课程仪表盘', icon: DataAnalysis },
  { path: '/students', label: '学生管理', icon: User },
  { path: '/scores', label: '成绩管理', icon: Collection },
  { path: '/attendance', label: '考勤管理', icon: Calendar },
  { path: '/rankings', label: '班级排名', icon: TrendCharts },
  { path: '/analysis', label: '数据分析', icon: DataAnalysis },
  { path: '/points', label: '积分系统', icon: Coin },
  { path: '/materials', label: '课程资料', icon: Collection },
  { path: '/homework', label: '作业管理', icon: Reading },
  { path: '/notifications', label: '通知中心', icon: Bell }
]

const studentMenu = [
  { path: '/materials', label: '课程资料', icon: Collection },
  { path: '/homework', label: '作业', icon: Reading },
  { path: '/notifications', label: '通知', icon: Bell }
]

const adminMenu = [
  { path: '/students', label: '学生管理', icon: User },
  { path: '/classes', label: '班级管理', icon: School },
  { path: '/users', label: '用户管理', icon: UserFilled },
  { path: '/subjects', label: '课程管理', icon: Reading },
  { path: '/semesters', label: '学期管理', icon: Collection },
  { path: '/logs', label: '操作日志', icon: Collection },
  { path: '/settings', label: '系统设置', icon: Setting }
]

const menuItems = computed(() => {
  if (userStore.isStudent) {
    return [...studentBaseMenu, ...studentMenu]
  }
  if (userStore.isAdmin) {
    return adminMenu
  }
  return teacherMenu
})

const roleText = role => {
  const map = {
    admin: '管理员',
    class_teacher: '班主任',
    teacher: '任课老师',
    student: '学生'
  }
  return map[role] || '未知角色'
}

const resetPasswordForm = () => {
  passwordForm.current_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
}

const openChangePasswordDialog = () => {
  resetPasswordForm()
  passwordDialogVisible.value = true
}

const closeChangePasswordDialog = () => {
  passwordDialogVisible.value = false
  resetPasswordForm()
}

const submitChangePassword = async () => {
  if (!passwordForm.current_password || !passwordForm.new_password || !passwordForm.confirm_password) {
    ElMessage.warning('请填写完整的密码信息')
    return
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }

  passwordSubmitting.value = true
  try {
    const result = await api.auth.changePassword({ ...passwordForm })
    ElMessage.success(result?.message || '密码修改成功')
    closeChangePasswordDialog()
  } finally {
    passwordSubmitting.value = false
  }
}

const syncResponsiveSidebar = () => {
  if (typeof window !== 'undefined' && window.innerWidth <= mobileBreakpoint) {
    isCollapsed.value = true
  }
}

const syncTeacherCourses = async force => {
  if (!userStore.canSelectCourse) {
    return
  }

  try {
    await userStore.ensureSelectedCourse(force)
  } catch (error) {
    console.error('加载教师课程失败', error)
  }
}

const handleCourseSwitch = courseId => {
  const course = availableCourses.value.find(item => String(item.id) === String(courseId))
  if (!course) {
    return
  }

  userStore.setSelectedCourse(course)

  if (route.path.startsWith('/homework/')) {
    router.push('/homework')
    return
  }

  if (route.path === '/courses') {
    router.push(userStore.isStudent ? '/homework' : '/dashboard')
  }
}

const handleCommand = command => {
  if (command === 'change-password') {
    openChangePasswordDialog()
    return
  }
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}

onMounted(() => {
  syncResponsiveSidebar()
  window.addEventListener('resize', syncResponsiveSidebar)
  syncTeacherCourses(false)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncResponsiveSidebar)
})

watch(
  () => userStore.userInfo?.id,
  () => {
    syncTeacherCourses(true)
  }
)
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
  background: #f4f7fb;
}

.sidebar {
  background: linear-gradient(180deg, #0f172a 0%, #132238 100%);
  color: #fff;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #93c5fd;
}

.logo-texts h2 {
  margin: 0;
  font-size: 18px;
  color: #fff;
}

.logo-texts p {
  margin: 4px 0 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
}

.collapse-btn {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.sidebar-menu {
  border-right: none;
  background: transparent;
  padding: 12px 8px;
}

.sidebar-menu :deep(.el-menu-item) {
  margin: 6px 0;
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.82);
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
  color: #fff;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid #e2e8f0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 18px;
}

.course-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
}

.course-chip-label {
  color: #64748b;
}

.course-chip-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.course-chip-meta span {
  font-size: 12px;
  color: #64748b;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.course-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 200px;
}

.course-option span {
  font-size: 12px;
  color: #64748b;
}

.course-dropdown-menu :deep(.is-current-course) {
  background: #eff6ff;
}

.user-box {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-meta strong {
  color: #111827;
}

.user-meta span {
  font-size: 12px;
  color: #64748b;
}

.main-content {
  padding: 0;
}

.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 768px) {
  .header {
    height: auto;
    padding: 12px;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-left {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
