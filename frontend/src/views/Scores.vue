<template>
  <div class="scores-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">成绩管理</h1>
        <p class="page-subtitle">
          {{
            selectedCourse
              ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分配班级'}`
              : '请先选择课程后查看成绩。'
          }}
        </p>
      </div>
      <div class="header-actions">
        <el-button v-if="selectedCourse" @click="openSchemeDialog">平时分占比</el-button>
        <el-button v-if="selectedCourse" @click="openWeightDialog">各次考试占比</el-button>
        <el-button v-if="selectedCourse" :loading="compositionLoading" @click="loadClassCompositions">
          刷新成绩构成
        </el-button>
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

      <el-card shadow="never" class="weights-card">
        <template #header>
          <div class="card-header-inline">
            <strong>成绩构成说明</strong>
            <span class="weight-total">三部分之和须为 100%</span>
          </div>
        </template>
        <p class="scheme-hint">
          作业平时分由系统根据各次作业批改得分折算；「{{ OTHER_DAILY }}」与各次考试成绩由教师在本页录入；加权总成绩 =
          作业均分×作业占比 + 其他平时分×其占比 + 各次考试×对应占比。
        </p>
        <div class="scheme-tags">
          <el-tag type="success" size="large">作业平时分 {{ gradeScheme.homework_weight }}%</el-tag>
          <el-tag type="warning" size="large">{{ OTHER_DAILY }} {{ gradeScheme.extra_daily_weight }}%</el-tag>
          <el-tag v-for="item in examWeights" :key="item.exam_type" type="info" size="large">
            {{ item.exam_type }} {{ Number(item.weight).toFixed(0) }}%
          </el-tag>
        </div>
        <p class="scheme-sum" :class="{ invalid: !partsSumValid }">
          当前合计：作业 {{ gradeScheme.homework_weight }}% + 其他平时 {{ gradeScheme.extra_daily_weight }}% + 考试
          {{ totalExamWeight }}% = {{ partsSum }}%
          <template v-if="!partsSumValid">（须等于 100% 才能计算总成绩）</template>
        </p>
      </el-card>

      <el-card shadow="never" class="totals-card">
        <template #header>
          <div class="card-header-inline">
            <strong>学生成绩构成（加权总成绩）</strong>
            <div class="toolbar-inline">
              <el-select
                v-model="compositionSemester"
                placeholder="学期"
                style="width: 200px"
                @change="loadClassCompositions"
              >
                <el-option v-for="item in semesters" :key="item.id" :label="item.name" :value="item.name" />
              </el-select>
            </div>
          </div>
        </template>
        <el-table
          v-loading="compositionLoading"
          :data="classCompositions"
          empty-text="请选择学期并点击「刷新成绩构成」。"
        >
          <el-table-column prop="student_name" label="学生" min-width="120" />
          <el-table-column prop="student_no" label="学号" width="120" />
          <el-table-column label="作业平时(折算%)" width="130">
            <template #default="{ row }">{{ row.homework_average_percent ?? '—' }}</template>
          </el-table-column>
          <el-table-column :label="OTHER_DAILY" width="100">
            <template #default="{ row }">{{ row.other_daily_score ?? '—' }}</template>
          </el-table-column>
          <el-table-column
            v-for="w in examWeights"
            :key="w.exam_type"
            :label="w.exam_type"
            width="100"
          >
            <template #default="{ row }">{{ row.exam_scores?.[w.exam_type] ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="总成绩" width="110">
            <template #default="{ row }">
              <el-tag v-if="row.weighted_total != null" :type="scoreTag(row.weighted_total)">
                {{ row.weighted_total }}
              </el-tag>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="missing_for_total" label="缺项" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              {{ (row.missing_for_total || []).length ? row.missing_for_total.join('、') : '—' }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="appeals-card">
        <template #header>
          <div class="card-header-inline">
            <strong>成绩申诉</strong>
            <el-button size="small" @click="loadAppeals">刷新</el-button>
          </div>
        </template>
        <el-table :data="appeals" empty-text="暂无申诉">
          <el-table-column prop="id" label="编号" width="70" />
          <el-table-column prop="student_name" label="学生" width="100" />
          <el-table-column prop="semester" label="学期" width="120" />
          <el-table-column prop="target_component" label="申诉对象" min-width="120" />
          <el-table-column prop="reason_text" label="理由" min-width="160" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'pending'"
                type="primary"
                link
                @click="openAppealDialog(row)"
              >
                回复
              </el-button>
            </template>
          </el-table-column>
        </el-table>
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
          <el-table-column prop="exam_type" label="类型" width="140" />
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
      :title="editingScore ? '编辑成绩' : batchEntryStep === 1 ? '录入成绩' : '批量录入成绩'"
      :width="editingScore ? '560px' : batchEntryStep === 1 ? '560px' : '760px'"
      destroy-on-close
    >
      <el-form
        v-if="editingScore || batchEntryStep === 1"
        ref="formRef"
        :model="form"
        :rules="editingScore ? rules : batchRules"
        label-width="90px"
      >
        <template v-if="editingScore">
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
          <el-form-item label="类型" prop="exam_type">
            <el-input v-model="form.exam_type" placeholder="各次考试 或 其他平时分" />
          </el-form-item>
          <el-form-item label="考试时间" prop="exam_date">
            <el-date-picker v-model="form.exam_date" type="datetime" style="width: 100%" />
          </el-form-item>
          <el-form-item label="所属学期" prop="semester">
            <el-select v-model="form.semester" style="width: 100%">
              <el-option v-for="item in semesters" :key="item.id" :label="item.name" :value="item.name" />
            </el-select>
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="类型" prop="exam_type">
            <el-input v-model="form.exam_type" placeholder="期中考试、期末考试 或 其他平时分" />
          </el-form-item>
          <el-form-item label="考试时间" prop="exam_date">
            <el-date-picker v-model="form.exam_date" type="datetime" style="width: 100%" clearable />
          </el-form-item>
        </template>
      </el-form>

      <div v-else class="batch-entry-panel">
        <div class="batch-entry-summary">
          <div class="summary-item">
            <strong>类型：</strong>{{ form.exam_type }}
          </div>
          <div class="summary-item">
            <strong>考试时间：</strong>{{ formatDate(form.exam_date) }}
          </div>
          <div class="summary-item">
            <strong>课程：</strong>{{ selectedCourse?.name }}
          </div>
        </div>

        <el-alert
          title="输入一个成绩后按回车，会自动跳到下一个学生的成绩框。"
          type="info"
          :closable="false"
          class="batch-entry-alert"
        />

        <div class="batch-fill-tools">
          <el-input
            v-model="bulkScore"
            type="number"
            min="0"
            max="100"
            step="0.5"
            placeholder="输入统一分数"
            style="width: 180px"
          />
          <el-button @click="fillAllScores">一键录入</el-button>
        </div>

        <el-table :data="batchStudents" max-height="420">
          <el-table-column prop="student_name" label="学生姓名" min-width="180" />
          <el-table-column prop="student_no" label="学号" width="180" />
          <el-table-column label="成绩" width="180">
            <template #default="{ row, $index }">
              <el-input
                :ref="element => setScoreInputRef(element, $index)"
                v-model="row.score"
                type="number"
                min="0"
                max="100"
                step="0.5"
                placeholder="请输入成绩"
                @keydown.enter.prevent="focusNextScoreInput($index)"
              />
            </template>
          </el-table-column>
        </el-table>
      </div>

      <template #footer>
        <template v-if="editingScore">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
        </template>
        <template v-else-if="batchEntryStep === 1">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="goToBatchEntry">确认</el-button>
        </template>
        <template v-else>
          <el-button @click="batchEntryStep = 1">返回</el-button>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitBatchScores">提交成绩</el-button>
        </template>
      </template>
    </el-dialog>

    <el-dialog
      v-model="weightDialogVisible"
      title="各次考试占比（与作业、其他平时分之和为 100%）"
      width="640px"
      destroy-on-close
    >
      <el-alert
        type="info"
        :closable="false"
        class="mb-12"
        title="此处仅配置「各次考试」占比。作业平时分与其他平时分占比在「平时分占比」中设置。"
      />
      <div class="weight-dialog-tools">
        <el-button @click="addWeightRow">新增考试</el-button>
        <span class="weight-total">考试合计 {{ totalWeight }}%</span>
      </div>
      <el-table :data="weightForm.items" empty-text="请新增考试并填写占比">
        <el-table-column label="考试名称" min-width="220">
          <template #default="{ row }">
            <el-input v-model="row.exam_type" placeholder="例如：期中考试" />
          </template>
        </el-table-column>
        <el-table-column label="占比(%)" width="160">
          <template #default="{ row }">
            <el-input-number v-model="row.weight" :min="0" :max="100" :precision="2" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ $index }">
            <el-button type="danger" size="small" @click="removeWeightRow($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="weightDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingWeights" @click="saveWeights">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="schemeDialogVisible" title="平时分占比" width="480px" destroy-on-close>
      <el-form label-width="140px">
        <el-form-item label="作业平时分占比(%)">
          <el-input-number v-model="schemeForm.homework_weight" :min="0" :max="100" :precision="2" />
        </el-form-item>
        <el-form-item :label="`${OTHER_DAILY}占比(%)`">
          <el-input-number v-model="schemeForm.extra_daily_weight" :min="0" :max="100" :precision="2" />
        </el-form-item>
      </el-form>
      <p class="muted small">与下方「各次考试占比」之和须为 100%。</p>
      <template #footer>
        <el-button @click="schemeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingScheme" @click="saveScheme">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="appealDialogVisible" title="回复成绩申诉" width="560px" destroy-on-close>
      <el-input v-model="appealResolve.response" type="textarea" :rows="5" placeholder="教师回复" />
      <template #footer>
        <el-button @click="appealDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="appealResolve.loading" @click="submitAppealResolve">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'

const OTHER_DAILY = '其他平时分'

const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const weightDialogVisible = ref(false)
const schemeDialogVisible = ref(false)
const appealDialogVisible = ref(false)
const editingScore = ref(null)
const batchEntryStep = ref(1)
const formRef = ref(null)
const scoreInputRefs = ref([])
const savingWeights = ref(false)
const savingScheme = ref(false)
const bulkScore = ref('')

const scores = ref([])
const semesters = ref([])
const students = ref([])
const batchStudents = ref([])
const examWeights = ref([])
const filterSemester = ref('')
const gradeScheme = ref({ homework_weight: 30, extra_daily_weight: 20 })
const schemeForm = reactive({ homework_weight: 30, extra_daily_weight: 20 })
const compositionSemester = ref('')
const compositionLoading = ref(false)
const classCompositions = ref([])
const appeals = ref([])
const appealResolve = reactive({ appealId: null, response: '', loading: false })

const selectedCourse = computed(() => userStore.selectedCourse)

const form = reactive({
  student_id: null,
  score: 0,
  exam_type: '期中考试',
  exam_date: null,
  semester: ''
})

const weightForm = reactive({
  items: []
})

const rules = {
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  score: [{ required: true, message: '请输入成绩', trigger: 'blur' }],
  semester: [{ required: true, message: '请选择学期', trigger: 'change' }]
}

const batchRules = {
  exam_type: [{ required: true, message: '请输入类型', trigger: 'blur' }]
}

const averageScore = computed(() => {
  if (!scores.value.length) return 0
  return Number(
    (scores.value.reduce((sum, item) => sum + Number(item.score || 0), 0) / scores.value.length).toFixed(1)
  )
})

const maxScore = computed(() =>
  scores.value.length ? Math.max(...scores.value.map(item => Number(item.score || 0))) : 0
)
const passRate = computed(() => {
  if (!scores.value.length) return 0
  const passed = scores.value.filter(item => Number(item.score || 0) >= 60).length
  return Number(((passed / scores.value.length) * 100).toFixed(1))
})

const totalWeight = computed(() =>
  Number(weightForm.items.reduce((sum, item) => sum + Number(item.weight || 0), 0).toFixed(2))
)

const totalExamWeight = computed(() =>
  examWeights.value.reduce((s, item) => s + Number(item.weight || 0), 0)
)

const partsSum = computed(() =>
  Number(
    (
      Number(gradeScheme.value.homework_weight || 0) +
      Number(gradeScheme.value.extra_daily_weight || 0) +
      totalExamWeight.value
    ).toFixed(2)
  )
)

const partsSumValid = computed(() => partsSum.value === 100)

const loadSemesters = async () => {
  semesters.value = await api.semesters.list()
  if (!form.semester && semesters.value.length) {
    form.semester = semesters.value[0].name
  }
  if (!compositionSemester.value && semesters.value.length) {
    compositionSemester.value = semesters.value[0].name
  }
}

const loadStudents = async () => {
  if (!selectedCourse.value) {
    students.value = []
    return
  }
  students.value = await api.courses.getStudents(selectedCourse.value.id)
}

const loadWeights = async () => {
  if (!selectedCourse.value) {
    examWeights.value = []
    weightForm.items = []
    return
  }

  examWeights.value = await api.scores.getWeights(selectedCourse.value.id)
  weightForm.items = examWeights.value.map(item => ({
    exam_type: item.exam_type,
    weight: Number(item.weight)
  }))
}

const loadGradeScheme = async () => {
  if (!selectedCourse.value) {
    gradeScheme.value = { homework_weight: 30, extra_daily_weight: 20 }
    return
  }
  const s = await api.scores.getGradeScheme(selectedCourse.value.id)
  gradeScheme.value = {
    homework_weight: Number(s.homework_weight),
    extra_daily_weight: Number(s.extra_daily_weight)
  }
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

const loadClassCompositions = async () => {
  if (!selectedCourse.value || !compositionSemester.value) {
    classCompositions.value = []
    return
  }
  compositionLoading.value = true
  try {
    classCompositions.value = await api.scores.listClassComposition({
      subject_id: selectedCourse.value.id,
      semester: compositionSemester.value
    })
  } finally {
    compositionLoading.value = false
  }
}

const loadAppeals = async () => {
  if (!selectedCourse.value) {
    appeals.value = []
    return
  }
  appeals.value = await api.scores.listAppeals({ subject_id: selectedCourse.value.id })
}

const resetForm = () => {
  form.student_id = null
  form.score = 0
  form.exam_type = '期中考试'
  form.exam_date = null
  form.semester = semesters.value[0]?.name || ''
  batchStudents.value = []
  scoreInputRefs.value = []
  bulkScore.value = ''
  batchEntryStep.value = 1
}

const openCreateDialog = () => {
  editingScore.value = null
  resetForm()
  batchStudents.value = students.value.map(item => ({
    student_id: item.student_id,
    student_name: item.student_name,
    student_no: item.student_no,
    score: ''
  }))
  dialogVisible.value = true
}

const openWeightDialog = async () => {
  await loadWeights()
  weightDialogVisible.value = true
}

const openSchemeDialog = async () => {
  await loadGradeScheme()
  schemeForm.homework_weight = gradeScheme.value.homework_weight
  schemeForm.extra_daily_weight = gradeScheme.value.extra_daily_weight
  schemeDialogVisible.value = true
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

const setScoreInputRef = (element, index) => {
  scoreInputRefs.value[index] = element
}

const focusScoreInput = index => {
  const component = scoreInputRefs.value[index]
  const input = component?.input || component?.$el?.querySelector?.('input')
  input?.focus()
  input?.select?.()
}

const focusNextScoreInput = index => {
  const nextIndex = index + 1
  if (nextIndex < batchStudents.value.length) {
    focusScoreInput(nextIndex)
  }
}

const goToBatchEntry = async () => {
  await formRef.value.validate()
  batchEntryStep.value = 2
  await nextTick()
  focusScoreInput(0)
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
    await loadClassCompositions()
  } finally {
    submitting.value = false
  }
}

const submitBatchScores = async () => {
  const filledScores = batchStudents.value.filter(item => `${item.score}`.trim() !== '')

  if (!filledScores.length) {
    ElMessage.warning('请至少录入一名学生的成绩')
    return
  }

  const invalidStudent = filledScores.find(item => {
    const value = Number(item.score)
    return Number.isNaN(value) || value < 0 || value > 100
  })
  if (invalidStudent) {
    ElMessage.error(`请检查 ${invalidStudent.student_name} 的成绩，需在 0 到 100 之间`)
    return
  }

  submitting.value = true
  try {
    await api.scores.batchCreate({
      scores: filledScores.map(item => ({
        student_id: item.student_id,
        student_no: item.student_no,
        subject_id: selectedCourse.value.id,
        class_id: selectedCourse.value.class_id,
        score: Number(item.score),
        exam_type: form.exam_type,
        exam_date: form.exam_date,
        semester: form.semester
      }))
    })
    ElMessage.success('成绩已录入')
    dialogVisible.value = false
    await loadScores()
    await loadClassCompositions()
  } finally {
    submitting.value = false
  }
}

const fillAllScores = () => {
  const value = Number(bulkScore.value)
  if (Number.isNaN(value) || value < 0 || value > 100) {
    ElMessage.error('请输入 0 到 100 之间的分数')
    return
  }

  batchStudents.value = batchStudents.value.map(item => ({
    ...item,
    score: String(value)
  }))
  ElMessage.success('已为所有学生填入统一分数')
}

const addWeightRow = () => {
  weightForm.items.push({
    exam_type: '',
    weight: 0
  })
}

const removeWeightRow = index => {
  weightForm.items.splice(index, 1)
}

const saveWeights = async () => {
  if (!selectedCourse.value) {
    return
  }

  const normalizedItems = weightForm.items
    .map(item => ({
      exam_type: `${item.exam_type || ''}`.trim(),
      weight: Number(item.weight || 0)
    }))
    .filter(item => item.exam_type)

  if (!normalizedItems.length) {
    ElMessage.error('请至少配置一次考试占比')
    return
  }

  const examSum = Number(normalizedItems.reduce((sum, item) => sum + item.weight, 0).toFixed(2))
  const hw = Number(gradeScheme.value.homework_weight || 0)
  const ex = Number(gradeScheme.value.extra_daily_weight || 0)
  if (examSum + hw + ex > 100) {
    ElMessage.error('考试占比与平时分占比之和不能超过 100%，请下调考试或平时分占比')
    return
  }

  savingWeights.value = true
  try {
    examWeights.value = await api.scores.updateWeights(selectedCourse.value.id, {
      items: normalizedItems
    })
    weightForm.items = examWeights.value.map(item => ({
      exam_type: item.exam_type,
      weight: Number(item.weight)
    }))
    weightDialogVisible.value = false
    ElMessage.success('考试占比已保存')
    await loadClassCompositions()
  } finally {
    savingWeights.value = false
  }
}

const saveScheme = async () => {
  if (!selectedCourse.value) return
  savingScheme.value = true
  try {
    const s = await api.scores.updateGradeScheme(selectedCourse.value.id, {
      homework_weight: schemeForm.homework_weight,
      extra_daily_weight: schemeForm.extra_daily_weight
    })
    gradeScheme.value = {
      homework_weight: Number(s.homework_weight),
      extra_daily_weight: Number(s.extra_daily_weight)
    }
    schemeDialogVisible.value = false
    ElMessage.success('平时分占比已保存')
    await loadClassCompositions()
  } finally {
    savingScheme.value = false
  }
}

const deleteScore = async score => {
  try {
    await ElMessageBox.confirm(`确认删除 ${score.student_name} 的成绩记录吗？`, '删除成绩', { type: 'warning' })
    await api.scores.delete(score.id)
    ElMessage.success('成绩已删除')
    await loadScores()
    await loadClassCompositions()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除成绩失败', error)
    }
  }
}

const openAppealDialog = row => {
  appealResolve.appealId = row.id
  appealResolve.response = ''
  appealDialogVisible.value = true
}

const submitAppealResolve = async () => {
  if (!appealResolve.response.trim()) {
    ElMessage.warning('请填写回复')
    return
  }
  appealResolve.loading = true
  try {
    await api.scores.updateAppeal(appealResolve.appealId, {
      teacher_response: appealResolve.response.trim(),
      status: 'resolved'
    })
    ElMessage.success('已回复')
    appealDialogVisible.value = false
    await loadAppeals()
  } finally {
    appealResolve.loading = false
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
  await loadSemesters()
  await Promise.all([loadStudents(), loadScores(), loadWeights(), loadGradeScheme(), loadAppeals()])
  await loadClassCompositions()
})

watch(selectedCourse, async () => {
  await Promise.all([loadStudents(), loadScores(), loadWeights(), loadGradeScheme(), loadAppeals()])
  await loadClassCompositions()
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
  flex-wrap: wrap;
  gap: 12px;
}

.stats-card {
  margin-bottom: 20px;
}

.weights-card,
.totals-card,
.appeals-card {
  margin-bottom: 20px;
}

.scheme-hint {
  margin: 0 0 12px;
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
}

.scheme-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.scheme-sum {
  margin: 12px 0 0;
  font-size: 14px;
  color: #0f172a;
}

.scheme-sum.invalid {
  color: #b45309;
}

.toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.toolbar-inline {
  display: flex;
  gap: 8px;
}

.card-header-inline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.weight-total {
  color: #64748b;
  font-size: 14px;
}

.weight-dialog-tools {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.mb-12 {
  margin-bottom: 12px;
}

.muted {
  color: #94a3b8;
}

.small {
  font-size: 13px;
}

.batch-entry-panel {
  display: grid;
  gap: 16px;
}

.batch-entry-summary {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  padding: 14px 16px;
  background: #f8fafc;
  border-radius: 12px;
}

.summary-item {
  color: #475569;
}

.batch-entry-alert {
  margin-bottom: 4px;
}

.batch-fill-tools {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
