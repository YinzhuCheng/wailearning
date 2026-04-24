<template>
  <div class="student-form-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ isEdit ? '编辑学生' : '新增学生' }}</h1>
        <p class="page-subtitle">
          {{ isEdit ? '修改学生信息并保存到学生管理列表。' : '手动新增一名学生并关联到对应班级。' }}
        </p>
      </div>
      <el-button @click="router.push('/students')">返回学生管理</el-button>
    </div>

    <el-card shadow="never" v-loading="loading">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px" class="student-form">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" maxlength="30" show-word-limit />
        </el-form-item>

        <el-form-item label="性别" prop="gender">
          <el-radio-group v-model="form.gender">
            <el-radio value="male">男</el-radio>
            <el-radio value="female">女</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="学号" prop="student_no">
          <el-input v-model="form.student_no" maxlength="40" />
        </el-form-item>

        <el-form-item label="所属班级" prop="class_id">
          <el-select
            v-model="form.class_id"
            placeholder="请选择班级"
            style="width: 100%"
            :disabled="isEdit && !isAdmin"
          >
            <el-option
              v-for="item in classes"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="手机号">
          <el-input v-model="form.phone" maxlength="20" />
        </el-form-item>

        <el-form-item label="家长电话">
          <el-input v-model="form.parent_phone" maxlength="20" />
        </el-form-item>

        <el-form-item label="家庭住址">
          <el-input v-model="form.address" type="textarea" :rows="3" maxlength="200" show-word-limit />
        </el-form-item>

        <el-form-item class="form-actions">
          <el-button @click="router.push('/students')">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitForm">
            {{ isEdit ? '保存修改' : '创建学生' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const formRef = ref(null)
const loading = ref(false)
const submitting = ref(false)
const classes = ref([])

const form = reactive({
  name: '',
  gender: 'male',
  student_no: '',
  class_id: null,
  phone: '',
  parent_phone: '',
  address: ''
})

const isEdit = computed(() => Boolean(route.params.id))

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  student_no: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  class_id: [{ required: true, message: '请选择班级', trigger: 'change' }]
}

const fillForm = student => {
  form.name = student?.name || ''
  form.gender = student?.gender || 'male'
  form.student_no = student?.student_no || ''
  form.class_id = student?.class_id ?? null
  form.phone = student?.phone || ''
  form.parent_phone = student?.parent_phone || ''
  form.address = student?.address || ''
}

const loadClasses = async () => {
  classes.value = await api.classes.list()
}

const loadStudent = async () => {
  if (!isEdit.value) {
    return
  }

  const student = await api.students.get(route.params.id)
  fillForm(student)
}

const submitForm = async () => {
  await formRef.value.validate()

  submitting.value = true
  try {
    const payload = {
      name: form.name,
      gender: form.gender,
      student_no: form.student_no,
      class_id: form.class_id,
      phone: form.phone || null,
      parent_phone: form.parent_phone || null,
      address: form.address || null
    }

    if (isEdit.value) {
      const updatePayload = isAdmin.value
        ? payload
        : {
            name: payload.name,
            gender: payload.gender,
            student_no: payload.student_no,
            phone: payload.phone,
            parent_phone: payload.parent_phone,
            address: payload.address
          }
      await api.students.update(route.params.id, updatePayload)
      ElMessage.success('学生信息已更新')
    } else {
      await api.students.create(payload)
      ElMessage.success('学生已创建')
    }

    router.push('/students')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await loadClasses()
    await loadStudent()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.student-form-page {
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

.student-form {
  max-width: 760px;
}

.form-actions :deep(.el-form-item__content) {
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }

  .student-form {
    max-width: 100%;
  }
}
</style>
