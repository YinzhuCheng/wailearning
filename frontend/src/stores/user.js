import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { http } from '@/api'
import { normalizeSystemSettings } from '@/utils/branding'

const cachedSystemSettings = normalizeSystemSettings(
  JSON.parse(localStorage.getItem('system_settings') || 'null')
)

if (cachedSystemSettings) {
  localStorage.setItem('system_settings', JSON.stringify(cachedSystemSettings))
}

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const systemSettings = ref(cachedSystemSettings)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 'admin')
  const isClassTeacher = computed(() => userInfo.value?.role === 'class_teacher')
  const isTeacher = computed(() => userInfo.value?.role === 'teacher')
  const classId = computed(() => userInfo.value?.class_id)

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
    } catch (e) {
      console.error('Failed to fetch system settings', e)
    }
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    systemSettings.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('system_settings')
  }

  return {
    token,
    userInfo,
    systemSettings,
    isLoggedIn,
    isAdmin,
    isClassTeacher,
    isTeacher,
    classId,
    login,
    logout,
    fetchSystemSettings
  }
})
