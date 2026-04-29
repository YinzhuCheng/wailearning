import axios from 'axios'
import { ElMessage } from 'element-plus'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api'

const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10000
})
const fileTransferRequestConfig = {
  timeout: 0
}

/** FastAPI/Pydantic 422: { detail: [{ loc, msg, type }, ...] } — must stringify for ElMessage. */
const formatValidationDetail = detail => {
  if (!Array.isArray(detail) || !detail.length) {
    return null
  }
  const parts = detail
    .map(item => {
      if (typeof item === 'string') {
        return item
      }
      if (item && typeof item === 'object') {
        if (typeof item.msg === 'string') {
          return item.msg
        }
        if (typeof item.message === 'string') {
          return item.message
        }
      }
      return null
    })
    .filter(Boolean)
  return parts.length ? parts.join('；') : null
}

const extractErrorMessage = async error => {
  const data = error?.response?.data

  if (data instanceof Blob) {
    try {
      const text = await data.text()
      if (text) {
        try {
          const parsed = JSON.parse(text)
          const d = parsed?.detail
          if (Array.isArray(d)) {
            return formatValidationDetail(d) || parsed?.message || text
          }
          if (typeof d === 'string') {
            return d
          }
          return parsed?.message || text
        } catch {
          return text
        }
      }
    } catch {
      return 'Request failed'
    }
  }

  if (typeof data === 'string' && data.trim()) {
    return data
  }

  const detail = data?.detail
  if (Array.isArray(detail)) {
    return formatValidationDetail(detail) || data?.message || 'Request failed'
  }
  if (detail != null && typeof detail === 'object') {
    if (typeof detail.msg === 'string') {
      return detail.msg
    }
    if (typeof detail.message === 'string') {
      return detail.message
    }
  }
  if (typeof detail === 'string') {
    return detail
  }

  return data?.message || 'Request failed'
}

http.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

http.interceptors.response.use(
  response => (response.config?.returnFullResponse ? response : response.data),
  async error => {
    if (error.response) {
      const message = await extractErrorMessage(error)
      ElMessage.error(message)
      if (error.response.status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        localStorage.removeItem('selected_course')
        window.location.href = '/login'
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('Request timed out')
    } else {
      ElMessage.error('Network error')
    }
    return Promise.reject(error)
  }
)

/** Same as `http` but no global ElMessage on error (caller handles toasts) and unbounded timeout for long LLM calls. */
const httpQuiet = axios.create({
  baseURL: apiBaseUrl,
  timeout: 0
})
httpQuiet.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)
httpQuiet.interceptors.response.use(
  response => (response.config?.returnFullResponse ? response : response.data),
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      localStorage.removeItem('selected_course')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export { http, httpQuiet, apiBaseUrl }

const subjectsApi = {
  list: params => http.get('/subjects', { params }),
  electiveCatalog: () => http.get('/subjects/elective-catalog'),
  studentSelfEnroll: subjectId => http.post(`/subjects/${subjectId}/student-self-enroll`),
  studentSelfDrop: subjectId => http.post(`/subjects/${subjectId}/student-self-drop`),
  get: id => http.get(`/subjects/${id}`),
  create: data => http.post('/subjects', data),
  update: (id, data) => http.put(`/subjects/${id}`, data),
  delete: id => http.delete(`/subjects/${id}`),
  getStudents: id => http.get(`/subjects/${id}/students`),
  syncEnrollments: id => http.post(`/subjects/${id}/sync-enrollments`),
  rosterEnroll: (subjectId, data) => http.post(`/subjects/${subjectId}/roster-enroll`, data),
  removeStudent: (subjectId, studentId) => http.delete(`/subjects/${subjectId}/students/${studentId}`),
  updateEnrollmentType: (subjectId, studentId, data) => http.put(`/subjects/${subjectId}/students/${studentId}/enrollment-type`, data)
}

const api = {
  auth: {
    login: data => http.post('/auth/login', data),
    register: data => http.post('/auth/register', data),
    getCurrentUser: () => http.get('/auth/me'),
    changePassword: data => http.post('/auth/change-password', data)
  },
  users: {
    list: params => http.get('/users', { params }),
    listStudentCandidates: () => http.get('/users/student-candidates'),
    loadStudentCandidates: data => http.post('/users/student-candidates/load', data),
    batchSetClass: data => http.post('/users/batch-set-class', data),
    upsertStudentRosterFromUsers: data => http.post('/users/student-roster/from-users', data),
    get: id => http.get(`/users/${id}`),
    create: data => http.post('/users', data),
    update: (id, data) => http.put(`/users/${id}`, data),
    delete: id => http.delete(`/users/${id}`)
  },
  classes: {
    list: () => http.get('/classes'),
    get: id => http.get(`/classes/${id}`),
    create: data => http.post('/classes', data),
    update: (id, data) => http.put(`/classes/${id}`, data),
    delete: id => http.delete(`/classes/${id}`)
  },
  students: {
    list: params => http.get('/students', { params }),
    get: id => http.get(`/students/${id}`),
    create: data => http.post('/students', data),
    update: (id, data) => http.put(`/students/${id}`, data),
    delete: id => http.delete(`/students/${id}`),
    batchCreate: data =>
      http.post('/students/batch', JSON.stringify(data), {
        headers: { 'Content-Type': 'application/json' }
      })
  },
  subjects: subjectsApi,
  courses: subjectsApi,
  scores: {
    list: params => http.get('/scores', { params }),
    get: id => http.get(`/scores/${id}`),
    create: data => http.post('/scores', data),
    batchCreate: data =>
      http.post('/scores/batch', JSON.stringify(data), {
        headers: { 'Content-Type': 'application/json' }
      }),
    update: (id, data) => http.put(`/scores/${id}`, data),
    delete: id => http.delete(`/scores/${id}`),
    getStudentScores: (studentId, params) => http.get(`/scores/student/${studentId}`, { params }),
    getWeights: subjectId => http.get(`/scores/weights/${subjectId}`),
    updateWeights: (subjectId, data) => http.put(`/scores/weights/${subjectId}`, data)
  },
  semesters: {
    list: () => http.get('/semesters'),
    create: data => http.post('/semesters', data),
    update: (id, data) => http.put(`/semesters/${id}`, data),
    delete: id => http.delete(`/semesters/${id}`)
  },
  attendance: {
    list: params => http.get('/attendance', { params }),
    create: data => http.post('/attendance', data),
    update: (id, data) => http.put(`/attendance/${id}`, data),
    delete: id => http.delete(`/attendance/${id}`),
    getClassStats: (classId, params) => http.get(`/attendance/statistics/class/${classId}`, { params }),
    getStudentStats: (studentId, params) => http.get(`/attendance/statistics/student/${studentId}`, { params }),
    batchCreate: data =>
      http.post('/attendance/batch', JSON.stringify(data), {
        headers: { 'Content-Type': 'application/json' }
      }),
    batchCreateForClass: data =>
      http.post('/attendance/class-batch', JSON.stringify(data), {
        headers: { 'Content-Type': 'application/json' }
      })
  },
  dashboard: {
    getStats: params => http.get('/dashboard/stats', { params }),
    getClassRankings: params => http.get('/dashboard/rankings/classes', { params }),
    getStudentRankings: params => http.get('/dashboard/rankings/students', { params }),
    getSubjectRankings: (subjectId, params) => http.get(`/dashboard/rankings/subjects/${subjectId}`, { params }),
    getTrends: params => http.get('/dashboard/analysis/trends', { params }),
    getSubjectAnalysis: params => http.get('/dashboard/analysis/subjects', { params }),
    getHomeworkLearning: params => http.get('/dashboard/analysis/homework-learning', { params })
  },
  homework: {
    list: params => http.get('/homeworks', { params }),
    get: id => http.get(`/homeworks/${id}`),
    create: data => http.post('/homeworks', data),
    update: (id, data) => http.put(`/homeworks/${id}`, data),
    delete: id => http.delete(`/homeworks/${id}`),
    batchLateSubmission: data => http.post('/homeworks/batch-late-submission', data),
    batchRegrade: (homeworkId, data) =>
      http.post(`/homeworks/${homeworkId}/submissions/batch-regrade`, data),
    getMySubmission: id => http.get(`/homeworks/${id}/submission/me`),
    getMySubmissionHistory: id => http.get(`/homeworks/${id}/submission/me/history`),
    submit: (id, data) => http.post(`/homeworks/${id}/submission`, data),
    getSubmissions: (id, params) => http.get(`/homeworks/${id}/submissions`, { params }),
    listCourseStudents: subjectId => http.get(`/homeworks/courses/${subjectId}/students`),
    listStudentHomeworks: (subjectId, studentId, params) =>
      http.get(`/homeworks/courses/${subjectId}/students/${studentId}/homeworks`, { params }),
    submitAppeal: (homeworkId, submissionId, data) =>
      http.post(`/homeworks/${homeworkId}/submissions/${submissionId}/appeal`, data),
    acknowledgeAppeal: (homeworkId, submissionId) =>
      http.post(`/homeworks/${homeworkId}/submissions/${submissionId}/appeal/acknowledge`),
    getSubmissionHistory: (homeworkId, submissionId) =>
      http.get(`/homeworks/${homeworkId}/submissions/${submissionId}/history`),
    reviewSubmission: (homeworkId, submissionId, data) =>
      http.put(`/homeworks/${homeworkId}/submissions/${submissionId}/review`, data),
    regradeSubmission: (homeworkId, submissionId, data = {}) =>
      http.post(`/homeworks/${homeworkId}/submissions/${submissionId}/regrade`, data),
    downloadSubmissions: (id, data) =>
      http.post(`/homeworks/${id}/submissions/download`, data, {
        responseType: 'blob',
        returnFullResponse: true,
        ...fileTransferRequestConfig
      })
  },
  llmSettings: {
    listPresets: () => http.get('/llm-settings/presets'),
    createPreset: data => http.post('/llm-settings/presets', data),
    updatePreset: (id, data) => http.put(`/llm-settings/presets/${id}`, data),
    /** multipart with field `image` (File); do not set Content-Type manually. */
    validatePreset: (id, imageFile) => {
      const form = new FormData()
      form.append('image', imageFile)
      return httpQuiet.post(`/llm-settings/presets/${id}/validate`, form)
    },
    getCourseConfig: subjectId => http.get(`/llm-settings/courses/${subjectId}`),
    updateCourseConfig: (subjectId, data) => http.put(`/llm-settings/courses/${subjectId}`, data),
    getStudentQuota: subjectId => http.get(`/llm-settings/courses/student-quota/${subjectId}`),
    getGlobalQuotaPolicy: () => http.get('/llm-settings/admin/quota-policy'),
    updateGlobalQuotaPolicy: data => http.put('/llm-settings/admin/quota-policy', data),
    bulkQuotaOverrides: data => http.post('/llm-settings/admin/quota-overrides/bulk', data),
    setStudentQuotaOverride: (studentId, data) => http.put(`/llm-settings/admin/students/${studentId}/quota-override`, data)
  },
  notifications: {
    syncStatus: params => http.get('/notifications/sync-status', { params }),
    list: params => http.get('/notifications', { params }),
    get: id => http.get(`/notifications/${id}`),
    create: data => http.post('/notifications', data),
    update: (id, data) => http.put(`/notifications/${id}`, data),
    delete: id => http.delete(`/notifications/${id}`),
    markRead: id => http.post(`/notifications/${id}/read`),
    markAllRead: params => http.post('/notifications/mark-all-read', null, { params })
  },
  materials: {
    list: params => http.get('/materials', { params }),
    get: id => http.get(`/materials/${id}`),
    create: data => http.post('/materials', data),
    update: (id, data) => http.put(`/materials/${id}`, data),
    delete: id => http.delete(`/materials/${id}`)
  },
  materialChapters: {
    tree: params => http.get('/material-chapters/tree', { params }),
    create: (subjectId, data) => http.post(`/material-chapters?subject_id=${subjectId}`, data),
    update: (chapterId, data) => http.put(`/material-chapters/${chapterId}`, data),
    delete: (chapterId, subjectId) => http.delete(`/material-chapters/${chapterId}?subject_id=${subjectId}`),
    reorderChapters: (subjectId, data) => http.post(`/material-chapters/reorder?subject_id=${subjectId}`, data),
    reorderSections: (subjectId, data) =>
      http.post(`/material-chapters/sections/reorder?subject_id=${subjectId}`, data),
    addPlacement: (materialId, subjectId, data) =>
      http.post(`/material-chapters/materials/${materialId}/placements?subject_id=${subjectId}`, data),
    removePlacement: (sectionId, subjectId) =>
      http.delete(`/material-chapters/placements/${sectionId}?subject_id=${subjectId}`)
  },
  files: {
    upload: file => {
      const formData = new FormData()
      formData.append('file', file)
      return http.post('/files/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        ...fileTransferRequestConfig
      })
    }
  }
}

export default api
