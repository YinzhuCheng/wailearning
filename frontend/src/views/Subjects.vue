<template>
  <div class="courses-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ pageTitle }}</h1>
        <p class="page-subtitle">{{ pageSubtitle }}</p>
      </div>
      <el-button v-if="showManageActions" type="primary" @click="openCreateDialog">
        新建课程
      </el-button>
    </div>

    <el-empty
      v-if="isClassTeacherView && !currentClassId"
      description="当前班主任账号没有绑定班级。"
    />

    <template v-else-if="isClassTeacherView">
      <el-card shadow="never">
        <el-table :data="classTeacherCourses" v-loading="loading">
          <el-table-column prop="name" label="课程名称" min-width="180" />
          <el-table-column prop="teacher_name" label="任课老师" width="160" />
          <el-table-column prop="class_name" label="班级" width="160" />
          <el-table-column label="课程类型" width="120">
            <template #default="{ row }">
              <el-tag :type="row.course_type === 'elective' ? 'warning' : 'success'">
                {{ row.course_type === 'elective' ? '选修课' : '必修课' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'info' : 'primary'">
                {{ row.status === 'completed' ? '已结课' : '进行中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="semester" label="学期" width="140" />
          <el-table-column label="课程时间" min-width="320">
            <template #default="{ row }">
              <div v-if="getCourseTimeLines(row).length" class="course-time-list">
                <div
                  v-for="(line, index) in getCourseTimeLines(row)"
                  :key="`${row.id}-${index}`"
                  class="course-time-line"
                >
                  {{ line }}
                </div>
              </div>
              <span v-else>未设置</span>
            </template>
          </el-table-column>
          <el-table-column prop="student_count" label="学生数" width="100" />
          <el-table-column label="操作" width="320" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="openCourseDetail(row)">
                课程详细
              </el-button>
              <el-button type="primary" size="small" @click="openEditDialogForRow(row)">
                编辑
              </el-button>
              <el-button type="success" size="small" @click="openLlmConfigDialog(row)">LLM 配置</el-button>
              <el-button v-if="userStore.isAdmin" type="danger" size="small" @click="deleteCourse(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-dialog
        v-model="courseDetailVisible"
        title="课程详细"
        width="880px"
        destroy-on-close
      >
        <div v-if="detailCourse" class="course-detail-meta">
          <div><strong>课程：</strong>{{ detailCourse.name }}</div>
          <div><strong>班级：</strong>{{ detailCourse.class_name || currentClassName }}</div>
          <div><strong>任课老师：</strong>{{ detailCourse.teacher_name || '未安排教师' }}</div>
        </div>

        <el-table :data="courseDetailRows" v-loading="courseDetailLoading">
          <el-table-column prop="student_name" label="学生姓名" min-width="150" />
          <el-table-column prop="student_no" label="学号" min-width="160" />
          <el-table-column prop="absence_count" label="缺勤次数" width="120" />
          <el-table-column prop="missing_homework_count" label="缺交次数" width="120" />
          <el-table-column prop="final_score_text" label="最终成绩" width="140" />
        </el-table>
      </el-dialog>
    </template>

    <template v-else>
      <el-card shadow="never">
        <el-table :data="courses" v-loading="loading">
          <el-table-column prop="name" label="课程名称" min-width="180" />
          <el-table-column prop="class_name" label="班级" width="160" />
          <el-table-column prop="teacher_name" label="任课老师" width="160" />
          <el-table-column label="课程类型" width="120">
            <template #default="{ row }">
              <el-tag :type="row.course_type === 'elective' ? 'warning' : 'success'">
                {{ row.course_type === 'elective' ? '选修课' : '必修课' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'info' : 'primary'">
                {{ row.status === 'completed' ? '已结课' : '进行中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="semester" label="学期" width="140" />
          <el-table-column label="课程时间" min-width="360">
            <template #default="{ row }">
              <div v-if="getCourseTimeLines(row).length" class="course-time-list">
                <div
                  v-for="(line, index) in getCourseTimeLines(row)"
                  :key="`${row.id}-${index}`"
                  class="course-time-line"
                >
                  {{ line }}
                </div>
              </div>
              <span v-else>未设置</span>
            </template>
          </el-table-column>
          <el-table-column prop="student_count" label="学生数" width="100" />
          <el-table-column prop="description" label="课程简介" min-width="220" show-overflow-tooltip />
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
              <el-button type="success" size="small" @click="openLlmConfigDialog(row)">LLM 配置</el-button>
              <el-button type="danger" size="small" @click="deleteCourse(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-dialog
        v-model="dialogVisible"
        :title="editingCourse ? '编辑课程' : '新建课程'"
        width="960px"
        destroy-on-close
      >
        <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
          <el-form-item label="课程名称" prop="name">
            <el-input v-model="form.name" />
          </el-form-item>
          <el-form-item label="所属班级" prop="class_id">
            <el-select v-model="form.class_id" placeholder="请选择班级" style="width: 100%">
              <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="任课老师" prop="teacher_id">
            <el-select v-model="form.teacher_id" placeholder="请选择任课老师" style="width: 100%" clearable>
              <el-option v-for="item in teachers" :key="item.id" :label="item.real_name" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="课程类型" prop="course_type">
            <el-radio-group v-model="form.course_type">
              <el-radio label="required">必修课</el-radio>
              <el-radio label="elective">选修课</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="课程状态" prop="status">
            <el-radio-group v-model="form.status">
              <el-radio label="active">进行中</el-radio>
              <el-radio label="completed">已结课</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="所属学期" prop="semester_id">
            <el-select v-model="form.semester_id" placeholder="请选择学期" style="width: 100%" clearable>
              <el-option v-for="item in semesters" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-form-item>

          <el-form-item label="课程时间" prop="course_times" class="course-times-form-item">
            <div class="course-times-editor">
              <div
                v-for="(courseTime, index) in form.course_times"
                :key="`course-time-${index}`"
                class="course-time-panel"
              >
                <div class="course-time-panel__header">
                  <div>
                    <div class="course-time-panel__title">课程时间 {{ index + 1 }}</div>
                    <div class="course-time-panel__subtitle">
                      设置这一段时间内的起始日期、结束日期和每周上课时间
                    </div>
                  </div>
                  <el-button
                    v-if="form.course_times.length > 1"
                    text
                    type="danger"
                    @click="removeCourseTime(index)"
                  >
                    删除
                  </el-button>
                </div>

                <div class="course-time-panel__fields">
                  <el-form-item :prop="`course_times.${index}.course_start_at`" label="开始日期" label-width="80px">
                    <el-date-picker
                      v-model="courseTime.course_start_at"
                      type="date"
                      placeholder="请选择开始日期"
                      style="width: 100%"
                      value-format="YYYY-MM-DD"
                    />
                  </el-form-item>

                  <el-form-item :prop="`course_times.${index}.course_end_at`" label="结束日期" label-width="80px">
                    <el-date-picker
                      v-model="courseTime.course_end_at"
                      type="date"
                      placeholder="请选择结束日期"
                      style="width: 100%"
                      value-format="YYYY-MM-DD"
                    />
                  </el-form-item>
                </div>

                <div class="course-time-panel__schedule">
                  <div class="course-time-panel__schedule-label">每周时间</div>
                  <CourseSchedulePicker v-model="courseTime.weekly_schedule" />
                </div>
              </div>

              <el-button plain class="course-times-editor__add" @click="addCourseTime">
                添加课程时间
              </el-button>
            </div>
          </el-form-item>

          <el-form-item label="课程简介" prop="description">
            <MarkdownEditorWithPreview
              v-model="form.description"
              :rows="5"
              field-label="课程简介"
              placeholder="支持 Markdown 与 LaTeX；保存前可预览。"
            />
          </el-form-item>

          <el-form-item label="课程封面">
            <el-upload :auto-upload="false" :show-file-list="false" accept="image/*" :on-change="handleCoverChange">
              <el-button>选择图片</el-button>
            </el-upload>
            <div v-if="coverObjectUrl" class="cover-preview">
              <img :src="coverObjectUrl" alt="封面预览" class="cover-preview__img" />
            </div>
            <div v-else-if="form.cover_image_url" class="cover-hint muted-text">已保存封面；选择新图片可替换。</div>
            <el-button v-if="coverObjectUrl || form.cover_image_url" link type="danger" @click="removeCover">
              移除封面
            </el-button>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
        </template>
      </el-dialog>

      <el-dialog
        v-model="llmDialogVisible"
        :title="llmDialogCourse ? `${llmDialogCourse.name} · LLM 配置` : 'LLM 配置'"
        width="960px"
        destroy-on-close
      >
        <el-form v-if="llmDialogCourse" :model="llmForm" label-width="140px" v-loading="llmLoading">
          <el-alert
            class="llm-notice"
            type="info"
            :closable="false"
            :title="llmVisualValidationNotice"
          />

          <el-form-item label="启用自动评分">
            <el-switch v-model="llmForm.is_enabled" />
          </el-form-item>

          <el-form-item label="响应语言">
            <el-input v-model="llmForm.response_language" placeholder="例如 zh-CN / en-US，可为空" />
          </el-form-item>

          <el-form-item label="学生日 token 限额">
            <el-input-number v-model="llmForm.daily_student_token_limit" :min="1" :step="1000" style="width: 100%" />
          </el-form-item>

          <el-form-item label="输入 token 上限">
            <el-input-number v-model="llmForm.max_input_tokens" :min="1000" :step="1000" style="width: 100%" />
          </el-form-item>

          <el-form-item label="输出 token 上限">
            <el-input-number v-model="llmForm.max_output_tokens" :min="1" :step="100" style="width: 100%" />
          </el-form-item>

          <el-form-item label="字符/token 估算">
            <el-input-number v-model="llmForm.estimated_chars_per_token" :min="0.5" :step="0.5" :precision="1" style="width: 100%" />
          </el-form-item>

          <el-form-item label="单图 token 估算">
            <el-input-number v-model="llmForm.estimated_image_tokens" :min="1" :step="100" style="width: 100%" />
          </el-form-item>

          <el-form-item label="额度时区">
            <el-input v-model="llmForm.quota_timezone" placeholder="例如 UTC / Asia/Shanghai" />
          </el-form-item>

          <el-form-item label="系统提示词">
            <el-input v-model="llmForm.system_prompt" type="textarea" :rows="5" placeholder="可选。若为空则使用系统默认提示词。" />
          </el-form-item>

          <el-form-item label="教师提示词（自动评分 / 助教）">
            <el-input
              v-model="llmForm.teacher_prompt"
              type="textarea"
              :rows="5"
              placeholder="可选。说明自动评分尺度、风格，以及智能助教回答时的偏好；勿在此写入应对学生保密的细则。"
            />
          </el-form-item>

          <el-form-item label="路由策略">
            <el-radio-group v-model="llmRoutingMode">
              <el-radio label="flat">单列表优先级（按顺序故障转移）</el-radio>
              <el-radio label="groups">多组故障转移（整组失败后切换下一组）</el-radio>
            </el-radio-group>
            <div class="llm-route-hint">与课程绑定；任课教师与管理员均可修改。保存时以当前选项为准。</div>
          </el-form-item>

          <template v-if="llmRoutingMode === 'flat'">
            <el-form-item label="端点顺序">
              <div class="llm-endpoints">
                <el-empty v-if="!llmPresets.length" description="暂无可用端点，请先由管理员创建并完成视觉校验。" />
                <div
                  v-for="preset in llmPresets"
                  :key="preset.id"
                  class="llm-endpoint-row"
                >
                  <el-checkbox
                    :model-value="isPresetSelected(preset.id)"
                    :disabled="preset.validation_status !== 'validated' || !preset.supports_vision"
                    @change="checked => togglePresetSelection(preset, checked)"
                  >
                    <div class="llm-endpoint-meta">
                      <strong>{{ preset.name }}</strong>
                      <span>{{ preset.model_name }}</span>
                      <span>状态：{{ preset.validation_status === 'validated' ? '已通过视觉校验' : preset.validation_message || '未校验' }}</span>
                    </div>
                  </el-checkbox>

                  <el-input-number
                    v-if="isPresetSelected(preset.id)"
                    :model-value="getPresetPriority(preset.id)"
                    :min="1"
                    @update:model-value="value => updatePresetPriority(preset.id, value)"
                  />
                </div>
              </div>
            </el-form-item>
          </template>

          <template v-else>
            <el-form-item label="多组端点">
              <div
                v-for="(grp, gi) in llmGroupsUi"
                :key="grp._key"
                class="llm-group-panel"
              >
                <div class="llm-group-panel__head">
                  <span class="llm-group-panel__title">故障转移组 {{ gi + 1 }}</span>
                  <el-input v-model="grp.name" placeholder="组名称（可选）" style="width: 220px" clearable />
                  <el-button v-if="llmGroupsUi.length > 1" text type="danger" @click="removeLlmGroup(gi)">删除组</el-button>
                </div>
                <div class="llm-endpoints">
                  <div
                    v-for="preset in llmPresets"
                    :key="`${grp._key}-${preset.id}`"
                    class="llm-endpoint-row"
                  >
                    <el-checkbox
                      :model-value="isPresetInGroup(gi, preset.id)"
                      :disabled="preset.validation_status !== 'validated' || !preset.supports_vision"
                      @change="checked => togglePresetInGroup(gi, preset, checked)"
                    >
                      <div class="llm-endpoint-meta">
                        <strong>{{ preset.name }}</strong>
                        <span>{{ preset.model_name }}</span>
                        <span>状态：{{ preset.validation_status === 'validated' ? '已通过视觉校验' : preset.validation_message || '未校验' }}</span>
                      </div>
                    </el-checkbox>
                    <el-input-number
                      v-if="isPresetInGroup(gi, preset.id)"
                      :model-value="getGroupPresetPriority(gi, preset.id)"
                      :min="1"
                      @update:model-value="value => setGroupPresetPriority(gi, preset.id, value)"
                    />
                  </div>
                </div>
              </div>
              <el-button type="primary" plain class="llm-add-group" @click="addLlmGroup">添加组</el-button>
            </el-form-item>
          </template>
        </el-form>

        <template #footer>
          <el-button @click="llmDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="llmSaving" @click="saveLlmConfig">保存配置</el-button>
        </template>
      </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import CourseSchedulePicker from '@/components/CourseSchedulePicker.vue'
import MarkdownEditorWithPreview from '@/components/MarkdownEditorWithPreview.vue'
import { useUserStore } from '@/stores/user'
import { validateAttachmentFile } from '@/utils/attachments'
import {
  filterCoursesByClassId,
  resolveClassTeacherClassId,
  resolveClassTeacherClassName
} from '@/utils/classTeacher'
import { loadAllPages } from '@/utils/pagedFetch'
import { parseScheduleValue } from '@/utils/courseSchedule'
import {
  createEmptyCourseTime,
  formatCourseTimeEntry,
  normalizeEditableCourseTimes,
  serializeCourseTimesPayload
} from '@/utils/courseTimes'

const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const editingCourse = ref(null)
const formRef = ref(null)
const coverFile = ref(null)
const coverObjectUrl = ref('')

const resetCover = () => {
  if (coverObjectUrl.value) {
    URL.revokeObjectURL(coverObjectUrl.value)
    coverObjectUrl.value = ''
  }
  coverFile.value = null
}

const handleCoverChange = uploadFile => {
  const file = uploadFile.raw
  const result = validateAttachmentFile(file)
  if (!result.valid) {
    ElMessage.error(result.message)
    return false
  }
  if (!file.type.startsWith('image/')) {
    ElMessage.error('封面请使用图片文件')
    return false
  }
  resetCover()
  coverFile.value = file
  coverObjectUrl.value = URL.createObjectURL(file)
  return false
}

const removeCover = () => {
  resetCover()
  form.cover_image_url = ''
}

const courseDetailVisible = ref(false)
const courseDetailLoading = ref(false)
const detailCourse = ref(null)
const llmDialogVisible = ref(false)
const llmDialogCourse = ref(null)
const llmLoading = ref(false)
const llmSaving = ref(false)
const llmPresets = ref([])
const llmVisualValidationNotice = ref('LLM 连通性验证会同时校验视觉接口。只有通过视觉能力校验的端点，才能被加入课程配置并用于作业自动评分。')

const courses = ref([])
const classes = ref([])
const teachers = ref([])
const semesters = ref([])
const classTeacherCoursePool = ref([])
const courseDetailRows = ref([])

const llmForm = reactive({
  is_enabled: false,
  response_language: '',
  daily_student_token_limit: null,
  estimated_chars_per_token: 4.0,
  estimated_image_tokens: 850,
  max_input_tokens: 16000,
  max_output_tokens: 1200,
  quota_timezone: 'UTC',
  system_prompt: '',
  teacher_prompt: '',
  endpoints: []
})

const llmRoutingMode = ref('flat')
const llmGroupsUi = ref([])

const emptyLlmGroup = () => ({
  _key: `g-${Date.now()}-${Math.random()}`,
  name: '',
  presetPriorities: {}
})

const isClassTeacherView = computed(() => userStore.isClassTeacher)
const currentClassId = computed(() => resolveClassTeacherClassId(userStore.userInfo, classTeacherCoursePool.value))
const currentClassName = computed(() => resolveClassTeacherClassName(userStore.userInfo, classTeacherCoursePool.value) || '未分配班级')
const classTeacherCourses = computed(() => filterCoursesByClassId(classTeacherCoursePool.value, currentClassId.value))
const showManageActions = computed(() => !isClassTeacherView.value)

const pageTitle = computed(() => (isClassTeacherView.value ? '课程信息' : '课程管理'))
const pageSubtitle = computed(() => {
  if (isClassTeacherView.value) {
    return currentClassId.value ? `${currentClassName.value} 全部课程信息` : '请先为班主任账号分配班级。'
  }

  return '管理员与任课教师可管理课程信息、课程封面、以及课程级 LLM 配置；班主任可在本班课程列表中执行相同管理操作（删除课程仅管理员）。'
})

const form = reactive({
  name: '',
  class_id: null,
  teacher_id: null,
  semester_id: null,
  course_type: 'required',
  status: 'active',
  course_times: [createEmptyCourseTime()],
  description: '',
  cover_image_url: ''
})

const validateCourseTimes = (_rule, value, callback) => {
  if (!Array.isArray(value) || !value.length) {
    callback(new Error('请至少添加一组课程时间'))
    return
  }

  for (const item of value) {
    if (!item.course_start_at || !item.course_end_at) {
      callback(new Error('请为每组课程时间选择开始日期和结束日期'))
      return
    }

    if (new Date(item.course_end_at) < new Date(item.course_start_at)) {
      callback(new Error('课程时间的结束日期不能早于开始日期'))
      return
    }

    if (!parseScheduleValue(item.weekly_schedule).length) {
      callback(new Error('请为每组课程时间选择每周时间'))
      return
    }
  }

  callback()
}

const rules = {
  name: [{ required: true, message: '请输入课程名称', trigger: 'blur' }],
  class_id: [{ required: true, message: '请选择所属班级', trigger: 'change' }],
  course_type: [{ required: true, message: '请选择课程类型', trigger: 'change' }],
  status: [{ required: true, message: '请选择课程状态', trigger: 'change' }],
  course_times: [{ validator: validateCourseTimes, trigger: 'change' }]
}

const resetForm = () => {
  resetCover()
  Object.assign(form, {
    name: '',
    class_id: null,
    teacher_id: null,
    semester_id: null,
    course_type: 'required',
    status: 'active',
    course_times: [createEmptyCourseTime()],
    description: '',
    cover_image_url: ''
  })
}

const loadCourses = async () => {
  loading.value = true
  try {
    if (isClassTeacherView.value) {
      classTeacherCoursePool.value = await userStore.fetchTeachingCourses(true)
      return
    }

    courses.value = await api.subjects.list()
  } finally {
    loading.value = false
  }
}

const loadOptions = async () => {
  const [classData, userData, semesterData] = await Promise.all([
    api.classes.list(),
    api.users.list(),
    api.semesters.list()
  ])
  classes.value = classData || []
  teachers.value = (userData || []).filter(item => ['teacher', 'class_teacher'].includes(item.role))
  semesters.value = semesterData || []
}

const addCourseTime = () => {
  form.course_times.push(createEmptyCourseTime())
  formRef.value?.clearValidate('course_times')
}

const removeCourseTime = index => {
  if (form.course_times.length <= 1) {
    return
  }

  form.course_times.splice(index, 1)
  formRef.value?.clearValidate('course_times')
}

const openCreateDialog = () => {
  editingCourse.value = null
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = course => {
  editingCourse.value = course
  resetCover()
  const normalizedCourseTimes = normalizeEditableCourseTimes(course)

  Object.assign(form, {
    name: course.name,
    class_id: course.class_id,
    teacher_id: course.teacher_id,
    semester_id: course.semester_id ?? null,
    course_type: course.course_type || 'required',
    status: course.status || 'active',
    course_times: normalizedCourseTimes.length ? normalizedCourseTimes : [createEmptyCourseTime()],
    description: course.description || '',
    cover_image_url: course.cover_image_url || ''
  })
  dialogVisible.value = true
}

const openEditDialogForRow = async row => {
  await loadOptions()
  openEditDialog(row)
}

const getCourseTimeLines = course =>
  normalizeEditableCourseTimes(course)
    .map(formatCourseTimeEntry)
    .filter(Boolean)

const submitForm = async () => {
  await formRef.value.validate()
  submitting.value = true

  try {
    if (coverFile.value) {
      const uploaded = await api.files.upload(coverFile.value)
      form.cover_image_url = uploaded.attachment_url
      resetCover()
    }

    const payload = {
      name: form.name,
      class_id: form.class_id,
      teacher_id: form.teacher_id,
      semester_id: form.semester_id || null,
      course_type: form.course_type,
      status: form.status,
      course_times: serializeCourseTimesPayload(form.course_times),
      description: form.description,
      cover_image_url: form.cover_image_url?.trim() || null
    }

    if (editingCourse.value) {
      await api.subjects.update(editingCourse.value.id, payload)
      ElMessage.success('课程已更新')
    } else {
      await api.subjects.create(payload)
      ElMessage.success('课程已创建')
    }

    dialogVisible.value = false
    await loadCourses()
  } finally {
    submitting.value = false
  }
}

const resetLlmForm = () => {
  llmRoutingMode.value = 'flat'
  llmGroupsUi.value = [emptyLlmGroup()]
  Object.assign(llmForm, {
    is_enabled: false,
    response_language: '',
    daily_student_token_limit: null,
    estimated_chars_per_token: 4.0,
    estimated_image_tokens: 850,
    max_input_tokens: 16000,
    max_output_tokens: 1200,
    quota_timezone: 'UTC',
    system_prompt: '',
    teacher_prompt: '',
    endpoints: []
  })
}

const normalizeNullableNumber = value => value || null

const applyLlmConfig = config => {
  resetLlmForm()
  if (!config) {
    return
  }
  llmVisualValidationNotice.value = config.visual_validation_notice || llmVisualValidationNotice.value
  llmForm.is_enabled = Boolean(config.is_enabled)
  llmForm.response_language = config.response_language || ''
  llmForm.daily_student_token_limit = config.daily_student_token_limit || null
  llmForm.estimated_chars_per_token = config.estimated_chars_per_token ?? 4.0
  llmForm.estimated_image_tokens = config.estimated_image_tokens ?? 850
  llmForm.max_input_tokens = config.max_input_tokens ?? 16000
  llmForm.max_output_tokens = config.max_output_tokens ?? 1200
  llmForm.quota_timezone = config.quota_timezone || 'UTC'
  llmForm.system_prompt = config.system_prompt || ''
  llmForm.teacher_prompt = config.teacher_prompt || ''
  const gr = config.groups || []
  const hasGroupMembers = gr.some(g => (g.members || []).length > 0)
  if (hasGroupMembers) {
    llmRoutingMode.value = 'groups'
    llmGroupsUi.value = gr.map(g => ({
      _key: `g-${g.id}-${Math.random()}`,
      name: g.name || '',
      presetPriorities: Object.fromEntries((g.members || []).map(m => [m.preset_id, m.priority]))
    }))
    llmForm.endpoints = []
  } else {
    llmRoutingMode.value = 'flat'
    llmForm.endpoints = (config.endpoints || []).map(item => ({
      preset_id: item.preset_id,
      priority: item.priority
    }))
    llmGroupsUi.value = [emptyLlmGroup()]
  }
}

const openLlmConfigDialog = async course => {
  llmDialogCourse.value = course
  llmDialogVisible.value = true
  llmLoading.value = true
  try {
    const [presets, config] = await Promise.all([
      api.llmSettings.listPresets(),
      api.llmSettings.getCourseConfig(course.id)
    ])
    llmPresets.value = presets || []
    applyLlmConfig(config)
  } finally {
    llmLoading.value = false
  }
}

const isPresetSelected = presetId =>
  llmForm.endpoints.some(item => String(item.preset_id) === String(presetId))

const getPresetPriority = presetId =>
  llmForm.endpoints.find(item => String(item.preset_id) === String(presetId))?.priority || 1

const togglePresetSelection = (preset, checked) => {
  const existingIndex = llmForm.endpoints.findIndex(item => String(item.preset_id) === String(preset.id))
  if (!checked && existingIndex >= 0) {
    llmForm.endpoints.splice(existingIndex, 1)
    return
  }
  if (checked && existingIndex < 0) {
    llmForm.endpoints.push({
      preset_id: preset.id,
      priority: llmForm.endpoints.length + 1
    })
  }
}

const updatePresetPriority = (presetId, value) => {
  const target = llmForm.endpoints.find(item => String(item.preset_id) === String(presetId))
  if (!target) {
    return
  }
  target.priority = value || 1
}

const addLlmGroup = () => {
  llmGroupsUi.value.push(emptyLlmGroup())
}

const removeLlmGroup = index => {
  if (llmGroupsUi.value.length <= 1) {
    return
  }
  llmGroupsUi.value.splice(index, 1)
}

const isPresetInGroup = (groupIndex, presetId) => {
  const g = llmGroupsUi.value[groupIndex]
  if (!g) {
    return false
  }
  return Object.prototype.hasOwnProperty.call(g.presetPriorities, presetId)
}

const togglePresetInGroup = (groupIndex, preset, checked) => {
  const g = llmGroupsUi.value[groupIndex]
  if (!g || preset.validation_status !== 'validated' || !preset.supports_vision) {
    return
  }
  if (checked) {
    const vals = Object.values(g.presetPriorities)
    const maxP = vals.length ? Math.max(...vals) : 0
    g.presetPriorities[preset.id] = maxP + 1
  } else {
    delete g.presetPriorities[preset.id]
  }
}

const getGroupPresetPriority = (groupIndex, presetId) =>
  llmGroupsUi.value[groupIndex]?.presetPriorities?.[presetId] ?? 1

const setGroupPresetPriority = (groupIndex, presetId, value) => {
  const g = llmGroupsUi.value[groupIndex]
  if (g && Object.prototype.hasOwnProperty.call(g.presetPriorities, presetId)) {
    g.presetPriorities[presetId] = value || 1
  }
}

const saveLlmConfig = async () => {
  if (!llmDialogCourse.value) {
    return
  }
  llmSaving.value = true
  try {
    const base = {
      is_enabled: llmForm.is_enabled,
      response_language: llmForm.response_language?.trim() || null,
      daily_student_token_limit: normalizeNullableNumber(llmForm.daily_student_token_limit),
      estimated_chars_per_token: llmForm.estimated_chars_per_token,
      estimated_image_tokens: llmForm.estimated_image_tokens,
      max_input_tokens: llmForm.max_input_tokens,
      max_output_tokens: llmForm.max_output_tokens,
      quota_timezone: llmForm.quota_timezone?.trim() || 'UTC',
      system_prompt: llmForm.system_prompt?.trim() || null,
      teacher_prompt: llmForm.teacher_prompt?.trim() || null
    }
    if (llmRoutingMode.value === 'groups') {
      const groupsPayload = llmGroupsUi.value
        .map((g, gi) => {
          const ids = Object.keys(g.presetPriorities).map(Number)
          const members = ids
            .sort((a, b) => (g.presetPriorities[a] || 99) - (g.presetPriorities[b] || 99))
            .map((pid, idx) => ({ preset_id: pid, priority: idx + 1 }))
          return {
            priority: gi + 1,
            name: (g.name || '').trim() || `group ${gi + 1}`,
            members
          }
        })
        .filter(g => g.members.length > 0)
      if (!groupsPayload.length) {
        ElMessage.warning('多组模式下请至少在一个组内勾选一个已校验端点')
        return
      }
      await api.llmSettings.updateCourseConfig(llmDialogCourse.value.id, {
        ...base,
        groups: groupsPayload,
        endpoints: []
      })
    } else {
      await api.llmSettings.updateCourseConfig(llmDialogCourse.value.id, {
        ...base,
        endpoints: [...llmForm.endpoints].sort((left, right) => left.priority - right.priority),
        groups: []
      })
    }
    ElMessage.success('LLM 配置已保存')
    llmDialogVisible.value = false
  } finally {
    llmSaving.value = false
  }
}

const deleteCourse = async course => {
  try {
    await ElMessageBox.confirm(`确认删除课程“${course.name}”吗？`, '删除课程', { type: 'warning' })
    await api.subjects.delete(course.id)
    ElMessage.success('课程已删除')
    await loadCourses()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除课程失败', error)
    }
  }
}

const normalizeExamTypeKey = examType => `${examType || ''}`.trim().toLowerCase()

const average = values => {
  if (!values.length) {
    return null
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

const buildFinalScoreMap = (scores, weights) => {
  const scoreMap = new Map()
  const weightMap = new Map(
    (weights || []).map(item => [normalizeExamTypeKey(item.exam_type), Number(item.weight || 0)])
  )

  ;(scores || []).forEach(score => {
    const studentId = Number(score.student_id)
    const examTypeKey = normalizeExamTypeKey(score.exam_type)
    const numericScore = Number(score.score)

    if (!scoreMap.has(studentId)) {
      scoreMap.set(studentId, new Map())
    }

    if (!scoreMap.get(studentId).has(examTypeKey)) {
      scoreMap.get(studentId).set(examTypeKey, [])
    }

    scoreMap.get(studentId).get(examTypeKey).push(numericScore)
  })

  const finalScoreMap = new Map()

  scoreMap.forEach((examMap, studentId) => {
    let weightedTotal = 0
    let coveredWeight = 0
    const allScores = []

    examMap.forEach((values, examTypeKey) => {
      const examAverage = average(values)
      allScores.push(...values)

      const weight = weightMap.get(examTypeKey)
      if (weight && examAverage !== null) {
        weightedTotal += (examAverage * weight) / 100
        coveredWeight += weight
      }
    })

    let finalScore = null

    if (weightMap.size > 0 && coveredWeight > 0) {
      finalScore = weightedTotal / (coveredWeight / 100)
    } else {
      finalScore = average(allScores)
    }

    finalScoreMap.set(studentId, finalScore)
  })

  return finalScoreMap
}

const formatFinalScore = value => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '暂无'
  }

  const numeric = Number(value)
  return Number.isInteger(numeric) ? `${numeric}` : numeric.toFixed(1)
}

const openCourseDetail = async course => {
  detailCourse.value = course
  courseDetailVisible.value = true
  courseDetailLoading.value = true

  try {
    const [studentsResult, attendanceResult, scoresResult, weightResult, homeworkRows] = await Promise.all([
      api.subjects.getStudents(course.id),
      api.attendance.list({
        class_id: course.class_id,
        subject_id: course.id,
        page: 1,
        page_size: 1000
      }),
      api.scores.list({
        class_id: course.class_id,
        subject_id: course.id,
        page: 1,
        page_size: 1000
      }),
      api.scores.getWeights(course.id).catch(() => []),
      loadAllPages(params => api.homework.list({
        ...params,
        class_id: course.class_id,
        subject_id: course.id
      }))
    ])

    const submissionResults = await Promise.all(
      homeworkRows.map(homework => api.homework.getSubmissions(homework.id))
    )

    const absenceCountMap = new Map()
    ;(attendanceResult?.data || []).forEach(item => {
      if (item.status === 'absent') {
        const studentId = Number(item.student_id)
        absenceCountMap.set(studentId, (absenceCountMap.get(studentId) || 0) + 1)
      }
    })

    const missingHomeworkMap = new Map()
    submissionResults.forEach(result => {
      ;(result?.data || []).forEach(item => {
        if (item.status !== 'submitted') {
          const studentId = Number(item.student_id)
          missingHomeworkMap.set(studentId, (missingHomeworkMap.get(studentId) || 0) + 1)
        }
      })
    })

    const finalScoreMap = buildFinalScoreMap(scoresResult?.data || [], weightResult || [])

    courseDetailRows.value = (studentsResult || []).map(student => ({
      student_id: student.student_id,
      student_name: student.student_name,
      student_no: student.student_no,
      absence_count: absenceCountMap.get(Number(student.student_id)) || 0,
      missing_homework_count: missingHomeworkMap.get(Number(student.student_id)) || 0,
      final_score_text: formatFinalScore(finalScoreMap.get(Number(student.student_id)))
    }))
  } finally {
    courseDetailLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadCourses(), loadOptions()])
})

watch(
  () => userStore.userInfo?.id,
  async () => {
    await Promise.all([loadCourses(), loadOptions()])
  }
)
</script>

<style scoped>
.courses-page {
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

.course-detail-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
  color: #334155;
}

.course-time-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.course-time-line {
  line-height: 1.6;
  color: #334155;
}

.course-times-editor {
  display: flex;
  width: 100%;
  flex-direction: column;
  gap: 16px;
}

.course-times-editor__add {
  align-self: flex-start;
}

.llm-notice {
  margin-bottom: 18px;
}

.llm-endpoints {
  display: flex;
  width: 100%;
  flex-direction: column;
  gap: 12px;
}

.llm-endpoint-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 14px;
  border: 1px solid #dbe4f0;
  border-radius: 14px;
  background: #f8fbff;
}

.llm-endpoint-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.llm-endpoint-meta span {
  font-size: 12px;
  color: #64748b;
}

.course-time-panel {
  border: 1px solid #dbe4f0;
  border-radius: 18px;
  background: #f8fbff;
  padding: 18px;
}

.course-time-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.course-time-panel__title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.course-time-panel__subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: #64748b;
}

.course-time-panel__fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.course-time-panel__fields :deep(.el-form-item) {
  margin-bottom: 0;
}

.course-time-panel__schedule {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.course-time-panel__schedule-label {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

@media (max-width: 900px) {
  .course-detail-meta,
  .page-header,
  .course-time-panel__header {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .course-time-panel__fields {
    grid-template-columns: 1fr;
  }
}

.cover-preview {
  margin-top: 10px;
}

.cover-preview__img {
  max-height: 140px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.cover-hint {
  margin-top: 8px;
  font-size: 13px;
  color: #64748b;
}

.llm-route-hint {
  margin: 6px 0 14px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.llm-group-panel {
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid #dbe4f0;
  border-radius: 14px;
  background: #f8fbff;
}

.llm-group-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.llm-group-panel__title {
  font-weight: 600;
  color: #0f172a;
}
</style>
