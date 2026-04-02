<template>
  <div class="users-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">支持管理员、班主任、任课老师和学生四类用户。</p>
      </div>
      <div class="page-actions">
        <el-button type="success" plain @click="openStudentImportDialog">载入学生用户</el-button>
        <el-button type="primary" @click="openCreateDialog">新建用户</el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="users" v-loading="loading">
        <el-table-column prop="username" label="用户名" min-width="160" />
        <el-table-column prop="real_name" label="姓名" min-width="140" />
        <el-table-column label="角色" width="140">
          <template #default="{ row }">
            <el-tag :type="roleTag(row.role)">{{ roleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="class_id" label="班级ID" width="120" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              type="danger"
              size="small"
              :disabled="isDeleteDisabled(row)"
              @click="deleteUser(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingUser ? '编辑用户' : '新建用户'"
      width="520px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="Boolean(editingUser)" />
        </el-form-item>
        <el-form-item v-if="!editingUser" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="form.real_name" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio label="admin">管理员</el-radio>
            <el-radio label="class_teacher">班主任</el-radio>
            <el-radio label="teacher">任课老师</el-radio>
            <el-radio label="student">学生</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="showClassAssignmentField" label="所属班级" prop="class_id">
          <el-select v-model="form.class_id" placeholder="可选" style="width: 100%" clearable>
            <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editingUser" label="是否启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="studentImportDialogVisible"
      title="载入学生用户"
      width="920px"
      destroy-on-close
    >
      <div class="student-import-dialog">
        <el-alert
          title="将为所选学生批量生成系统账号，用户名和初始密码都使用学号，角色固定为学生。"
          type="info"
          :closable="false"
        />

        <div class="student-import-toolbar">
          <div class="student-import-summary">
            <span>待载入学生 {{ pendingStudents.length }} 人</span>
            <span>已选择 {{ selectedPendingCount }} 人</span>
          </div>

          <div class="student-import-actions">
            <el-button link type="primary" @click="toggleAllPendingStudents">全选</el-button>
            <el-button link @click="clearPendingStudentSelection">清空选择</el-button>
            <el-button :loading="pendingStudentsLoading" @click="loadPendingStudents">
              刷新名单
            </el-button>
          </div>
        </div>

        <el-empty
          v-if="!pendingStudentsLoading && !pendingStudents.length"
          description="当前所有学生都已生成系统用户。"
        />

        <el-table
          v-else
          ref="pendingStudentsTableRef"
          :data="pendingStudents"
          v-loading="pendingStudentsLoading"
          max-height="420"
          @selection-change="handlePendingSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="name" label="学生姓名" min-width="140" />
          <el-table-column prop="student_no" label="学号" min-width="160" />
          <el-table-column prop="class_name" label="所属班级" min-width="180" />
          <el-table-column label="状态" width="120">
            <template #default>
              <el-tag type="info">未生成</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <template #footer>
        <el-button @click="studentImportDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="studentImportSubmitting"
          :disabled="!selectedPendingCount"
          @click="submitStudentImport"
        >
          批量生成账号
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const studentImportDialogVisible = ref(false)
const pendingStudentsLoading = ref(false)
const studentImportSubmitting = ref(false)
const editingUser = ref(null)
const formRef = ref(null)
const pendingStudentsTableRef = ref(null)
const users = ref([])
const classes = ref([])
const pendingStudents = ref([])
const selectedPendingStudents = ref([])

const form = reactive({
  username: '',
  password: '',
  real_name: '',
  role: 'teacher',
  class_id: null,
  is_active: true
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

const roleText = role => ({
  admin: '管理员',
  class_teacher: '班主任',
  teacher: '任课老师',
  student: '学生'
}[role] || role)

const roleTag = role => ({
  admin: 'danger',
  class_teacher: 'warning',
  teacher: 'success',
  student: 'info'
}[role] || '')

const isDeleteDisabled = user => user.role === 'admin'

const showClassAssignmentField = computed(() => form.role !== 'teacher')
const selectedPendingCount = computed(() => selectedPendingStudents.value.length)

watch(
  () => form.role,
  role => {
    if (role === 'teacher') {
      form.class_id = null
    }
  }
)

const resetForm = () => {
  Object.assign(form, {
    username: '',
    password: '',
    real_name: '',
    role: 'teacher',
    class_id: null,
    is_active: true
  })
}

const loadUsers = async () => {
  loading.value = true
  try {
    users.value = await api.users.list()
  } finally {
    loading.value = false
  }
}

const loadClasses = async () => {
  classes.value = await api.classes.list()
}

const loadPendingStudents = async () => {
  pendingStudentsLoading.value = true
  try {
    pendingStudents.value = await api.users.listStudentCandidates()
    selectedPendingStudents.value = []
    pendingStudentsTableRef.value?.clearSelection()
  } finally {
    pendingStudentsLoading.value = false
  }
}

const openCreateDialog = () => {
  editingUser.value = null
  resetForm()
  dialogVisible.value = true
}

const openStudentImportDialog = async () => {
  studentImportDialogVisible.value = true
  clearPendingStudentSelection()
  await loadPendingStudents()
}

const openEditDialog = user => {
  editingUser.value = user
  Object.assign(form, {
    username: user.username,
    password: '',
    real_name: user.real_name,
    role: user.role,
    class_id: user.role === 'teacher' ? null : user.class_id,
    is_active: user.is_active
  })
  dialogVisible.value = true
}

const buildPayload = () => ({
  ...form,
  class_id: form.role === 'teacher' ? null : form.class_id
})

const submitForm = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = buildPayload()
    if (editingUser.value) {
      await api.users.update(editingUser.value.id, {
        real_name: payload.real_name,
        role: payload.role,
        class_id: payload.class_id,
        is_active: payload.is_active
      })
      ElMessage.success('用户已更新')
    } else {
      await api.users.create(payload)
      ElMessage.success('用户已创建')
    }
    dialogVisible.value = false
    await loadUsers()
  } finally {
    submitting.value = false
  }
}

const deleteUser = async user => {
  try {
    await ElMessageBox.confirm(
      `确认删除用户“${user.real_name}”（账号：${user.username}）吗？此操作不可恢复。`,
      '删除用户',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        distinguishCancelAndClose: true
      }
    )
    await api.users.delete(user.id)
    ElMessage.success('用户已删除')
    await loadUsers()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      console.error('删除用户失败', error)
    }
  }
}

const handlePendingSelectionChange = rows => {
  selectedPendingStudents.value = rows
}

const clearPendingStudentSelection = () => {
  selectedPendingStudents.value = []
  pendingStudentsTableRef.value?.clearSelection()
}

const toggleAllPendingStudents = () => {
  pendingStudentsTableRef.value?.toggleAllSelection()
}

const submitStudentImport = async () => {
  if (!selectedPendingCount.value) {
    ElMessage.warning('请至少选择一名学生')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认批量生成 ${selectedPendingCount.value} 名学生的系统账号吗？用户名和初始密码都将使用学号。`,
      '载入学生用户',
      {
        type: 'warning',
        confirmButtonText: '确认生成',
        cancelButtonText: '取消',
        distinguishCancelAndClose: true
      }
    )
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      console.error('确认载入学生用户失败', error)
    }
    return
  }

  studentImportSubmitting.value = true

  try {
    const result = await api.users.loadStudentCandidates({
      student_ids: selectedPendingStudents.value.map(student => student.id)
    })

    const successCount = result?.success || 0
    const failedCount = result?.failed || 0
    const createdUsers = result?.created_users || []
    const errorRows = result?.errors || []

    await Promise.all([loadUsers(), loadPendingStudents()])
    clearPendingStudentSelection()

    if (successCount > 0) {
      ElMessage({
        type: failedCount > 0 ? 'warning' : 'success',
        message:
          failedCount > 0
            ? `已生成 ${successCount} 个学生账号，${failedCount} 个未生成`
            : `已成功生成 ${successCount} 个学生账号`,
        duration: 5000
      })
    } else {
      ElMessage.warning('没有生成任何学生账号')
    }

    if (failedCount > 0) {
      const detailLines = [`成功：${successCount} 个`, `失败：${failedCount} 个`]

      if (createdUsers.length > 0) {
        detailLines.push('')
        detailLines.push(`已生成：${createdUsers.slice(0, 10).join('、')}`)
      }

      const errorLines = errorRows.slice(0, 10).map(item => {
        const name = item.student_name || `学生ID ${item.student_id ?? '-'}`
        const studentNo = item.student_no ? `（${item.student_no}）` : ''
        return `${name}${studentNo}：${item.reason}`
      })

      if (errorLines.length > 0) {
        detailLines.push('')
        detailLines.push('失败明细：')
        detailLines.push(...errorLines)
      }

      await ElMessageBox.alert(detailLines.join('\n'), '载入结果', {
        confirmButtonText: '知道了'
      })
    }

    if (failedCount === 0 || pendingStudents.value.length === 0) {
      studentImportDialogVisible.value = false
    }
  } finally {
    studentImportSubmitting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadUsers(), loadClasses()])
})
</script>

<style scoped>
.users-page {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;
}

.page-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
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

.student-import-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.student-import-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.student-import-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: #475569;
}

.student-import-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .page-header,
  .student-import-toolbar {
    flex-direction: column;
  }

  .page-actions,
  .student-import-actions {
    justify-content: stretch;
  }
}
</style>
