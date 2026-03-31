<template>
  <div class="homework-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">作业管理</h1>
        <p class="page-subtitle">
          {{ selectedCourse ? `${selectedCourse.name} · ${selectedCourse.class_name || '未分配班级'}` : '请先选择课程后查看作业。' }}
        </p>
      </div>
      <div class="header-actions">
        <el-button v-if="userStore.isStudent" @click="router.push('/courses')">切换课程</el-button>
        <el-button v-if="!userStore.isStudent && selectedCourse" type="primary" @click="openCreateDialog">
          发布作业
        </el-button>
      </div>
    </div>

    <el-empty v-if="!selectedCourse" description="请先选择一门课程。" />

    <template v-else>
      <el-card shadow="never">
        <el-table :data="homeworks" v-loading="loading">
          <el-table-column prop="title" label="作业标题" min-width="200" />
          <el-table-column prop="subject_name" label="课程" width="160" />
          <el-table-column prop="due_date" label="截止时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.due_date) }}
            </template>
          </el-table-column>
          <el-table-column prop="creator_name" label="发布人" width="120" />
          <el-table-column prop="created_at" label="发布时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="viewHomework(row)">查看</el-button>
              <el-button
                v-if="!userStore.isStudent"
                size="small"
                type="danger"
                @click="deleteHomework(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-dialog v-model="dialogVisible" title="发布作业" width="620px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="作业标题" prop="title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="截止时间" prop="due_date">
          <el-date-picker
            v-model="form.due_date"
            type="datetime"
            placeholder="请选择截止时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="作业内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="作业详情" width="620px" destroy-on-close>
      <el-descriptions v-if="currentHomework" :column="2" border>
        <el-descriptions-item label="作业标题" :span="2">{{ currentHomework.title }}</el-descriptions-item>
        <el-descriptions-item label="课程">{{ currentHomework.subject_name || selectedCourse?.name }}</el-descriptions-item>
        <el-descriptions-item label="截止时间">{{ formatDate(currentHomework.due_date) }}</el-descriptions-item>
        <el-descriptions-item label="发布人">{{ currentHomework.creator_name }}</el-descriptions-item>
        <el-descriptions-item label="发布时间">{{ formatDate(currentHomework.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="作业内容" :span="2">{{ currentHomework.content || '暂无内容' }}</el-descriptions-item>
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
const currentHomework = ref(null)
const homeworks = ref([])
const formRef = ref(null)

const selectedCourse = computed(() => userStore.selectedCourse)

const form = reactive({
  title: '',
  content: '',
  due_date: null
})

const rules = {
  title: [{ required: true, message: '请输入作业标题', trigger: 'blur' }]
}

const buildParams = () => {
  if (!selectedCourse.value) {
    return {}
  }
  return {
    class_id: selectedCourse.value.class_id,
    subject_id: selectedCourse.value.id,
    page: 1,
    page_size: 200
  }
}

const loadHomeworks = async () => {
  if (!selectedCourse.value) {
    homeworks.value = []
    return
  }
  loading.value = true
  try {
    const result = await api.homework.list(buildParams())
    homeworks.value = result?.data || []
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  form.title = ''
  form.content = ''
  form.due_date = null
  dialogVisible.value = true
}

const submitForm = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    await api.homework.create({
      title: form.title,
      content: form.content,
      due_date: form.due_date,
      class_id: selectedCourse.value.class_id,
      subject_id: selectedCourse.value.id
    })
    ElMessage.success('作业已发布')
    dialogVisible.value = false
    await loadHomeworks()
  } finally {
    submitting.value = false
  }
}

const viewHomework = async row => {
  currentHomework.value = await api.homework.get(row.id)
  detailVisible.value = true
}

const deleteHomework = async row => {
  try {
    await ElMessageBox.confirm(`确认删除作业“${row.title}”吗？`, '删除作业', { type: 'warning' })
    await api.homework.delete(row.id)
    ElMessage.success('作业已删除')
    await loadHomeworks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除作业失败', error)
    }
  }
}

const formatDate = value => {
  if (!value) return '未设置'
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(() => {
  loadHomeworks()
})

watch(selectedCourse, () => {
  loadHomeworks()
})
</script>

<style scoped>
.homework-page {
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

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }
}
</style>
