<template>
  <div class="attendance-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">考勤管理</h1>
        <p class="page-subtitle">
          {{ selectedCourse ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分配班级'}` : '请先选择课程后查看考勤。' }}
        </p>
      </div>
      <div class="header-actions">
        <el-button v-if="selectedCourse" type="primary" @click="openCreateDialog">录入单条考勤</el-button>
        <el-button v-if="selectedCourse" type="success" @click="openBatchDialog">整课批量考勤</el-button>
      </div>
    </div>

    <el-empty v-if="!selectedCourse" description="请先选择一门课程。" />

    <template v-else>
      <el-card shadow="never" class="stats-card">
        <el-row :gutter="20">
          <el-col :span="6"><el-statistic title="考勤记录" :value="attendances.length" /></el-col>
          <el-col :span="6"><el-statistic title="出勤" :value="attendanceStats.present" /></el-col>
          <el-col :span="6"><el-statistic title="缺勤" :value="attendanceStats.absent" /></el-col>
          <el-col :span="6"><el-statistic title="出勤率" :value="attendanceStats.rate" suffix="%" /></el-col>
        </el-row>
      </el-card>

      <el-card shadow="never">
        <el-table :data="attendances" v-loading="loading">
          <el-table-column prop="student_name" label="学生" min-width="180" />
          <el-table-column prop="date" label="日期" width="180">
            <template #default="{ row }">
              {{ formatDate(row.date) }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)">{{ statusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
              <el-button type="danger" size="small" @click="deleteAttendance(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-dialog
      v-model="dialogVisible"
      :title="editingAttendance ? '编辑考勤' : '录入单条考勤'"
      width="560px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="学生" prop="student_id">
          <el-select v-model="form.student_id" filterable style="width: 100%">
            <el-option
              v-for="item in students"
              :key="item.student_id"
              :label="`${item.student_name} (${item.student_no || '无学号'})`"
              :value="item.student_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="考勤时间" prop="date">
          <el-date-picker v-model="form.date" type="datetime" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio label="present">出勤</el-radio>
            <el-radio label="absent">缺勤</el-radio>
            <el-radio label="late">迟到</el-radio>
            <el-radio label="leave">请假</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchDialogVisible" title="整课批量考勤" width="520px" destroy-on-close>
      <el-form ref="batchFormRef" :model="batchForm" :rules="batchRules" label-width="90px">
        <el-form-item label="考勤日期" prop="date">
          <el-date-picker v-model="batchForm.date" type="date" style="width: 100%" />
        </el-form-item>
        <el-form-item label="默认状态" prop="status">
          <el-radio-group v-model="batchForm.status">
            <el-radio label="present">出勤</el-radio>
            <el-radio label="absent">缺勤</el-radio>
            <el-radio label="late">迟到</el-radio>
            <el-radio label="leave">请假</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="batchForm.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchSubmitting" @click="submitBatchForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const batchSubmitting = ref(false)
const dialogVisible = ref(false)
const batchDialogVisible = ref(false)
const editingAttendance = ref(null)
const formRef = ref(null)
const batchFormRef = ref(null)

const students = ref([])
const attendances = ref([])

const selectedCourse = computed(() => userStore.selectedCourse)

const form = reactive({
  student_id: null,
  date: null,
  status: 'present',
  remark: ''
})

const batchForm = reactive({
  date: null,
  status: 'present',
  remark: ''
})

const rules = {
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  date: [{ required: true, message: '请选择考勤时间', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

const batchRules = {
  date: [{ required: true, message: '请选择考勤日期', trigger: 'change' }],
  status: [{ required: true, message: '请选择默认状态', trigger: 'change' }]
}

const attendanceStats = computed(() => {
  const present = attendances.value.filter(item => item.status === 'present').length
  const absent = attendances.value.filter(item => item.status === 'absent').length
  const total = attendances.value.length
  return {
    present,
    absent,
    rate: total ? Number(((present / total) * 100).toFixed(1)) : 0
  }
})

const loadStudents = async () => {
  if (!selectedCourse.value) {
    students.value = []
    return
  }
  students.value = await api.courses.getStudents(selectedCourse.value.id)
}

const loadAttendances = async () => {
  if (!selectedCourse.value) {
    attendances.value = []
    return
  }
  loading.value = true
  try {
    const result = await api.attendance.list({
      class_id: selectedCourse.value.class_id,
      subject_id: selectedCourse.value.id,
      page: 1,
      page_size: 1000
    })
    attendances.value = result?.data || []
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.student_id = null
  form.date = null
  form.status = 'present'
  form.remark = ''
}

const openCreateDialog = () => {
  editingAttendance.value = null
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = attendance => {
  editingAttendance.value = attendance
  Object.assign(form, {
    student_id: attendance.student_id,
    date: attendance.date ? new Date(attendance.date) : null,
    status: attendance.status,
    remark: attendance.remark || ''
  })
  dialogVisible.value = true
}

const openBatchDialog = () => {
  batchForm.date = null
  batchForm.status = 'present'
  batchForm.remark = ''
  batchDialogVisible.value = true
}

const submitForm = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = {
      student_id: form.student_id,
      class_id: selectedCourse.value.class_id,
      subject_id: selectedCourse.value.id,
      date: form.date,
      status: form.status,
      remark: form.remark
    }
    if (editingAttendance.value) {
      await api.attendance.update(editingAttendance.value.id, payload)
      ElMessage.success('考勤已更新')
    } else {
      await api.attendance.create(payload)
      ElMessage.success('考勤已录入')
    }
    dialogVisible.value = false
    await loadAttendances()
  } finally {
    submitting.value = false
  }
}

const submitBatchForm = async () => {
  await batchFormRef.value.validate()
  batchSubmitting.value = true
  try {
    await api.attendance.batchCreateForClass({
      class_id: selectedCourse.value.class_id,
      subject_id: selectedCourse.value.id,
      date: batchForm.date,
      status: batchForm.status,
      remark: batchForm.remark
    })
    ElMessage.success('整课考勤已保存')
    batchDialogVisible.value = false
    await loadAttendances()
  } finally {
    batchSubmitting.value = false
  }
}

const deleteAttendance = async attendance => {
  try {
    await ElMessageBox.confirm(`确认删除 ${attendance.student_name} 的考勤记录吗？`, '删除考勤', { type: 'warning' })
    await api.attendance.delete(attendance.id)
    ElMessage.success('考勤已删除')
    await loadAttendances()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除考勤失败', error)
    }
  }
}

const statusText = status => ({
  present: '出勤',
  absent: '缺勤',
  late: '迟到',
  leave: '请假'
}[status] || status)

const statusTag = status => ({
  present: 'success',
  absent: 'danger',
  late: 'warning',
  leave: 'info'
}[status] || '')

const formatDate = value => {
  if (!value) return '未设置'
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(async () => {
  await Promise.all([loadStudents(), loadAttendances()])
})

watch(selectedCourse, async () => {
  await Promise.all([loadStudents(), loadAttendances()])
})
</script>

<style scoped>
.attendance-page {
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
  gap: 12px;
}

.stats-card {
  margin-bottom: 20px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
