<template>
  <div class="users-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">支持管理员、班主任、任课老师和学生四类用户。</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">新建用户</el-button>
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const editingUser = ref(null)
const formRef = ref(null)
const users = ref([])
const classes = ref([])

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

const openCreateDialog = () => {
  editingUser.value = null
  resetForm()
  dialogVisible.value = true
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
    await ElMessageBox.confirm(`确认删除用户“${user.real_name}”吗？`, '删除用户', { type: 'warning' })
    await api.users.delete(user.id)
    ElMessage.success('用户已删除')
    await loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除用户失败', error)
    }
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

.page-title {
  margin: 0 0 8px;
  font-size: 28px;
  color: #0f172a;
}

.page-subtitle {
  margin: 0;
  color: #64748b;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
