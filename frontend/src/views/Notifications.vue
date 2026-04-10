<template>
  <div class="notifications-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ pageTitle }}</h1>
        <p class="page-subtitle">{{ pageSubtitle }}</p>
      </div>
      <div class="header-actions">
        <el-badge :value="unreadCount" :hidden="unreadCount === 0">
          <el-button @click="markAllRead" :disabled="unreadCount === 0">全部标为已读</el-button>
        </el-badge>
        <el-button
          v-if="showCreateButton"
          type="primary"
          @click="openCreateDialog"
        >
          发布通知
        </el-button>
      </div>
    </div>

    <el-empty
      v-if="showEmpty"
      :description="emptyText"
    />

    <template v-else>
      <el-card shadow="never">
        <el-table :data="notifications" v-loading="loading" @row-click="viewNotification">
          <el-table-column width="70">
            <template #default="{ row }">
              <el-tag v-if="row.is_pinned" type="warning" size="small">置顶</el-tag>
              <span v-else-if="!row.is_read" class="unread-dot"></span>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="通知标题" min-width="220">
            <template #default="{ row }">
              <span :class="{ 'unread-title': !row.is_read }">{{ row.title }}</span>
            </template>
          </el-table-column>
          <el-table-column label="所属课程" min-width="160">
            <template #default="{ row }">
              {{ row.subject_name || '班级通知' }}
            </template>
          </el-table-column>
          <el-table-column label="附件" width="140">
            <template #default="{ row }">
              <el-button
                v-if="row.attachment_url"
                type="primary"
                link
                @click.stop="openAttachment(row)"
              >
                下载附件
              </el-button>
              <span v-else class="muted-text">无</span>
            </template>
          </el-table-column>
          <el-table-column prop="priority" label="优先级" width="120">
            <template #default="{ row }">
              <el-tag :type="priorityType(row.priority)">
                {{ priorityText(row.priority) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="creator_name" label="发布人" width="120" />
          <el-table-column prop="created_at" label="发布时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column v-if="showManageColumn" label="操作" width="180">
            <template #default="{ row }">
              <el-button
                v-if="canManageNotification(row)"
                type="primary"
                size="small"
                @click.stop="editNotification(row)"
              >
                编辑
              </el-button>
              <el-button
                v-if="canManageNotification(row)"
                type="danger"
                size="small"
                @click.stop="deleteNotification(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-dialog
      v-model="dialogVisible"
      :title="editingNotification ? '编辑通知' : '发布通知'"
      width="620px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="通知标题" prop="title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option label="普通" value="normal" />
            <el-option label="重要" value="important" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="置顶">
          <el-switch v-model="form.is_pinned" />
        </el-form-item>
        <el-form-item label="通知内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="6" />
        </el-form-item>
        <el-form-item label="附件">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            :limit="1"
            :on-change="handleAttachmentChange"
          >
            <el-button>选择附件</el-button>
          </el-upload>
          <div class="attachment-help">{{ attachmentHintText }}</div>
          <div v-if="attachmentDisplayName" class="attachment-preview">
            <el-button
              v-if="form.attachment_url"
              type="primary"
              link
              @click="downloadFormAttachment"
            >
              {{ attachmentDisplayName }}
            </el-button>
            <span v-else>{{ attachmentDisplayName }}</span>
            <el-button link type="danger" @click="removeAttachment">移除</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="通知详情" width="620px" destroy-on-close>
      <el-descriptions v-if="currentNotification" :column="2" border>
        <el-descriptions-item label="通知标题" :span="2">{{ currentNotification.title }}</el-descriptions-item>
        <el-descriptions-item label="班级">{{ currentNotification.class_name || currentClassName || selectedCourse?.class_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="课程">{{ currentNotification.subject_name || '班级通知' }}</el-descriptions-item>
        <el-descriptions-item label="优先级">{{ priorityText(currentNotification.priority) }}</el-descriptions-item>
        <el-descriptions-item label="发布人">{{ currentNotification.creator_name }}</el-descriptions-item>
        <el-descriptions-item label="发布时间" :span="2">{{ formatDate(currentNotification.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="通知内容" :span="2">{{ currentNotification.content || '暂无内容' }}</el-descriptions-item>
        <el-descriptions-item label="附件" :span="2">
          <el-button v-if="currentNotification.attachment_url" type="primary" link @click="openAttachment(currentNotification)">
            {{ currentNotification.attachment_name || '下载附件' }}
          </el-button>
          <span v-else class="muted-text">无附件</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { attachmentHintText, downloadAttachment, validateAttachmentFile } from '@/utils/attachments'
import {
  filterCoursesByClassId,
  filterImportantNotifications,
  filterNotificationsForClass,
  resolveClassTeacherClassId,
  resolveClassTeacherClassName
} from '@/utils/classTeacher'
import { loadAllPages } from '@/utils/pagedFetch'

const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentNotification = ref(null)
const editingNotification = ref(null)
const notifications = ref([])
const unreadCount = ref(0)
const formRef = ref(null)
const attachmentFile = ref(null)
const classTeacherCoursePool = ref([])

const selectedCourse = computed(() => userStore.selectedCourse)
const isClassTeacherView = computed(() => userStore.isClassTeacher)
const currentClassId = computed(() => resolveClassTeacherClassId(userStore.userInfo, classTeacherCoursePool.value))
const currentClassName = computed(() => resolveClassTeacherClassName(userStore.userInfo, classTeacherCoursePool.value) || '未分配班级')
const currentClassCourses = computed(() => filterCoursesByClassId(classTeacherCoursePool.value, currentClassId.value))
const currentClassCourseIds = computed(() => new Set(currentClassCourses.value.map(course => Number(course.id))))
const attachmentDisplayName = computed(() => attachmentFile.value?.name || form.attachment_name || '')

const pageTitle = computed(() => (isClassTeacherView.value ? '通知信息' : '通知中心'))
const pageSubtitle = computed(() => {
  if (isClassTeacherView.value) {
    return currentClassId.value
      ? `${currentClassName.value} 全部课程的重要通知`
      : '请先为班主任账号分配班级。'
  }

  return selectedCourse.value
    ? `${selectedCourse.value.name} · ${selectedCourse.value.class_name || '未分配班级'}`
    : '请先选择课程后查看通知。'
})

const showEmpty = computed(() => {
  if (isClassTeacherView.value) {
    return !currentClassId.value
  }

  return !selectedCourse.value
})

const emptyText = computed(() => (isClassTeacherView.value ? '当前班主任账号没有绑定班级。' : '请先选择一门课程。'))
const showCreateButton = computed(() => !userStore.isStudent && !isClassTeacherView.value && Boolean(selectedCourse.value))
const showManageColumn = computed(() => !userStore.isStudent && !isClassTeacherView.value)

const form = reactive({
  title: '',
  content: '',
  priority: 'normal',
  is_pinned: false,
  attachment_name: '',
  attachment_url: '',
  remove_attachment: false
})

const rules = {
  title: [{ required: true, message: '请输入通知标题', trigger: 'blur' }]
}

const resetForm = () => {
  form.title = ''
  form.content = ''
  form.priority = 'normal'
  form.is_pinned = false
  form.attachment_name = ''
  form.attachment_url = ''
  form.remove_attachment = false
  attachmentFile.value = null
}

const loadClassTeacherNotifications = async () => {
  classTeacherCoursePool.value = await userStore.fetchTeachingCourses(true)

  if (!currentClassId.value) {
    notifications.value = []
    unreadCount.value = 0
    return
  }

  const allNotifications = await loadAllPages(params => api.notifications.list(params))
  const filtered = filterImportantNotifications(
    filterNotificationsForClass(allNotifications, currentClassId.value, currentClassCourseIds.value)
  )

  notifications.value = filtered
  unreadCount.value = filtered.filter(item => !item.is_read).length
}

const loadLegacyNotifications = async () => {
  if (!selectedCourse.value) {
    notifications.value = []
    unreadCount.value = 0
    return
  }

  const result = await api.notifications.list({
    subject_id: selectedCourse.value.id,
    page: 1,
    page_size: 100
  })
  notifications.value = result?.data || []
  unreadCount.value = Number(result?.unread_count || 0)
}

const loadNotifications = async () => {
  loading.value = true
  try {
    if (isClassTeacherView.value) {
      await loadClassTeacherNotifications()
    } else {
      await loadLegacyNotifications()
    }
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  editingNotification.value = null
  resetForm()
  dialogVisible.value = true
}

const editNotification = async row => {
  editingNotification.value = await api.notifications.get(row.id)
  Object.assign(form, {
    title: editingNotification.value.title,
    content: editingNotification.value.content,
    priority: editingNotification.value.priority,
    is_pinned: editingNotification.value.is_pinned,
    attachment_name: editingNotification.value.attachment_name || '',
    attachment_url: editingNotification.value.attachment_url || '',
    remove_attachment: false
  })
  attachmentFile.value = null
  dialogVisible.value = true
}

const handleAttachmentChange = uploadFile => {
  const file = uploadFile.raw
  const result = validateAttachmentFile(file)
  if (!result.valid) {
    ElMessage.error(result.message)
    return false
  }

  attachmentFile.value = file
  form.attachment_name = file.name
  form.attachment_url = ''
  form.remove_attachment = false
  return false
}

const removeAttachment = () => {
  attachmentFile.value = null
  form.attachment_name = ''
  form.attachment_url = ''
  form.remove_attachment = true
}

const uploadAttachmentIfNeeded = async () => {
  if (!attachmentFile.value) {
    return {
      attachment_name: form.attachment_name || null,
      attachment_url: form.attachment_url || null,
      remove_attachment: form.remove_attachment
    }
  }

  const uploaded = await api.files.upload(attachmentFile.value)
  form.attachment_name = uploaded.attachment_name
  form.attachment_url = uploaded.attachment_url
  form.remove_attachment = false
  attachmentFile.value = null

  return {
    attachment_name: uploaded.attachment_name,
    attachment_url: uploaded.attachment_url,
    remove_attachment: false
  }
}

const submitForm = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    const attachment = await uploadAttachmentIfNeeded()
    const payload = {
      title: form.title,
      content: form.content,
      priority: form.priority,
      is_pinned: form.is_pinned,
      attachment_name: attachment.attachment_name,
      attachment_url: attachment.attachment_url,
      remove_attachment: attachment.remove_attachment,
      class_id: selectedCourse.value.class_id,
      subject_id: selectedCourse.value.id
    }

    if (editingNotification.value) {
      await api.notifications.update(editingNotification.value.id, payload)
      ElMessage.success('通知已更新')
    } else {
      await api.notifications.create(payload)
      ElMessage.success('通知已发布')
    }

    dialogVisible.value = false
    await loadNotifications()
  } finally {
    submitting.value = false
  }
}

const viewNotification = async row => {
  currentNotification.value = await api.notifications.get(row.id)
  if (!currentNotification.value.is_read) {
    await api.notifications.markRead(row.id)
  }
  detailVisible.value = true
  await loadNotifications()
}

const openAttachment = async row => {
  if (!row?.attachment_url) {
    return
  }
  await downloadAttachment(row.attachment_url, row.attachment_name)
}

const downloadFormAttachment = async () => {
  await downloadAttachment(form.attachment_url, attachmentDisplayName.value)
}

const canManageNotification = row => userStore.isAdmin || row.created_by === userStore.userInfo?.id

const deleteNotification = async row => {
  try {
    await ElMessageBox.confirm(`确认删除通知“${row.title}”吗？`, '删除通知', { type: 'warning' })
    await api.notifications.delete(row.id)
    ElMessage.success('通知已删除')
    await loadNotifications()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除通知失败', error)
    }
  }
}

const markAllRead = async () => {
  if (isClassTeacherView.value) {
    await Promise.all(
      notifications.value
        .filter(item => !item.is_read)
        .map(item => api.notifications.markRead(item.id))
    )
  } else {
    await api.notifications.markAllRead({
      subject_id: selectedCourse.value?.id
    })
  }

  await loadNotifications()
}

const priorityText = priority => ({
  normal: '普通',
  important: '重要',
  urgent: '紧急'
}[priority] || '普通')

const priorityType = priority => ({
  normal: '',
  important: 'warning',
  urgent: 'danger'
}[priority] || '')

const formatDate = value => {
  if (!value) return '未设置'
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(() => {
  loadNotifications()
})

watch(
  () => [selectedCourse.value?.id, userStore.userInfo?.id],
  () => {
    loadNotifications()
  }
)
</script>

<style scoped>
.notifications-page {
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
  align-items: center;
  gap: 12px;
}

.unread-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #2563eb;
}

.unread-title {
  font-weight: 700;
}

.attachment-help,
.muted-text {
  color: #64748b;
  font-size: 13px;
}

.attachment-help {
  margin-top: 8px;
}

.attachment-preview {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
