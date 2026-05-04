<template>
  <el-container
    class="layout-container"
    :class="{
      'layout-container--mobile-sidebar-open': isMobile && !isCollapsed,
      'layout-container--sidebar-hidden': !isMobile && isSidebarHidden
    }"
  >
    <div v-if="isMobile && !isCollapsed" class="mobile-sidebar-backdrop" @click="isCollapsed = true" />
    <el-aside :width="sidebarWidth" class="sidebar" :class="{ 'sidebar--hidden': isSidebarHidden && !isMobile }">
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
          :aria-label="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
          @click="toggleSidebarCollapse"
        />
      </div>

      <div class="sidebar-body">
        <el-menu
          :default-active="route.path"
          :default-openeds="homeworkMenuOpenIndices"
          :collapse="isCollapsed"
          router
          class="sidebar-menu sidebar-menu--scroll"
        >
          <template v-for="item in menuItems" :key="item.type === 'submenu' ? item.index : item.path">
            <el-sub-menu v-if="item.type === 'submenu'" :index="item.index">
              <template #title>
                <el-icon><component :is="item.icon" /></el-icon>
                <span>{{ item.label }}</span>
              </template>
              <el-menu-item v-for="child in item.children" :key="child.path" :index="child.path">
                <el-icon><component :is="child.icon" /></el-icon>
                <template #title>{{ child.label }}</template>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="item.path">
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>{{ item.label }}</template>
            </el-menu-item>
          </template>
        </el-menu>

        <el-menu
          :default-active="route.path"
          :collapse="isCollapsed"
          router
          class="sidebar-menu sidebar-menu--footer"
        >
          <el-menu-item index="/personal-settings">
            <el-icon><Setting /></el-icon>
            <template #title>个人设置</template>
          </el-menu-item>
        </el-menu>
      </div>
    </el-aside>

    <button
      type="button"
      class="sidebar-edge-handle"
      :class="{
        'sidebar-edge-handle--hidden': !isMobile && isSidebarHidden,
        'sidebar-edge-handle--drawer-open': isMobile && !isCollapsed
      }"
      :style="sidebarHandleStyle"
      :aria-label="sidebarHandleLabel"
      :title="sidebarHandleLabel"
      data-testid="sidebar-edge-handle"
      @click="toggleSidebarDrawer"
    >
      <el-icon :size="18">
        <component :is="sidebarHandleIcon" />
      </el-icon>
    </button>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-button
            v-if="isMobile"
            class="mobile-menu-btn"
            :icon="isCollapsed ? Expand : Fold"
            circle
            size="small"
            aria-label="打开导航菜单"
            @click="toggleMobileSidebar"
          />
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: homePath }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="homeworkBreadcrumbParent" :to="{ path: '/homework' }">
              作业
            </el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentRouteName }}</el-breadcrumb-item>
          </el-breadcrumb>

          <div v-if="showClassContext" class="context-chip context-chip--class">
            <span class="context-chip__label">当前班级</span>
            <div class="context-chip__meta">
              <strong>{{ currentClassName }}</strong>
              <span>{{ classContextText }}</span>
            </div>
          </div>

          <div v-else-if="showCourseContext" class="context-chip">
            <span class="context-chip__label">当前课程</span>
            <div class="context-chip__meta">
              <strong>{{ selectedCourse?.name }}</strong>
              <span>{{ selectedCourse?.semester || '未设置学期' }}</span>
            </div>
            <el-tag size="small" type="primary">
              {{ selectedCourse?.course_type === 'elective' ? '选修课' : '必修课' }}
            </el-tag>
          </div>
        </div>

        <div class="header-right">
          <el-dropdown v-if="showCourseSwitcher" trigger="hover" data-testid="header-course-switch" @command="handleCourseSwitch">
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

          <el-dropdown data-testid="header-user-menu" @command="handleCommand">
            <div class="user-box">
              <el-avatar :size="34" :src="headerAvatarSrc || undefined">
                {{ userStore.userInfo?.real_name?.charAt(0) || 'U' }}
              </el-avatar>
              <div v-if="!isCollapsed" class="user-meta">
                <strong>{{ userStore.userInfo?.real_name }}</strong>
                <span>{{ roleText(userStore.userInfo?.role) }}</span>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="personal-settings">个人设置</el-dropdown-item>
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
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Bell,
  Collection,
  DataAnalysis,
  Expand,
  Fold,
  Reading,
  School,
  Setting,
  User,
  UserFilled
} from '@element-plus/icons-vue'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { fetchAttachmentBlobUrl } from '@/utils/attachments'
import { filterCoursesByClassId, resolveClassTeacherClassId, resolveClassTeacherClassName } from '@/utils/classTeacher'
import {
  emitNotificationRefresh,
  startNotificationPolling,
  subscribeNotificationBroadcast
} from '@/utils/notificationSync'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const adminHomePath = '/students'
const mobileBreakpoint = 768
const desktopSidebarStorageKey = 'wailearning-admin-sidebar-state'
const isCollapsed = ref(false)
const isSidebarHidden = ref(false)
const isMobile = ref(false)

const headerAvatarSrc = ref('')
let headerAvatarBlobUrl = ''

const revokeHeaderAvatarBlob = () => {
  if (headerAvatarBlobUrl) {
    URL.revokeObjectURL(headerAvatarBlobUrl)
    headerAvatarBlobUrl = ''
  }
  headerAvatarSrc.value = ''
}

const loadHeaderAvatar = async () => {
  revokeHeaderAvatarBlob()
  const url = userStore.userInfo?.avatar_url
  if (!url) {
    return
  }
  try {
    headerAvatarBlobUrl = await fetchAttachmentBlobUrl(url)
    headerAvatarSrc.value = headerAvatarBlobUrl
  } catch (error) {
    console.error('加载头像失败', error)
  }
}

const lastNotificationSyncSignature = ref(null)
let stopNotificationPolling = () => {}
let unsubscribeNotificationBroadcast = () => {}

const notificationSyncParams = computed(() => {
  if (userStore.isAdmin) {
    return null
  }

  if ((userStore.isTeacher || userStore.isStudent) && selectedCourse.value?.id) {
    return { subject_id: selectedCourse.value.id }
  }

  return {}
})

const pollNotificationSync = async () => {
  if (!userStore.isLoggedIn) {
    return
  }

  const params = notificationSyncParams.value || {}

  try {
    const status = await api.notifications.syncStatus(params)
    const signature = `${status.total}:${status.unread_count}:${status.latest_updated_at || ''}`
    if (lastNotificationSyncSignature.value !== null && signature !== lastNotificationSyncSignature.value) {
      emitNotificationRefresh()
    }
    lastNotificationSyncSignature.value = signature
  } catch (error) {
    console.error('通知同步检查失败', error)
  }
}

const selectedCourse = computed(() => userStore.selectedCourse)
const availableCourses = computed(() => userStore.teachingCourses || [])
const currentClassId = computed(() => resolveClassTeacherClassId(userStore.userInfo, availableCourses.value))
const classTeacherCourses = computed(() => filterCoursesByClassId(availableCourses.value, currentClassId.value))
const currentClassName = computed(() => resolveClassTeacherClassName(userStore.userInfo, availableCourses.value) || '未分配班级')

const homePath = computed(() => {
  if (userStore.isAdmin) {
    return adminHomePath
  }

  return userStore.isStudent ? '/courses' : '/dashboard'
})

const showClassContext = computed(() => userStore.isClassTeacher && Boolean(currentClassId.value))
const showCourseContext = computed(() => !userStore.isAdmin && !userStore.isClassTeacher && Boolean(selectedCourse.value))
const showCourseSwitcher = computed(() => !userStore.isAdmin && !userStore.isClassTeacher && availableCourses.value.length > 0)
const sidebarWidth = computed(() => {
  if (isMobile.value) {
    return isCollapsed.value ? '0px' : '240px'
  }
  if (isSidebarHidden.value) {
    return '0px'
  }
  return isCollapsed.value ? '72px' : '240px'
})
const sidebarHandleStyle = computed(() => {
  if (isMobile.value) {
    return { left: isCollapsed.value ? '0px' : '226px' }
  }

  return { left: isSidebarHidden.value ? '0px' : `calc(${sidebarWidth.value} - 14px)` }
})
const sidebarHandleLabel = computed(() => {
  if (isMobile.value) {
    return isCollapsed.value ? '打开导航菜单' : '关闭导航菜单'
  }

  return isSidebarHidden.value ? '拉出侧边栏' : '隐藏侧边栏'
})
const sidebarHandleIcon = computed(() => {
  if (isMobile.value) {
    return isCollapsed.value ? ArrowRight : ArrowLeft
  }

  return isSidebarHidden.value ? ArrowRight : ArrowLeft
})
const classContextText = computed(() => `班级课程 ${classTeacherCourses.value.length} 门`)

const routeNameMap = {
  '/courses': '我的课程',
  '/course-home': '课程主页',
  '/dashboard': '课程仪表盘',
  '/classes': '班级管理',
  '/students': '学生信息',
  '/scores': '成绩管理',
  '/student-scores': '我的成绩',
  '/attendance': '考勤管理',
  '/rankings': '班级排名',
  '/analysis': '数据分析',
  '/users': '用户管理',
  '/subjects': '课程信息',
  '/semesters': '学期管理',
  '/logs': '操作日志',
  '/points': '积分系统',
  '/points-display': '积分展示',
  '/settings': '系统设置',
  '/materials': '课程资料',
  '/homework': '作业管理',
  '/homework/students': '学生作业一览',
  '/homework/by-student': '学生作业一览',
  '/notifications': '消息与通知',
  '/personal-settings': '个人设置'
}

const currentRouteName = computed(() => route.meta?.title || routeNameMap[route.path] || '页面')

const homeworkBreadcrumbParent = computed(() => {
  const p = route.path
  return p === '/homework/students' || /^\/homework\/\d+\//.test(p)
})

const homeworkMenuOpenIndices = computed(() => {
  if (userStore.isStudent || userStore.isAdmin || userStore.isClassTeacher) {
    return []
  }
  if (route.path.startsWith('/homework')) {
    return ['homework-center']
  }
  return []
})

const classTeacherMenu = [
  { path: '/dashboard', label: '课程仪表盘', icon: DataAnalysis },
  { path: '/students', label: '学生信息', icon: User },
  { path: '/subjects', label: '课程信息', icon: Reading },
  { path: '/notifications', label: '通知信息', icon: Bell }
]

const teacherMenu = [
  { path: '/dashboard', label: '课程仪表盘', icon: DataAnalysis },
  { path: '/students', label: '学生管理', icon: User },
  { path: '/scores', label: '成绩管理', icon: Collection },
  { path: '/attendance', label: '考勤管理', icon: Collection },
  { path: '/materials', label: '课程资料', icon: Collection },
  {
    type: 'submenu',
    index: 'homework-center',
    label: '作业',
    icon: Reading,
    children: [
      { path: '/homework', label: '作业管理', icon: Reading },
      { path: '/homework/students', label: '学生作业一览', icon: User }
    ]
  },
  { path: '/notifications', label: '通知中心', icon: Bell }
]

const studentBaseMenu = [
  { path: '/courses', label: '我的课程', icon: Reading },
  { path: '/course-home', label: '课程主页', icon: School }
]

const studentMenu = [
  { path: '/materials', label: '课程资料', icon: Collection },
  { path: '/homework', label: '课程作业', icon: Reading },
  { path: '/student-scores', label: '我的成绩', icon: Collection },
  { path: '/notifications', label: '课程通知', icon: Bell }
]

const adminMenu = [
  { path: '/students', label: '学生管理', icon: User },
  { path: '/classes', label: '班级管理', icon: School },
  { path: '/users', label: '用户管理', icon: UserFilled },
  { path: '/subjects', label: '课程管理', icon: Reading },
  { path: '/semesters', label: '学期管理', icon: Collection },
  { path: '/notifications', label: '消息与通知', icon: Bell },
  { path: '/logs', label: '操作日志', icon: Collection },
  { path: '/settings', label: '系统设置', icon: Setting }
]

const menuItems = computed(() => {
  if (userStore.isStudent) {
    return selectedCourse.value ? [...studentBaseMenu, ...studentMenu] : [studentBaseMenu[0]]
  }

  if (userStore.isAdmin) {
    return adminMenu
  }

  if (userStore.isClassTeacher) {
    return classTeacherMenu
  }

  return teacherMenu
})

const roleText = role => ({
  admin: '管理员',
  class_teacher: '班主任',
  teacher: '任课老师',
  student: '学生'
}[role] || '未知角色')

const persistDesktopSidebarState = () => {
  if (typeof window === 'undefined' || isMobile.value) {
    return
  }

  const state = isSidebarHidden.value ? 'hidden' : isCollapsed.value ? 'collapsed' : 'expanded'
  window.localStorage.setItem(desktopSidebarStorageKey, state)
}

const restoreDesktopSidebarState = () => {
  if (typeof window === 'undefined') {
    return
  }

  const state = window.localStorage.getItem(desktopSidebarStorageKey)
  if (state === 'hidden') {
    isSidebarHidden.value = true
    isCollapsed.value = false
    return
  }
  if (state === 'collapsed') {
    isSidebarHidden.value = false
    isCollapsed.value = true
    return
  }
  isSidebarHidden.value = false
  isCollapsed.value = false
}

const toggleSidebarCollapse = () => {
  if (isSidebarHidden.value) {
    isSidebarHidden.value = false
    isCollapsed.value = false
    persistDesktopSidebarState()
    return
  }

  isCollapsed.value = !isCollapsed.value
  persistDesktopSidebarState()
}

const toggleMobileSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

const toggleSidebarDrawer = () => {
  if (isMobile.value) {
    toggleMobileSidebar()
    return
  }

  isSidebarHidden.value = !isSidebarHidden.value
  if (!isSidebarHidden.value) {
    isCollapsed.value = false
  }
  persistDesktopSidebarState()
}

const syncResponsiveSidebar = () => {
  if (typeof window === 'undefined') {
    return
  }

  const nextIsMobile = window.innerWidth <= mobileBreakpoint
  const changedMode = nextIsMobile !== isMobile.value
  isMobile.value = nextIsMobile
  if (isMobile.value) {
    isSidebarHidden.value = false
    isCollapsed.value = true
    return
  }

  if (changedMode) {
    restoreDesktopSidebarState()
  }
}

const syncTeacherCourses = async force => {
  if (!userStore.canSelectCourse) {
    return
  }

  try {
    await userStore.ensureSelectedCourse(force, {
      preserveEmptySelection: userStore.isStudent || userStore.isClassTeacher
    })
  } catch (error) {
    console.error('加载课程失败', error)
  }
}

const handleWindowFocus = () => {
  syncTeacherCourses(true)
  pollNotificationSync()
}

const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') {
    syncTeacherCourses(true)
    pollNotificationSync()
  }
}

const handleCourseSwitch = courseId => {
  const course = availableCourses.value.find(item => String(item.id) === String(courseId))
  if (!course) {
    return
  }

  userStore.setSelectedCourse(course)

  if (/^\/homework\/\d+\//.test(route.path)) {
    router.push('/homework')
    return
  }

  if (route.path === '/courses') {
    router.push(userStore.isStudent ? '/course-home' : '/dashboard')
  }
}

const handleCommand = command => {
  if (command === 'personal-settings') {
    router.push('/personal-settings')
    return
  }

  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}

onMounted(async () => {
  restoreDesktopSidebarState()
  syncResponsiveSidebar()
  window.addEventListener('resize', syncResponsiveSidebar)
  window.addEventListener('focus', handleWindowFocus)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  await loadHeaderAvatar()
  await syncTeacherCourses(true)
  await pollNotificationSync()
  stopNotificationPolling = startNotificationPolling(pollNotificationSync)
  unsubscribeNotificationBroadcast = subscribeNotificationBroadcast(() => {
    emitNotificationRefresh()
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncResponsiveSidebar)
  window.removeEventListener('focus', handleWindowFocus)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  stopNotificationPolling()
  unsubscribeNotificationBroadcast()
  revokeHeaderAvatarBlob()
})

watch(
  () => userStore.userInfo?.id,
  async () => {
    lastNotificationSyncSignature.value = null
    await syncTeacherCourses(true)
    await pollNotificationSync()
    await loadHeaderAvatar()
  }
)

watch(
  () => userStore.userInfo?.avatar_url,
  () => {
    loadHeaderAvatar()
  }
)

watch(
  () => route.fullPath,
  async () => {
    if (isMobile.value) {
      isCollapsed.value = true
    }
    await syncTeacherCourses(true)
    await pollNotificationSync()
  }
)

watch(notificationSyncParams, () => {
  lastNotificationSyncSignature.value = null
  pollNotificationSync()
})
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
  background: var(--wa-color-bg);
}

.layout-container > .el-container {
  min-width: 0;
}

.sidebar {
  display: flex;
  flex-direction: column;
  background: var(--wa-sidebar-bg);
  color: #fff;
  transition: width 0.2s ease, transform 0.2s ease;
}

.sidebar--hidden {
  overflow: hidden;
}

.sidebar-edge-handle {
  position: fixed;
  top: 50%;
  z-index: 1000;
  display: inline-flex;
  width: 28px;
  height: 58px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-left: none;
  border-radius: 0 var(--wa-radius-xl) var(--wa-radius-xl) 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), color-mix(in srgb, var(--wa-color-primary-50) 94%, white));
  color: var(--wa-color-primary-600);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.16);
  cursor: pointer;
  transform: translateY(-50%);
  transition: left 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.sidebar-edge-handle:hover,
.sidebar-edge-handle:focus-visible {
  transform: translateY(-50%) translateX(2px);
  background: #ffffff;
  box-shadow: 0 14px 32px color-mix(in srgb, var(--wa-color-primary-600) 22%, transparent);
  outline: none;
}

.sidebar-edge-handle--hidden {
  color: var(--wa-color-accent-700);
}

.sidebar-edge-handle--drawer-open {
  color: var(--wa-color-text);
  background: rgba(255, 255, 255, 0.94);
}

.mobile-sidebar-backdrop {
  position: fixed;
  inset: 0;
  z-index: 998;
  background: rgba(15, 23, 42, 0.36);
}

.sidebar-body {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
}

.sidebar-menu--scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-menu--footer {
  flex-shrink: 0;
  margin-top: auto;
  padding-top: 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
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
  display: flex;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border-radius: var(--wa-radius-lg);
  background: color-mix(in srgb, var(--wa-color-primary-500) 22%, transparent);
  color: var(--wa-color-primary-300);
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
  border-color: rgba(255, 255, 255, 0.2);
  background: transparent;
  color: #fff;
}

.sidebar-menu {
  border-right: none;
  background: transparent;
  padding: 12px 8px;
}

.sidebar-menu :deep(.el-menu-item) {
  margin: 6px 0;
  border-radius: var(--wa-radius-lg);
  color: rgba(255, 255, 255, 0.82);
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--wa-sidebar-active-bg);
  color: #fff;
}

.sidebar-menu :deep(.el-sub-menu__title) {
  margin: 6px 0;
  border-radius: var(--wa-radius-lg);
  color: rgba(255, 255, 255, 0.82);
}

.sidebar-menu :deep(.el-sub-menu__title:hover) {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item) {
  margin: 4px 0;
  padding-left: 48px !important;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--wa-border-subtle);
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(10px);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 18px;
  min-width: 0;
}

.context-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 100%;
  border-radius: 999px;
  background: var(--wa-color-primary-50);
  padding: 8px 14px;
  color: var(--wa-color-primary-700);
}

.context-chip--class {
  background: var(--wa-color-accent-50);
  color: var(--wa-color-accent-700);
}

.context-chip__label {
  color: var(--wa-color-text-muted);
}

.context-chip__meta {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.context-chip__meta strong,
.context-chip__meta span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.context-chip__meta span {
  font-size: 12px;
  color: var(--wa-color-text-muted);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.course-option {
  display: flex;
  min-width: 200px;
  flex-direction: column;
  gap: 4px;
}

.course-option span {
  font-size: 12px;
  color: var(--wa-color-text-muted);
}

.course-dropdown-menu :deep(.is-current-course) {
  background: var(--wa-color-primary-50);
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
  color: var(--wa-color-text);
}

.user-meta span {
  font-size: 12px;
  color: var(--wa-color-text-muted);
}

.main-content {
  min-width: 0;
  padding: 0;
}

.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--wa-color-text-muted);
}

@media (max-width: 768px) {
  .layout-container {
    position: relative;
  }

  .sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 999;
    overflow: hidden;
    box-shadow: 18px 0 40px rgba(15, 23, 42, 0.2);
  }

  .sidebar[style*="0px"] {
    transform: translateX(-100%);
  }

  .sidebar-edge-handle {
    width: 30px;
    height: 54px;
  }

  .layout-container--mobile-sidebar-open {
    overflow: hidden;
  }

  .logo {
    padding: 14px 12px;
  }

  .header {
    height: auto;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding: 12px;
  }

  .header-left {
    width: 100%;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 10px;
  }

  .mobile-menu-btn {
    flex: 0 0 auto;
  }

  .header-left :deep(.el-breadcrumb) {
    min-width: 0;
    max-width: calc(100% - 44px);
  }

  .context-chip {
    width: 100%;
    border-radius: 18px;
    align-items: flex-start;
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .user-meta {
    display: none;
  }
}
</style>
