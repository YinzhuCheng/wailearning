import { createRouter, createWebHistory } from 'vue-router'

import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'courses',
        name: 'Courses',
        component: () => import('@/views/MyCourses.vue')
      },
      {
        path: 'course-home',
        name: 'StudentCourseHome',
        component: () => import('@/views/StudentCourseHome.vue')
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue')
      },
      {
        path: 'classes',
        name: 'Classes',
        component: () => import('@/views/Classes.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'students',
        name: 'Students',
        component: () => import('@/views/Students.vue')
      },
      {
        path: 'students/new',
        name: 'StudentCreate',
        component: () => import('@/views/StudentForm.vue'),
        meta: { requiresTeachingRoster: true, title: '新增学生' }
      },
      {
        path: 'students/:id/edit',
        name: 'StudentEdit',
        component: () => import('@/views/StudentForm.vue'),
        meta: { requiresTeachingRoster: true, title: '编辑学生' }
      },
      {
        path: 'scores',
        name: 'Scores',
        component: () => import('@/views/Scores.vue')
      },
      {
        path: 'attendance',
        name: 'Attendance',
        component: () => import('@/views/Attendance.vue')
      },
      {
        path: 'rankings',
        name: 'Rankings',
        component: () => import('@/views/Rankings.vue')
      },
      {
        path: 'analysis',
        name: 'Analysis',
        component: () => import('@/views/Analysis.vue')
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/Users.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'subjects',
        name: 'Subjects',
        component: () => import('@/views/Subjects.vue')
      },
      {
        path: 'semesters',
        name: 'Semesters',
        component: () => import('@/views/Semesters.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/Logs.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'points',
        name: 'Points',
        component: () => import('@/views/Points.vue')
      },
      {
        path: 'points-display',
        name: 'PointsDisplay',
        component: () => import('@/views/PointsDisplay.vue')
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'homework',
        name: 'Homework',
        component: () => import('@/views/Homework.vue')
      },
      {
        path: 'homework/:id/submit',
        name: 'HomeworkSubmit',
        component: () => import('@/views/HomeworkSubmission.vue'),
        meta: { title: '提交作业' }
      },
      {
        path: 'homework/:id/submissions',
        name: 'HomeworkSubmissions',
        component: () => import('@/views/HomeworkSubmissions.vue'),
        meta: { title: '学生提交', requiresTeacher: true }
      },
      {
        path: 'materials',
        name: 'Materials',
        component: () => import('@/views/Materials.vue')
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/Notifications.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

const adminHomePath = '/students'
const adminHiddenPaths = ['/courses', '/dashboard', '/scores', '/attendance', '/rankings', '/analysis', '/points', '/materials', '/homework', '/notifications']

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  if (to.path !== '/login' && !userStore.isLoggedIn) {
    next('/login')
    return
  }

  if (to.path === '/login' && userStore.isLoggedIn) {
    next(userStore.isAdmin ? adminHomePath : userStore.isStudent ? '/courses' : '/dashboard')
    return
  }

  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    next(userStore.isStudent ? '/courses' : '/dashboard')
    return
  }

  if (to.meta.requiresTeachingRoster && !userStore.canManageTeaching) {
    next(userStore.isStudent ? '/courses' : '/dashboard')
    return
  }

  if (to.meta.requiresTeacher && (userStore.isStudent || userStore.isAdmin)) {
    next(userStore.isStudent ? '/homework' : adminHomePath)
    return
  }

  if (userStore.isAdmin && adminHiddenPaths.includes(to.path)) {
    next(adminHomePath)
    return
  }

  if (userStore.isStudent && ['/dashboard', '/students', '/scores', '/attendance', '/rankings', '/analysis', '/points'].includes(to.path)) {
    next('/courses')
    return
  }

  if (!userStore.isAdmin && to.path !== '/login') {
    try {
      await userStore.ensureSelectedCourse(false, {
        preserveEmptySelection: userStore.isStudent
      })
    } catch (error) {
      console.error('Failed to preload teaching courses', error)
    }
  }

  if (userStore.isStudent && to.path !== '/courses' && !userStore.selectedCourse) {
    next('/courses')
    return
  }

  next()
})

export default router
