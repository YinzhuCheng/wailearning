<template>
  <div class="students-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ pageTitle }}</h1>
        <p class="page-subtitle">{{ pageSubtitle }}</p>
      </div>
    </div>

    <el-empty
      v-if="showEmpty"
      :description="emptyText"
    />

    <template v-else>
      <el-alert
        v-if="showTeacherAlert"
        title="当前课程学生名单支持手动移除选课学生。"
        type="warning"
        :closable="false"
        class="info-alert"
      />

      <el-card shadow="never">
        <template #header>
          <div class="card-header-block">
            <div class="card-header">
              <div>
                <strong>{{ cardTitle }}</strong>
                <span class="header-count">共 {{ students.length }} 人</span>
              </div>

              <div v-if="isAdminView" class="card-actions">
                <el-button @click="downloadTemplate('xlsx')">Excel 模板</el-button>
                <el-button @click="downloadTemplate('csv')">CSV 模板</el-button>
                <el-button type="primary" :loading="importing" @click="triggerImport">
                  一键导入名单
                </el-button>
                <el-button @click="router.push('/students/new')">新增学生</el-button>
                <input
                  ref="fileInputRef"
                  class="hidden-file-input"
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  @change="handleFileChange"
                />
              </div>
            </div>

            <p v-if="isAdminView" class="import-tip">
              支持 Excel / CSV 文件，模板列为：姓名、性别、学号、所属班级。导入时若发现新班级，会自动在系统中创建。
            </p>
          </div>
        </template>

        <el-table :data="students" v-loading="loading || importing">
          <template v-if="isAdminView">
            <el-table-column prop="name" label="姓名" min-width="160" />
            <el-table-column label="性别" width="120">
              <template #default="{ row }">
                {{ genderText(row.gender) }}
              </template>
            </el-table-column>
            <el-table-column prop="student_no" label="学号" min-width="180" />
            <el-table-column label="所属班级" min-width="180">
              <template #default="{ row }">
                {{ row.class_name || '未分配班级' }}
              </template>
            </el-table-column>
            <el-table-column label="账号状态" width="120">
              <template #default="{ row }">
                <el-tag :type="row.has_user ? 'success' : 'info'">
                  {{ row.has_user ? '已生成' : '未生成' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="router.push(`/students/${row.id}/edit`)">
                  编辑
                </el-button>
                <el-button type="danger" size="small" @click="deleteStudent(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </template>

          <template v-else-if="isClassTeacherView">
            <el-table-column prop="name" label="姓名" min-width="140" />
            <el-table-column label="性别" width="100">
              <template #default="{ row }">
                {{ genderText(row.gender) }}
              </template>
            </el-table-column>
            <el-table-column prop="student_no" label="学号" min-width="160" />
            <el-table-column prop="class_name" label="班级" min-width="160" />
            <el-table-column prop="phone" label="联系电话" min-width="150" />
            <el-table-column prop="parent_phone" label="家长电话" min-width="150" />
            <el-table-column prop="address" label="家庭住址" min-width="220" show-overflow-tooltip />
          </template>

          <template v-else>
            <el-table-column prop="student_name" label="学生姓名" min-width="160" />
            <el-table-column prop="student_no" label="学号" width="160" />
            <el-table-column prop="class_name" label="所属班级" width="180" />
            <el-table-column label="选课方式" width="120">
              <template #default="{ row }">
                <el-select
                  v-if="canManageRoster"
                  :model-value="row.enrollment_type || 'required'"
                  size="small"
                  style="width: 100%"
                  @change="value => updateEnrollmentType(row, value)"
                >
                  <el-option label="必修" value="required" />
                  <el-option label="选修" value="elective" />
                </el-select>
                <el-tag v-else :type="(row.enrollment_type || 'required') === 'elective' ? 'warning' : 'success'">
                  {{ (row.enrollment_type || 'required') === 'elective' ? '选修' : '必修' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column v-if="canManageRoster" label="操作" width="140">
              <template #default="{ row }">
                <el-button type="danger" size="small" @click="removeStudent(row)">
                  移除
                </el-button>
              </template>
            </el-table-column>
          </template>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as XLSX from 'xlsx'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { resolveClassTeacherClassId, resolveClassTeacherClassName } from '@/utils/classTeacher'

const router = useRouter()
const userStore = useUserStore()

const TEMPLATE_HEADERS = ['姓名', '性别', '学号', '所属班级']
const TEMPLATE_ROWS = [
  {
    姓名: '张三',
    性别: '男',
    学号: '2026001',
    所属班级: '高一(1)班'
  }
]

const loading = ref(false)
const importing = ref(false)
const students = ref([])
const fileInputRef = ref(null)
const classTeacherCourses = ref([])

const selectedCourse = computed(() => userStore.selectedCourse)
const isAdminView = computed(() => userStore.isAdmin)
const isClassTeacherView = computed(() => userStore.isClassTeacher)
const canManageRoster = computed(() => userStore.canManageTeaching && !isAdminView.value && !isClassTeacherView.value)
const currentClassId = computed(() => resolveClassTeacherClassId(userStore.userInfo, classTeacherCourses.value))
const currentClassName = computed(() => resolveClassTeacherClassName(userStore.userInfo, classTeacherCourses.value) || '未分配班级')

const pageTitle = computed(() => {
  if (isClassTeacherView.value) {
    return '学生信息'
  }

  return isAdminView.value ? '学生管理' : '学生信息'
})

const pageSubtitle = computed(() => {
  if (isAdminView.value) {
    return '查看全校学生名单，并支持新增、编辑、删除和批量导入。'
  }

  if (isClassTeacherView.value) {
    return currentClassId.value ? `${currentClassName.value} 全部学生信息` : '请先为班主任账号分配班级。'
  }

  if (selectedCourse.value) {
    return `${selectedCourse.value.name} · ${selectedCourse.value.class_name || '未分配班级'}`
  }

  return '请先选择一门课程查看课程学生名单。'
})

const showEmpty = computed(() => {
  if (isAdminView.value) {
    return false
  }

  if (isClassTeacherView.value) {
    return !currentClassId.value
  }

  return !selectedCourse.value
})

const emptyText = computed(() => (isClassTeacherView.value ? '当前班主任账号没有绑定班级。' : '请先选择一门课程。'))
const showTeacherAlert = computed(() => !isAdminView.value && !isClassTeacherView.value && Boolean(selectedCourse.value))

const cardTitle = computed(() => {
  if (isAdminView.value) {
    return '全校学生名单'
  }

  if (isClassTeacherView.value) {
    return `${currentClassName.value} 学生名单`
  }

  return '课程学生名单'
})

const genderText = gender => {
  if (gender === 'male') {
    return '男'
  }
  if (gender === 'female') {
    return '女'
  }
  return '-'
}

const normalizeCellValue = value => {
  if (value === undefined || value === null) {
    return ''
  }
  return String(value).trim()
}

const normalizeRowKeys = row =>
  Object.fromEntries(
    Object.entries(row).map(([key, value]) => [
      String(key).replace(/^\uFEFF/, '').trim(),
      value
    ])
  )

const normalizeGenderInput = value => {
  const gender = normalizeCellValue(value).replace(/\s+/g, '').toLowerCase()
  const genderMap = {
    男: 'male',
    male: 'male',
    m: 'male',
    '1': 'male',
    女: 'female',
    female: 'female',
    f: 'female',
    '0': 'female'
  }
  return genderMap[gender] || ''
}

const resetFileInput = () => {
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

const triggerImport = () => {
  fileInputRef.value?.click()
}

const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.URL.revokeObjectURL(url)
}

const downloadTemplate = format => {
  const worksheet = XLSX.utils.json_to_sheet(TEMPLATE_ROWS, { header: TEMPLATE_HEADERS })

  if (format === 'csv') {
    const csv = XLSX.utils.sheet_to_csv(worksheet)
    downloadBlob(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8;' }), '学生导入模板.csv')
    return
  }

  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, '学生名单')
  XLSX.writeFile(workbook, '学生导入模板.xlsx')
}

const readWorkbook = async file => {
  const buffer = await file.arrayBuffer()
  const lowerName = file.name.toLowerCase()

  if (lowerName.endsWith('.csv')) {
    let content = new TextDecoder('utf-8').decode(buffer)

    if (content.includes('\uFFFD')) {
      try {
        content = new TextDecoder('gbk').decode(buffer)
      } catch (error) {
        console.warn('CSV GBK decode failed, fallback to UTF-8', error)
      }
    }

    return XLSX.read(content, { type: 'string' })
  }

  return XLSX.read(buffer, { type: 'array' })
}

const parseImportRows = rows => {
  const errors = []
  const payload = []

  rows.forEach((rawRow, index) => {
    const rowNumber = index + 2
    const row = normalizeRowKeys(rawRow)
    const name = normalizeCellValue(row.姓名 || row.学生姓名 || row.name)
    const gender = normalizeGenderInput(row.性别 || row.gender)
    const studentNo = normalizeCellValue(row.学号 || row.student_no || row.studentNo)
    const className = normalizeCellValue(row.所属班级 || row.班级 || row.class_name)

    const isEmptyRow = [name, studentNo, className, normalizeCellValue(row.性别 || row.gender)].every(
      value => !value
    )
    if (isEmptyRow) {
      return
    }

    if (!name) {
      errors.push(`第 ${rowNumber} 行缺少“姓名”`)
      return
    }

    if (!gender) {
      errors.push(`第 ${rowNumber} 行“性别”仅支持 男/女`)
      return
    }

    if (!studentNo) {
      errors.push(`第 ${rowNumber} 行缺少“学号”`)
      return
    }

    if (!className) {
      errors.push(`第 ${rowNumber} 行缺少“所属班级”`)
      return
    }

    payload.push({
      name,
      gender,
      student_no: studentNo,
      class_name: className
    })
  })

  return { errors, payload }
}

const loadAllStudents = async () => {
  const allStudents = []
  const pageSize = 1000
  let page = 1
  let total = 0

  do {
    const result = await api.students.list({ page, page_size: pageSize })
    const pageData = result?.data || []
    total = result?.total || pageData.length
    allStudents.push(...pageData)

    if (pageData.length < pageSize) {
      break
    }

    page += 1
  } while (allStudents.length < total)

  return allStudents
}

const ensureClassTeacherCourses = async () => {
  if (!isClassTeacherView.value) {
    return
  }

  classTeacherCourses.value = await userStore.fetchTeachingCourses(true)
}

const loadStudents = async () => {
  loading.value = true

  try {
    if (isAdminView.value) {
      students.value = await loadAllStudents()
      return
    }

    if (isClassTeacherView.value) {
      await ensureClassTeacherCourses()

      if (!currentClassId.value) {
        students.value = []
        return
      }

      const result = await api.students.list({
        class_id: currentClassId.value,
        page: 1,
        page_size: 1000
      })
      students.value = result?.data || []
      return
    }

    if (!selectedCourse.value) {
      students.value = []
      return
    }

    students.value = await api.courses.getStudents(selectedCourse.value.id)
  } catch (error) {
    console.error('加载学生数据失败', error)
    ElMessage.error('加载学生数据失败')
  } finally {
    loading.value = false
  }
}

const handleFileChange = async event => {
  const file = event.target.files?.[0]
  if (!file) {
    return
  }

  importing.value = true

  try {
    const workbook = await readWorkbook(file)
    const sheetName = workbook.SheetNames?.[0]
    if (!sheetName) {
      ElMessage.error('导入文件为空，请检查后重试')
      return
    }

    const worksheet = workbook.Sheets[sheetName]
    const matrix = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '', raw: false })
    const headers = (matrix[0] || []).map(cell => normalizeCellValue(cell).replace(/^\uFEFF/, ''))
    const missingHeaders = TEMPLATE_HEADERS.filter(header => !headers.includes(header))

    if (missingHeaders.length > 0) {
      ElMessage.error(`缺少模板列：${missingHeaders.join('、')}`)
      return
    }

    const rows = XLSX.utils.sheet_to_json(worksheet, { defval: '', raw: false })
    const { errors, payload } = parseImportRows(rows)

    if (errors.length > 0) {
      await ElMessageBox.alert(errors.slice(0, 10).join('\n'), '文件校验未通过', {
        confirmButtonText: '知道了'
      })
      return
    }

    if (!payload.length) {
      ElMessage.warning('文件中没有可导入的数据')
      return
    }

    const result = await api.students.batchCreate({ students: payload })
    const createdClasses = result?.created_classes || []
    const successCount = result?.success || 0
    const failedCount = result?.failed || 0

    if (successCount > 0) {
      const successParts = [`成功导入 ${successCount} 名学生`]
      if (createdClasses.length > 0) {
        successParts.push(`自动创建 ${createdClasses.length} 个班级`)
      }
      if (failedCount > 0) {
        successParts.push(`失败 ${failedCount} 条`)
      }
      ElMessage({
        type: failedCount > 0 ? 'warning' : 'success',
        message: successParts.join('，'),
        duration: 5000
      })
    }

    if (failedCount > 0) {
      const detailLines = [
        `成功：${successCount} 人`,
        `失败：${failedCount} 条`
      ]

      if (createdClasses.length > 0) {
        detailLines.push(`自动创建班级：${createdClasses.join('、')}`)
      }

      const errorLines = (result?.errors || []).slice(0, 10)
      if (errorLines.length > 0) {
        detailLines.push('')
        detailLines.push('失败明细：')
        detailLines.push(...errorLines)
      }

      await ElMessageBox.alert(detailLines.join('\n'), '导入结果', {
        confirmButtonText: '知道了'
      })
    }

    await loadStudents()
  } catch (error) {
    console.error('导入学生名单失败', error)
  } finally {
    importing.value = false
    resetFileInput()
  }
}

const deleteStudent = async student => {
  try {
    await ElMessageBox.confirm(
      `确认删除学生“${student.name}”吗？删除后会同步移除该学生的关联成绩、考勤和课程关联数据。`,
      '删除学生',
      { type: 'warning' }
    )
    await api.students.delete(student.id)
    ElMessage.success('学生已删除')
    await loadStudents()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除学生失败', error)
    }
  }
}

const removeStudent = async row => {
  try {
    await ElMessageBox.confirm(
      `确认将 ${row.student_name} 从 ${selectedCourse.value.name} 中移除吗？`,
      '移除学生',
      { type: 'warning' }
    )
    await api.courses.removeStudent(selectedCourse.value.id, row.student_id)
    ElMessage.success('学生已从课程中移除')
    await loadStudents()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('移除学生失败', error)
    }
  }
}

const updateEnrollmentType = async (row, value) => {
  if (!selectedCourse.value) {
    return
  }

  try {
    const updated = await api.courses.updateEnrollmentType(selectedCourse.value.id, row.student_id, {
      enrollment_type: value
    })
    const target = students.value.find(item => item.student_id === row.student_id)
    if (target) {
      Object.assign(target, updated)
    }
    ElMessage.success(`已切换为${value === 'elective' ? '选修' : '必修'}`)
  } catch (error) {
    console.error('更新选课方式失败', error)
    await loadStudents()
  }
}

onMounted(() => {
  loadStudents()
})

watch(
  () => [selectedCourse.value?.id, userStore.userInfo?.id],
  () => {
    loadStudents()
  }
)
</script>

<style scoped>
.students-page {
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

.info-alert {
  margin-bottom: 20px;
}

.card-header-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
}

.header-count {
  margin-left: 12px;
  color: #64748b;
}

.import-tip {
  margin: 0;
  color: #64748b;
  line-height: 1.6;
}

.hidden-file-input {
  display: none;
}

@media (max-width: 768px) {
  .page-header,
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }

  .card-actions {
    justify-content: stretch;
  }
}
</style>
