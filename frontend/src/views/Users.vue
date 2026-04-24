<template>
  <div class="users-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">
          支持管理员、班主任、任课老师和学生四类用户。可勾选学生行后使用「批量调班」；管理员可将所选学生账号
          <strong>补录到学生管理花名册</strong>（用户名即学号），或加入指定课程选课。
        </p>
      </div>
      <div class="page-actions">
        <el-button
          v-if="isAdmin"
          type="primary"
          plain
          data-testid="users-sync-roster"
          :disabled="!batchSelectedStudents.length"
          :loading="rosterSyncSubmitting"
          @click="submitSyncStudentRoster"
        >
          同步到学生管理
        </el-button>
        <el-button
          v-if="isAdmin"
          type="primary"
          plain
          data-testid="users-open-add-course"
          :disabled="!batchSelectedStudents.length"
          @click="openAddToCourseDialog"
        >
          加入课程…
        </el-button>
        <el-button type="warning" plain data-testid="users-open-batch-class" @click="openBatchClassDialog">
          批量调班
        </el-button>
        <el-button type="success" plain @click="openStudentImportDialog">载入学生用户</el-button>
        <el-button type="primary" @click="openCreateDialog">新建用户</el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-table
        ref="usersTableRef"
        :data="users"
        v-loading="loading"
        row-key="id"
        @selection-change="handleUserSelectionChange"
      >
        <el-table-column type="selection" width="48" :selectable="row => row.role === 'student'" />
        <el-table-column prop="username" label="用户名" min-width="160" />
        <el-table-column prop="real_name" label="姓名" min-width="140" />
        <el-table-column label="角色" width="140">
          <template #default="{ row }">
            <el-tag :type="roleTag(row.role)">{{ roleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="所属班级" min-width="160">
          <template #default="{ row }">
            {{ classNameById(row.class_id) }}
          </template>
        </el-table-column>
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
          <el-select
            v-model="form.class_id"
            :placeholder="form.role === 'student' ? '请选择班级' : '可选'"
            style="width: 100%"
            :clearable="form.role !== 'student'"
          >
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
      v-model="batchClassDialogVisible"
      data-testid="dialog-batch-class"
      title="批量调班（学生账号）"
      width="560px"
      destroy-on-close
      @closed="resetBatchClassDialog"
    >
      <el-alert type="info" :closable="false" class="batch-class-alert">
        <template #title>说明</template>
        <p class="batch-class-alert-body">
          仅支持<strong>学生</strong>角色。将把所选账号的「所属班级」统一改到下方班级，并自动与<strong>学号相同</strong>的花名册记录对齐（含选课同步）。
          若花名册中尚无对应学号，请先由教务在「学生管理」中补录花名册。
        </p>
      </el-alert>

      <el-form label-width="100px" class="batch-class-form">
        <el-form-item label="目标班级" required>
          <el-select
            v-model="batchTargetClassId"
            placeholder="请选择班级"
            style="width: 100%"
            filterable
            data-testid="batch-class-target-select"
          >
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="已选学生">
          <span>{{ batchSelectedStudents.length }} 人</span>
          <el-button link type="primary" class="batch-clear-link" @click="clearUserTableSelection">
            清空表格勾选
          </el-button>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="batchClassDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          data-testid="batch-class-confirm"
          :loading="batchClassSubmitting"
          :disabled="!batchSelectedStudents.length || !batchTargetClassId"
          @click="submitBatchClass"
        >
          确认调班
        </el-button>
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

    <el-dialog
      v-model="addToCourseDialogVisible"
      data-testid="dialog-users-add-course"
      title="将所选学生加入课程选课"
      width="560px"
      destroy-on-close
      @closed="resetAddToCourseDialog"
    >
      <el-alert type="info" :closable="false" class="batch-class-alert">
        <template #title>说明</template>
        <p class="batch-class-alert-body">
          仅处理已勾选且角色为<strong>学生</strong>的账号。系统会按账号「所属班级」补录/对齐花名册（用户名即学号），再把所选学生加入下方课程的选课名单（须与本班花名册一致）。
        </p>
      </el-alert>
      <el-form label-width="100px" class="batch-class-form">
        <el-form-item label="目标课程" required>
          <el-select
            v-model="addToCourseSubjectId"
            placeholder="请选择课程"
            style="width: 100%"
            filterable
            data-testid="users-add-course-select"
          >
            <el-option
              v-for="c in coursesWithClass"
              :key="c.id"
              :label="`${c.name}（${c.class_name || '班'}）`"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="已选学生">
          <span>{{ batchSelectedStudents.length }} 人</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addToCourseDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          data-testid="users-add-course-confirm"
          :loading="addToCourseSubmitting"
          :disabled="!addToCourseSubjectId || !batchSelectedStudents.length"
          @click="submitAddToCourse"
        >
          确认加入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { loadAllPages } from '@/utils/pagedFetch'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const studentImportDialogVisible = ref(false)
const batchClassDialogVisible = ref(false)
const batchTargetClassId = ref(null)
const batchClassSubmitting = ref(false)
const pendingStudentsLoading = ref(false)
const studentImportSubmitting = ref(false)
const editingUser = ref(null)
const formRef = ref(null)
const pendingStudentsTableRef = ref(null)
const usersTableRef = ref(null)
const users = ref([])
const classes = ref([])
const pendingStudents = ref([])
const selectedPendingStudents = ref([])
const batchSelectedStudents = ref([])
const rosterSyncSubmitting = ref(false)
const addToCourseDialogVisible = ref(false)
const addToCourseSubjectId = ref(null)
const addToCourseSubmitting = ref(false)
const allSubjects = ref([])

const form = reactive({
  username: '',
  password: '',
  real_name: '',
  role: 'teacher',
  class_id: null,
  is_active: true
})

const rules = computed(() => {
  const base = {
    username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
    password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
    real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
    role: [{ required: true, message: '请选择角色', trigger: 'change' }]
  }
  if (form.role === 'student') {
    base.class_id = [{ required: true, message: '学生账号必须选择所属班级', trigger: 'change' }]
  }
  return base
})

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
    if (role !== 'student') {
      formRef.value?.clearValidate?.(['class_id'])
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

const coursesWithClass = computed(() =>
  (allSubjects.value || []).filter(c => c.class_id)
)

const loadSubjectsIfAdmin = async () => {
  if (!isAdmin.value) {
    allSubjects.value = []
    return
  }
  try {
    allSubjects.value = await api.subjects.list()
  } catch (e) {
    console.error(e)
    allSubjects.value = []
  }
}

const classNameById = classId => {
  if (classId == null) {
    return '—'
  }
  const row = classes.value.find(c => c.id === classId)
  return row ? row.name : `班级 #${classId}`
}

const handleUserSelectionChange = rows => {
  batchSelectedStudents.value = (rows || []).filter(r => r.role === 'student')
}

const clearUserTableSelection = () => {
  batchSelectedStudents.value = []
  usersTableRef.value?.clearSelection()
}

const openBatchClassDialog = () => {
  if (!batchSelectedStudents.value.length) {
    ElMessage.warning('请先在表格中勾选需要调班的学生账号')
    return
  }
  batchTargetClassId.value = null
  batchClassDialogVisible.value = true
}

const submitSyncStudentRoster = async () => {
  if (!batchSelectedStudents.value.length) {
    return
  }
  rosterSyncSubmitting.value = true
  try {
    const result = await api.users.upsertStudentRosterFromUsers({
      user_ids: batchSelectedStudents.value.map(u => u.id)
    })
    const parts = []
    if (result?.created) parts.push(`新建花名册 ${result.created} 人`)
    if (result?.updated) parts.push(`更新姓名 ${result.updated} 人`)
    if (result?.skipped) parts.push(`已一致跳过 ${result.skipped} 人`)
    const errCount = (result?.errors || []).length
    if (errCount) {
      parts.push(`未处理 ${errCount} 人`)
    }
    ElMessage[errCount ? 'warning' : 'success'](parts.length ? parts.join('；') : '已完成')
    if (errCount) {
      const lines = (result.errors || []).slice(0, 8).map(e => `${e.username || `#${e.user_id}`}：${e.reason}`)
      await ElMessageBox.alert(lines.join('\n'), '部分未处理', { confirmButtonText: '知道了' })
    }
    clearUserTableSelection()
    await loadUsers()
  } finally {
    rosterSyncSubmitting.value = false
  }
}

const resetAddToCourseDialog = () => {
  addToCourseSubjectId.value = null
}

const openAddToCourseDialog = async () => {
  if (!batchSelectedStudents.value.length) {
    ElMessage.warning('请先勾选学生账号')
    return
  }
  await loadSubjectsIfAdmin()
  if (!coursesWithClass.value.length) {
    ElMessage.warning('暂无可选课程（课程须绑定班级）')
    return
  }
  addToCourseSubjectId.value = null
  addToCourseDialogVisible.value = true
}

const submitAddToCourse = async () => {
  if (!addToCourseSubjectId.value || !batchSelectedStudents.value.length) {
    return
  }
  const courseId = addToCourseSubjectId.value
  const course = (allSubjects.value || []).find(c => c.id === courseId)
  if (!course?.class_id) {
    ElMessage.error('所选课程未绑定班级')
    return
  }
  addToCourseSubmitting.value = true
  try {
    const rosterRes = await api.users.upsertStudentRosterFromUsers({
      user_ids: batchSelectedStudents.value.map(u => u.id)
    })
    const rosterErr = (rosterRes?.errors || []).length
    if (rosterErr) {
      ElMessage.warning(`花名册同步有 ${rosterErr} 个账号未处理，请查看详情后继续`)
      const lines = (rosterRes.errors || []).slice(0, 10).map(
        e => `${e.username || `#${e.user_id}`}：${e.reason}`
      )
      await ElMessageBox.alert(lines.join('\n'), '花名册同步', { confirmButtonText: '知道了' })
    }

    const rosterRows = await loadAllPages(params =>
      api.students.list({
        ...params,
        class_id: course.class_id,
        page_size: 500
      })
    )
    const noToId = new Map(
      (rosterRows || []).map(r => [`${(r.student_no || '').trim()}`, r.id]).filter(([k]) => k)
    )
    const studentIds = []
    const missingNames = []
    for (const u of batchSelectedStudents.value) {
      const key = `${(u.username || '').trim()}`
      const sid = noToId.get(key)
      if (sid) {
        studentIds.push(sid)
      } else if (key) {
        missingNames.push(key)
      }
    }
    if (missingNames.length) {
      await ElMessageBox.alert(
        `以下学号在课程所属班级的花名册中仍未找到，无法进课：\n${missingNames.slice(0, 15).join('、')}${
          missingNames.length > 15 ? '…' : ''
        }`,
        '无法匹配花名册',
        { confirmButtonText: '知道了' }
      )
    }
    if (!studentIds.length) {
      addToCourseDialogVisible.value = false
      clearUserTableSelection()
      return
    }

    const enrollRes = await api.subjects.rosterEnroll(courseId, {
      student_ids: [...new Set(studentIds)]
    })
    const msgParts = []
    if (enrollRes?.created > 0) msgParts.push(`新增选课 ${enrollRes.created} 人`)
    if (enrollRes?.skipped_already_enrolled > 0) {
      msgParts.push(`已在课 ${enrollRes.skipped_already_enrolled} 人`)
    }
    if (enrollRes?.skipped_not_in_class_roster > 0) {
      msgParts.push(`非课程班级花名册 ${enrollRes.skipped_not_in_class_roster} 人`)
    }
    ElMessage.success(msgParts.length ? msgParts.join('；') : '选课无变更')
    addToCourseDialogVisible.value = false
    clearUserTableSelection()
  } catch (e) {
    console.error(e)
  } finally {
    addToCourseSubmitting.value = false
  }
}

const resetBatchClassDialog = () => {
  batchTargetClassId.value = null
}

const submitBatchClass = async () => {
  if (!batchSelectedStudents.value.length || !batchTargetClassId.value) {
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认将 ${batchSelectedStudents.value.length} 名学生账号调至「${classNameById(batchTargetClassId.value)}」吗？`,
      '批量调班',
      { type: 'warning', distinguishCancelAndClose: true }
    )
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      console.error(e)
    }
    return
  }

  batchClassSubmitting.value = true
  try {
    const result = await api.users.batchSetClass({
      user_ids: batchSelectedStudents.value.map(u => u.id),
      class_id: batchTargetClassId.value
    })
    const updated = result?.updated ?? 0
    const errors = result?.errors || []
    if (errors.length) {
      const lines = errors.slice(0, 12).map(e => `用户 #${e.user_id}：${e.reason}`)
      await ElMessageBox.alert(['部分未处理：', ...lines].join('\n'), '调班结果', {
        confirmButtonText: '知道了'
      })
    }
    ElMessage.success(`已更新 ${updated} 个学生账号的班级`)
    batchClassDialogVisible.value = false
    clearUserTableSelection()
    await loadUsers()
  } catch (e) {
    console.error('批量调班失败', e)
  } finally {
    batchClassSubmitting.value = false
  }
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
  await Promise.all([loadUsers(), loadClasses(), loadSubjectsIfAdmin()])
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

.batch-class-alert {
  margin-bottom: 16px;
}

.batch-class-alert-body {
  margin: 0;
  line-height: 1.65;
  color: #334155;
}

.batch-class-form {
  margin-top: 8px;
}

.batch-clear-link {
  margin-left: 12px;
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
