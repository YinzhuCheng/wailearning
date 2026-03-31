<template>
  <div class="notifications-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">通知中心</h1>
        <p class="page-subtitle">
          {{ selectedCourse ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分配班级'}` : '请先选择课程后查看通知。' }}
        </p>
      </div>
      <div class="header-actions">
        <el-button v-if="userStore.isStudent" @click="router.push('/courses')">切换课程</el-button>
        <el-badge :value="unreadCount" :hidden="unreadCount === 0">
          <el-button @click="markAllRead" :disabled="unreadCount === 0">全部标为已读</el-button>
        </el-badge>
        <el-button v-if="!userStore.isStudent && selectedCourse" type="primary" @click="openCreateDialog">
          发布通知
        </el-button>
      </div>
    </div>

    <el-empty v-if="!selectedCourse" description="请先选择一门课程。" />

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
          <el-table-column v-if="!userStore.isStudent" label="操作" width="180">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click.stop="editNotification(row)">编辑</el-button>
              <el-button type="danger" size="small" @click.stop="deleteNotification(row)">删除</el-button>
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
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="通知详情" width="620px" destroy-on-close>
      <el-descriptions v-if="currentNotification" :column="2" border>
        <el-descriptions-item label="通知标题" :span="2">{{ currentNotification.title }}</el-descriptions-item>
        <el-descriptions-item label="课程">{{ currentNotification.subject_name || selectedCourse?.name }}</el-descriptions-item>
        <el-descriptions-item label="优先级">{{ priorityText(currentNotification.priority) }}</el-descriptions-item>
        <el-descriptions-item label="发布人">{{ currentNotification.creator_name }}</el-descriptions-item>
        <el-descriptions-item label="发布时间">{{ formatDate(currentNotification.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="通知内容" :span="2">{{ currentNotification.content || '暂无内容' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
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

const selectedCourse = computed(() => userStore.selectedCourse)

const form = reactive({
  title: '',
  content: '',
  priority: 'normal',
  is_pinned: false
})

const rules = {
  title: [{ required: true, message: '请输入通知标题', trigger: 'blur' }]
}

const loadNotifications = async () => {
  if (!selectedCourse.value) {
    notifications.value = []
    unreadCount.value = 0
    return
  }

  loading.value = true
  try {
    const result = await api.notifications.list({
      subject_id: selectedCourse.value.id,
      page: 1,
      page_size: 200
    })
    notifications.value = result?.data || []
    unreadCount.value = result?.unread_count || 0
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.title = ''
  form.content = ''
  form.priority = 'normal'
  form.is_pinned = false
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
    is_pinned: editingNotification.value.is_pinned
  })
  dialogVisible.value = true
}

const submitForm = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = {
      title: form.title,
      content: form.content,
      priority: form.priority,
      is_pinned: form.is_pinned,
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
  await api.notifications.markAllRead({
    subject_id: selectedCourse.value?.id
  })
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

watch(selectedCourse, () => {
  loadNotifications()
})
</script>

<style scoped>
.notifications-page {
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

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
