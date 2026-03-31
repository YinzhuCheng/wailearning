<template>
  <div class="scores-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">成绩管理</h1>
        <p class="page-subtitle">
          {{ selectedCourse ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分配班级'}` : '请先选择课程后查看成绩。' }}
        </p>
      </div>
      <div class="header-actions">
        <el-button v-if="selectedCourse" type="primary" @click="openCreateDialog">录入成绩</el-button>
      </div>
    </div>

    <el-empty v-if="!selectedCourse" description="请先选择一门课程。" />

    <template v-else>
      <el-card shadow="never" class="stats-card">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic title="成绩记录" :value="scores.length" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="平均分" :value="averageScore" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="最高分" :value="maxScore" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="及格率" :value="passRate" suffix="%" />
          </el-col>
        </el-row>
      </el-card>

      <el-card shadow="never">
        <div class="toolbar">
          <el-select v-model="filterSemester" placeholder="选择学期" clearable style="width: 200px" @change="loadScores">
            <el-option v-for="item in semesters" :key="item.id" :label="item.name" :value="item.name" />
          </el-select>
        </div>

        <el-table :data="scores" v-loading="loading">
          <el-table-column prop="student_name" label="学生" min-width="180" />
          <el-table-column prop="score" label="成绩" width="100">
            <template #default="{ row }">
              <el-tag :type="scoreTag(row.score)">{{ row.score }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="exam_type" label="考试类型" width="140" />
          <el-table-column prop="semester" label="学期" width="140" />
          <el-table-column prop="exam_date" label="考试时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.exam_date) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
              <el-button type="danger" size="small" @click="deleteScore(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-dialog
      v-model="dialogVisible"
      :title="editingScore ? '编辑成绩' : '录入成绩'"
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
        <el-form-item label="成绩" prop="score">
          <el-input-number v-model="form.score" :min="0" :max="100" :step="0.5" />
        </el-form-item>
        <el-form-item label="考试类型" prop="exam_type">
          <el-input v-model="form.exam_type" />
        </el-form-item>
        <el-form-item label="考试时间" prop="exam_date">
          <el-date-picker v-model="form.exam_date" type="datetime" style="width: 100%" />
        </el-form-item>
        <el-form-item label="所属学期" prop="semester">
          <el-select v-model="form.semester" style="width: 100%">
            <el-option v-for="item in semesters" :key="item.id" :label="item.name" :value="item.name" />
          </el-select>
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
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const editingScore = ref(null)
const formRef = ref(null)

const scores = ref([])
const semesters = ref([])
const students = ref([])
const filterSemester = ref('')

const selectedCourse = computed(() => userStore.selectedCourse)

const form = reactive({
  student_id: null,
  score: 0,
  exam_type: '平时成绩',
  exam_date: null,
  semester: ''
})

const rules = {
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  score: [{ required: true, message: '请输入成绩', trigger: 'blur' }],
  semester: [{ required: true, message: '请选择学期', trigger: 'change' }]
}

const averageScore = computed(() => {
  if (!scores.value.length) return 0
  return Number((scores.value.reduce((sum, item) => sum + Number(item.score || 0), 0) / scores.value.length).toFixed(1))
})

const maxScore = computed(() => scores.value.length ? Math.max(...scores.value.map(item => Number(item.score || 0))) : 0)
const passRate = computed(() => {
  if (!scores.value.length) return 0
  const passed = scores.value.filter(item => Number(item.score || 0) >= 60).length
  return Number(((passed / scores.value.length) * 100).toFixed(1))
})

const loadSemesters = async () => {
  semesters.value = await api.semesters.list()
  if (!form.semester && semesters.value.length) {
    form.semester = semesters.value[0].name
  }
}

const loadStudents = async () => {
  if (!selectedCourse.value) {
    students.value = []
    return
  }
  students.value = await api.courses.getStudents(selectedCourse.value.id)
}

const loadScores = async () => {
  if (!selectedCourse.value) {
    scores.value = []
    return
  }
  loading.value = true
  try {
    const result = await api.scores.list({
      class_id: selectedCourse.value.class_id,
      subject_id: selectedCourse.value.id,
      semester: filterSemester.value || undefined,
      page: 1,
      page_size: 500
    })
    scores.value = result?.data || []
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.student_id = null
  form.score = 0
  form.exam_type = '平时成绩'
  form.exam_date = null
  form.semester = semesters.value[0]?.name || ''
}

const openCreateDialog = () => {
  editingScore.value = null
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = score => {
  editingScore.value = score
  Object.assign(form, {
    student_id: score.student_id,
    score: score.score,
    exam_type: score.exam_type,
    exam_date: score.exam_date ? new Date(score.exam_date) : null,
    semester: score.semester
  })
  dialogVisible.value = true
}

const submitForm = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = {
      student_id: form.student_id,
      subject_id: selectedCourse.value.id,
      class_id: selectedCourse.value.class_id,
      score: form.score,
      exam_type: form.exam_type,
      exam_date: form.exam_date,
      semester: form.semester
    }
    if (editingScore.value) {
      await api.scores.update(editingScore.value.id, payload)
      ElMessage.success('成绩已更新')
    } else {
      await api.scores.create(payload)
      ElMessage.success('成绩已录入')
    }
    dialogVisible.value = false
    await loadScores()
  } finally {
    submitting.value = false
  }
}

const deleteScore = async score => {
  try {
    await ElMessageBox.confirm(`确认删除 ${score.student_name} 的成绩记录吗？`, '删除成绩', { type: 'warning' })
    await api.scores.delete(score.id)
    ElMessage.success('成绩已删除')
    await loadScores()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除成绩失败', error)
    }
  }
}

const scoreTag = score => {
  if (score >= 90) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

const formatDate = value => {
  if (!value) return '未设置'
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(async () => {
  await Promise.all([loadSemesters(), loadStudents(), loadScores()])
})

watch(selectedCourse, async () => {
  await Promise.all([loadStudents(), loadScores()])
})
</script>

<style scoped>
.scores-page {
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

.toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
