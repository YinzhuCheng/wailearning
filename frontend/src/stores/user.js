import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import api, { http } from '@/api'
import { normalizeSystemSettings } from '@/utils/branding'

const cachedSystemSettings = normalizeSystemSettings(
  JSON.parse(localStorage.getItem('system_settings') || 'null')
)

if (cachedSystemSettings) {
  localStorage.setItem('system_settings', JSON.stringify(cachedSystemSettings))
}

const cachedSelectedCourse = JSON.parse(localStorage.getItem('selected_course') || 'null')

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const systemSettings = ref(cachedSystemSettings)
  const selectedCourse = ref(cachedSelectedCourse)
  const teachingCourses = ref([])
  const teachingCoursesLoaded = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 'admin')
  const isClassTeacher = computed(() => userInfo.value?.role === 'class_teacher')
  const isTeacher = computed(() => userInfo.value?.role === 'teacher')
  const isStudent = computed(() => userInfo.value?.role === 'student')
  const classId = computed(() => userInfo.value?.class_id)
  const canManageTeaching = computed(() => ['admin', 'class_teacher', 'teacher'].includes(userInfo.value?.role))
  const canSelectCourse = computed(() => ['class_teacher', 'teacher', 'student'].includes(userInfo.value?.role))

  function setSelectedCourse(course) {
    const normalizedCourse = course
      ? teachingCourses.value.find(item => String(item.id) === String(course.id)) || course
      : null

    selectedCourse.value = normalizedCourse
    if (normalizedCourse) {
      localStorage.setItem('selected_course', JSON.stringify(normalizedCourse))
    } else {
      localStorage.removeItem('selected_course')
    }
  }

  function clearSelectedCourse() {
    setSelectedCourse(null)
  }

  function rankTeachingCourses(courses) {
    return [...courses].sort((left, right) => {
      const leftActive = left.status !== 'completed'
      const rightActive = right.status !== 'completed'

      if (leftActive !== rightActive) {
        return leftActive ? -1 : 1
      }

      const semesterCompare = `${right.semester || ''}`.localeCompare(`${left.semester || ''}`, 'zh-CN', {
        numeric: true,
        sensitivity: 'base'
      })

      if (semesterCompare !== 0) {
        return semesterCompare
      }

      return Number(right.id || 0) - Number(left.id || 0)
    })
  }

  function resolvePreferredCourse(courses) {
    if (!courses.length) {
      return null
    }

    const cachedCourse = selectedCourse.value
      ? courses.find(item => String(item.id) === String(selectedCourse.value.id))
      : null

    if (cachedCourse) {
      return cachedCourse
    }

    return courses[0]
  }

  async function fetchTeachingCourses(force = false) {
    if (!canSelectCourse.value || isAdmin.value) {
      teachingCourses.value = []
      teachingCoursesLoaded.value = true
      return []
    }

    if (teachingCoursesLoaded.value && !force) {
      return teachingCourses.value
    }

    const data = await api.courses.list()
    teachingCourses.value = rankTeachingCourses(Array.isArray(data) ? data : [])
    teachingCoursesLoaded.value = true

    return teachingCourses.value
  }

  async function ensureSelectedCourse(force = false) {
    const courses = await fetchTeachingCourses(force)
    const preferredCourse = resolvePreferredCourse(courses)

    if (preferredCourse) {
      setSelectedCourse(preferredCourse)
    } else {
      clearSelectedCourse()
    }

    return preferredCourse
  }

  async function login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const data = await api.auth.login(formData)
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)

    const userData = await api.auth.getCurrentUser()
    userInfo.value = userData
    localStorage.setItem('user', JSON.stringify(userData))

    await fetchSystemSettings()

    return userData
  }

  async function fetchSystemSettings() {
    try {
      const data = await http.get('/settings/public')
      const normalizedSettings = normalizeSystemSettings(data)
      systemSettings.value = normalizedSettings
      localStorage.setItem('system_settings', JSON.stringify(normalizedSettings))
      document.title = normalizedSettings?.system_name || 'BIMSA-CLASS 管理端'
    } catch (error) {
      console.error('Failed to fetch system settings', error)
    }
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    systemSettings.value = null
    selectedCourse.value = null
    teachingCourses.value = []
    teachingCoursesLoaded.value = false
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('system_settings')
    localStorage.removeItem('selected_course')
  }

  return {
    token,
    userInfo,
    systemSettings,
    selectedCourse,
    teachingCourses,
    teachingCoursesLoaded,
    isLoggedIn,
    isAdmin,
    isClassTeacher,
    isTeacher,
    isStudent,
    classId,
    canManageTeaching,
    canSelectCourse,
    login,
    logout,
    fetchSystemSettings,
    setSelectedCourse,
    clearSelectedCourse,
    fetchTeachingCourses,
    ensureSelectedCourse
  }
})
