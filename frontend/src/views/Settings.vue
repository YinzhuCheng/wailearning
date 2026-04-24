<template>
  <div class="settings-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span><el-icon><Setting /></el-icon> 系统设置</span>
        </div>
      </template>

      <el-form :model="form" label-width="120px" v-loading="loading">
        <el-form-item label="系统名称">
          <el-input v-model="form.system_name" placeholder="请输入系统名称" />
        </el-form-item>

        <el-form-item label="系统简介">
          <el-input v-model="form.system_intro" type="textarea" :rows="3" placeholder="请输入系统简介" />
        </el-form-item>

        <el-form-item label="系统 Logo">
          <div class="logo-upload">
            <el-input v-model="form.system_logo" placeholder="请输入 Logo 图片 URL">
              <template #append>
                <el-button @click="openImageDialog('system_logo')">上传</el-button>
              </template>
            </el-input>
            <div v-if="form.system_logo" class="logo-preview">
              <img :src="form.system_logo" alt="Logo" />
            </div>
            <div class="field-tip">支持在线图片 URL，建议尺寸 200x60。</div>
          </div>
        </el-form-item>

        <el-form-item label="Bing 每日一图">
          <div class="switch-group">
            <el-switch v-model="form.use_bing_background" active-text="启用" inactive-text="禁用" />
            <div class="field-tip">启用后，登录页面将自动使用 Bing 每日一图作为背景。</div>
          </div>
        </el-form-item>

        <el-form-item label="登录背景图">
          <div class="background-upload">
            <el-input v-model="form.login_background" placeholder="请输入背景图片URL" :disabled="form.use_bing_background">
              <template #append>
                <el-button :disabled="form.use_bing_background" @click="openImageDialog('login_background')">上传</el-button>
              </template>
            </el-input>
            <div v-if="form.login_background && !form.use_bing_background" class="background-preview">
              <img :src="form.login_background" alt="背景图" />
            </div>
            <div class="field-tip">
              {{ form.use_bing_background ? '已启用 Bing 每日一图，自定义背景将被忽略。' : '支持在线图片 URL，建议尺寸 1920x1080。' }}
            </div>
          </div>
        </el-form-item>

        <el-form-item label="版权信息">
          <el-input v-model="form.copyright" placeholder="请输入版权信息" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="saveSettings">
            <el-icon><Select /></el-icon> 保存设置
          </el-button>
          <el-button @click="resetSettings">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="preview-card">
      <template #header>
        <span><el-icon><View /></el-icon> 登录页面预览</span>
      </template>
      <div class="login-preview">
        <div class="preview-background" :style="backgroundStyle">
          <div class="preview-login-box">
            <div v-if="form.system_logo" class="preview-logo">
              <img :src="form.system_logo" alt="Logo" />
            </div>
            <h2 class="preview-title">{{ form.system_name }}</h2>
            <p class="preview-intro">{{ form.system_intro }}</p>
            <el-input placeholder="用户名" disabled />
            <el-input placeholder="密码" type="password" disabled style="margin-top: 10px" />
            <el-button type="primary" style="width: 100%; margin-top: 15px" disabled>登录</el-button>
          </div>
          <div class="preview-footer">{{ form.copyright }}</div>
        </div>
      </div>
    </el-card>

    <el-card class="preview-card">
      <template #header>
        <div class="card-header card-header--space">
          <span><el-icon><Connection /></el-icon> LLM 端点预设</span>
          <el-button type="primary" @click="openPresetDialog()">新增端点</el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        class="llm-notice"
        title="连通性会依次测试：先纯文本，再使用你上传的测试图做多模态校验（服务端将图片规范为 PNG + base64）。通过视觉能力校验的端点，才可被教师配置到课程中并用于带图作业自动评分。"
      />

      <el-table :data="presets" v-loading="presetsLoading">
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="model_name" label="模型" min-width="180" />
        <el-table-column prop="base_url" label="Base URL" min-width="220" show-overflow-tooltip />
        <el-table-column label="文本" width="110">
          <template #default="{ row }">
            <el-tag :type="presetStepTagType(row.text_validation_status)" size="small">
              {{ presetStepLabel(row.text_validation_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="视觉" width="110">
          <template #default="{ row }">
            <el-tag :type="presetStepTagType(row.vision_validation_status)" size="small">
              {{ presetStepLabel(row.vision_validation_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="总状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.validation_status === 'validated' ? 'success' : row.validation_status === 'failed' ? 'danger' : 'info'">
              {{ row.validation_status === 'validated' ? '已通过' : row.validation_status === 'failed' ? '失败' : '未校验' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="详情" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            {{ formatPresetDetail(row) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openPresetDialog(row)">编辑</el-button>
            <el-button size="small" :loading="row.validating" @click="openValidateDialog(row)">校验</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="preview-card">
      <template #header>
        <span><el-icon><Setting /></el-icon> LLM 用量与额度（全平台）</span>
      </template>
      <el-alert
        type="info"
        :closable="false"
        class="llm-notice"
        title="学生个人日 token 为全课共用同一池；统计日与「额度时区」由下方全局策略决定。并发数为同时处理的自动评分任务数上限。"
      />
      <el-form v-loading="llmQuotaLoading" label-width="200px" style="max-width: 640px">
        <el-form-item label="默认每人每日 token">
          <el-input-number v-model="llmQuotaForm.default_daily_student_tokens" :min="1" :step="10000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="并发评分任务数">
          <el-input-number v-model="llmQuotaForm.max_parallel_grading_tasks" :min="1" :max="64" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="额度统计时区">
          <el-input v-model="llmQuotaForm.quota_timezone" placeholder="例如 Asia/Shanghai" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="llmQuotaSaving" @click="saveLlmQuotaPolicy">保存全局策略</el-button>
        </el-form-item>
      </el-form>
      <el-divider />
      <p class="field-tip" style="margin-bottom: 12px">批量覆盖个人日限额（写入后优先生效；可清除恢复为默认）</p>
      <el-form label-width="200px" style="max-width: 640px">
        <el-form-item label="范围">
          <el-select v-model="bulkQuotaForm.scope" style="width: 100%">
            <el-option label="全校所有学生" value="all" />
            <el-option label="指定班级" value="class" />
            <el-option label="指定课程选课学生" value="subject" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="bulkQuotaForm.scope === 'class'" label="班级 ID">
          <el-input-number v-model="bulkQuotaForm.class_id" :min="1" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item v-if="bulkQuotaForm.scope === 'subject'" label="课程 ID">
          <el-input-number v-model="bulkQuotaForm.subject_id" :min="1" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="每人每日 token">
          <el-input-number v-model="bulkQuotaForm.daily_tokens" :min="1" :step="1000" style="width: 100%" :disabled="bulkQuotaForm.clear_override" />
        </el-form-item>
        <el-form-item label="清除个人覆盖">
          <el-switch v-model="bulkQuotaForm.clear_override" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="bulkQuotaLoading" @click="applyBulkQuotaOverrides">应用</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog v-model="uploadDialogVisible" title="上传图片" width="500px">
      <el-form>
        <el-form-item label="图片URL">
          <el-input v-model="imageUrl" placeholder="请输入图片URL" />
        </el-form-item>
        <el-form-item label="或上传文件">
          <el-upload
            class="upload-demo"
            drag
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            accept="image/*"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽图片到此处或<em>点击上传</em></div>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpload">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="validateDialogVisible" title="端点连通性校验" width="480px" destroy-on-close>
      <p class="validate-hint">
        请先选一张本地图片（JPEG/PNG/WebP 等，建议小于 5MB）用于多模态测试。校验顺序：纯文本 → 带图请求。
      </p>
      <el-upload
        :auto-upload="false"
        :limit="1"
        accept="image/*,.jpg,.jpeg,.png,.gif,.webp,.bmp"
        :on-change="onValidateFileChange"
        :on-exceed="() => ElMessage.warning('只需选择一张图片')"
      >
        <el-button type="primary">选择测试图</el-button>
        <template #tip>
          <div v-if="validateFileName" class="validate-file-name">已选：{{ validateFileName }}</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="validateDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="validateDialogLoading" @click="runValidate">开始校验</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="presetDialogVisible" :title="editingPresetId ? '编辑 LLM 端点' : '新增 LLM 端点'" width="620px" destroy-on-close>
      <el-form :model="presetForm" label-width="130px">
        <el-form-item label="预设名称">
          <el-input v-model="presetForm.name" placeholder="例如 OpenAI Vision 主端点" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="presetForm.base_url" placeholder="例如 https://api.example.com/v1/" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="presetForm.api_key" type="password" show-password placeholder="仅服务端保存，不会下发浏览器" />
        </el-form-item>
        <el-form-item label="模型名">
          <el-input v-model="presetForm.model_name" placeholder="例如 gpt-4.1-mini" />
        </el-form-item>
        <el-form-item label="连接超时（秒）">
          <el-input-number v-model="presetForm.connect_timeout_seconds" :min="1" :max="300" style="width: 100%" />
        </el-form-item>
        <el-form-item label="读取超时（秒）">
          <el-input-number v-model="presetForm.read_timeout_seconds" :min="1" :max="600" style="width: 100%" />
        </el-form-item>
        <el-form-item label="重试次数">
          <el-input-number v-model="presetForm.max_retries" :min="0" :max="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="初始退避（秒）">
          <el-input-number v-model="presetForm.initial_backoff_seconds" :min="1" :max="120" style="width: 100%" />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="presetForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="presetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="presetSaving" @click="savePreset">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Refresh, Select, Setting, UploadFilled, View } from '@element-plus/icons-vue'
import { normalizeBrandingText } from '@/utils/branding'
import { http } from '@/api'
import api from '@/api'

/** Axios errors carry response; thrown sync errors (e.g. ReferenceError) do not. */
const formatApiError = error => {
  const detail = error?.response?.data?.detail
  if (detail == null) {
    return error?.message || '未知错误'
  }
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map(item => (typeof item === 'object' && item != null ? item.msg || JSON.stringify(item) : String(item)))
      .filter(Boolean)
    return parts.length ? parts.join('；') : '请求参数无效'
  }
  if (typeof detail === 'object' && detail.msg) {
    return detail.msg
  }
  return String(detail)
}

const loading = ref(false)
const saving = ref(false)
const uploadDialogVisible = ref(false)
const imageUrl = ref('')
const currentUploadField = ref('')
const presets = ref([])
const presetsLoading = ref(false)
const presetDialogVisible = ref(false)
const presetSaving = ref(false)
const editingPresetId = ref(null)
const validateDialogVisible = ref(false)
const validateDialogLoading = ref(false)
const validateRow = ref(null)
const validateFile = ref(null)
const validateFileName = ref('')

const llmQuotaLoading = ref(false)
const llmQuotaSaving = ref(false)
const llmQuotaForm = reactive({
  default_daily_student_tokens: 100000,
  quota_timezone: 'Asia/Shanghai',
  max_parallel_grading_tasks: 3
})
const bulkQuotaLoading = ref(false)
const bulkQuotaForm = reactive({
  scope: 'all',
  class_id: null,
  subject_id: null,
  daily_tokens: 100000,
  clear_override: false
})

const form = ref({
  system_name: 'BIMSA-CLASS 大学生教学管理系统',
  login_background: '',
  system_logo: '',
  system_intro: '面向大学生的教学管理系统',
  copyright: '(c) 2026 BIMSA-CLASS',
  use_bing_background: true
})

const presetForm = reactive({
  name: '',
  base_url: '',
  api_key: '',
  model_name: '',
  connect_timeout_seconds: 10,
  read_timeout_seconds: 120,
  max_retries: 2,
  initial_backoff_seconds: 2,
  is_active: true
})

const originalForm = ref({})

const backgroundStyle = computed(() => {
  if (form.value.login_background) {
    return {
      backgroundImage: `url(${form.value.login_background})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center'
    }
  }
  return {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  }
})

const fetchSettings = async () => {
  loading.value = true
  try {
    const rows = await http.get('/settings/all')
    const settingsData = {}
    rows.forEach(item => {
      settingsData[item.setting_key] = ['system_name', 'copyright'].includes(item.setting_key)
        ? normalizeBrandingText(item.setting_value)
        : item.setting_value
    })
    form.value = {
      system_name: settingsData.system_name || 'BIMSA-CLASS 大学生教学管理系统',
      login_background: settingsData.login_background || '',
      system_logo: settingsData.system_logo || '',
      system_intro: settingsData.system_intro || '面向大学生的教学管理系统',
      copyright: settingsData.copyright || '(c) 2026 BIMSA-CLASS',
      use_bing_background: settingsData.use_bing_background === 'true'
    }
    originalForm.value = { ...form.value }
  } catch (error) {
    ElMessage.error('获取设置失败')
  } finally {
    loading.value = false
  }
}

const fetchLlmQuotaPolicy = async () => {
  llmQuotaLoading.value = true
  try {
    const row = await api.llmSettings.getGlobalQuotaPolicy()
    llmQuotaForm.default_daily_student_tokens = row.default_daily_student_tokens ?? 100000
    llmQuotaForm.quota_timezone = row.quota_timezone || 'Asia/Shanghai'
    llmQuotaForm.max_parallel_grading_tasks = row.max_parallel_grading_tasks ?? 3
  } catch (error) {
    ElMessage.error(`获取 LLM 额度策略失败：${formatApiError(error)}`)
  } finally {
    llmQuotaLoading.value = false
  }
}

const saveLlmQuotaPolicy = async () => {
  llmQuotaSaving.value = true
  try {
    await api.llmSettings.updateGlobalQuotaPolicy({
      default_daily_student_tokens: llmQuotaForm.default_daily_student_tokens,
      quota_timezone: (llmQuotaForm.quota_timezone || 'Asia/Shanghai').trim(),
      max_parallel_grading_tasks: llmQuotaForm.max_parallel_grading_tasks
    })
    ElMessage.success('LLM 全局额度策略已保存')
    await fetchLlmQuotaPolicy()
  } catch (error) {
    ElMessage.error(`保存失败：${formatApiError(error)}`)
  } finally {
    llmQuotaSaving.value = false
  }
}

const applyBulkQuotaOverrides = async () => {
  bulkQuotaLoading.value = true
  try {
    const body = {
      scope: bulkQuotaForm.scope,
      clear_override: bulkQuotaForm.clear_override
    }
    if (bulkQuotaForm.scope === 'class') {
      body.class_id = bulkQuotaForm.class_id
    }
    if (bulkQuotaForm.scope === 'subject') {
      body.subject_id = bulkQuotaForm.subject_id
    }
    if (!bulkQuotaForm.clear_override) {
      body.daily_tokens = bulkQuotaForm.daily_tokens
    }
    const res = await api.llmSettings.bulkQuotaOverrides(body)
    ElMessage.success(`已处理，影响学生约 ${res.affected_students} 人（含无变更的 0）`)
  } catch (error) {
    ElMessage.error(`批量设置失败：${formatApiError(error)}`)
  } finally {
    bulkQuotaLoading.value = false
  }
}

const fetchPresets = async () => {
  presetsLoading.value = true
  try {
    const data = await http.get('/llm-settings/presets')
    presets.value = (Array.isArray(data) ? data : []).map(item => ({
      ...item,
      validating: false
    }))
  } catch (error) {
    ElMessage.error('获取 LLM 端点失败')
  } finally {
    presetsLoading.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    await http.post('/settings/batch-update', form.value)
    ElMessage.success('设置保存成功')
    originalForm.value = { ...form.value }
  } catch (error) {
    ElMessage.error(`保存失败：${formatApiError(error)}`)
  } finally {
    saving.value = false
  }
}

const resetSettings = () => {
  form.value = { ...originalForm.value }
}

const openImageDialog = fieldName => {
  currentUploadField.value = fieldName
  imageUrl.value = form.value[fieldName]
  uploadDialogVisible.value = true
}

const handleFileChange = file => {
  const reader = new FileReader()
  reader.onload = event => {
    imageUrl.value = event.target.result
  }
  reader.readAsDataURL(file.raw)
}

const confirmUpload = () => {
  if (!imageUrl.value) {
    ElMessage.warning('请输入图片 URL 或上传图片')
    return
  }
  form.value[currentUploadField.value] = imageUrl.value
  uploadDialogVisible.value = false
  ElMessage.success('图片已添加')
}

const resetPresetForm = () => {
  editingPresetId.value = null
  Object.assign(presetForm, {
    name: '',
    base_url: 'https://yunwu.ai/v1',
    api_key: '',
    model_name: 'gpt-5.4',
    connect_timeout_seconds: 30,
    read_timeout_seconds: 180,
    max_retries: 3,
    initial_backoff_seconds: 5,
    is_active: true
  })
}

const openPresetDialog = preset => {
  resetPresetForm()
  if (preset) {
    editingPresetId.value = preset.id
    Object.assign(presetForm, {
      name: preset.name,
      base_url: preset.base_url,
      api_key: '',
      model_name: preset.model_name,
      connect_timeout_seconds: preset.connect_timeout_seconds,
      read_timeout_seconds: preset.read_timeout_seconds,
      max_retries: preset.max_retries,
      initial_backoff_seconds: preset.initial_backoff_seconds,
      is_active: preset.is_active
    })
  }
  presetDialogVisible.value = true
}

const buildPresetPayload = () => ({
  name: presetForm.name.trim(),
  base_url: presetForm.base_url.trim(),
  api_key: presetForm.api_key.trim(),
  model_name: presetForm.model_name.trim(),
  connect_timeout_seconds: presetForm.connect_timeout_seconds,
  read_timeout_seconds: presetForm.read_timeout_seconds,
  max_retries: presetForm.max_retries,
  initial_backoff_seconds: presetForm.initial_backoff_seconds,
  is_active: presetForm.is_active
})

const savePreset = async () => {
  if (!presetForm.name.trim() || !presetForm.base_url.trim() || !presetForm.model_name.trim()) {
    ElMessage.warning('请完整填写端点名称、Base URL 和模型名')
    return
  }
  presetSaving.value = true
  try {
    const payload = buildPresetPayload()
    if (editingPresetId.value) {
      if (!payload.api_key) {
        delete payload.api_key
      }
      await http.put(`/llm-settings/presets/${editingPresetId.value}`, payload)
      ElMessage.success('端点预设已更新')
    } else {
      await http.post('/llm-settings/presets', payload)
      ElMessage.success('端点预设已创建')
    }
    presetDialogVisible.value = false
    await fetchPresets()
  } catch (error) {
    ElMessage.error(`保存端点失败：${formatApiError(error)}`)
  } finally {
    presetSaving.value = false
  }
}

const presetStepLabel = s => {
  if (s === 'passed') return '通过'
  if (s === 'failed') return '失败'
  if (s === 'skipped') return '跳过'
  return '—'
}

const presetStepTagType = s => {
  if (s === 'passed') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'skipped') return 'info'
  return 'info'
}

const formatPresetDetail = row => {
  const parts = []
  if (row.text_validation_message) {
    parts.push(`文本：${row.text_validation_message}`)
  }
  if (row.vision_validation_message) {
    parts.push(`视觉：${row.vision_validation_message}`)
  }
  if (parts.length) {
    return parts.join('；')
  }
  return row.validation_message || '尚未执行连通性校验。请点击「校验」并上传测试图。'
}

const openValidateDialog = row => {
  validateRow.value = row
  validateFile.value = null
  validateFileName.value = ''
  validateDialogVisible.value = true
}

const onValidateFileChange = upload => {
  const raw = upload?.raw
  if (!raw) {
    return
  }
  validateFile.value = raw
  validateFileName.value = raw.name || 'image'
}

const runValidate = async () => {
  if (!validateRow.value) {
    return
  }
  if (!validateFile.value) {
    ElMessage.warning('请选择一张用于多模态测试的本地图片')
    return
  }
  const row = presets.value.find(p => p.id === validateRow.value.id) || validateRow.value
  validateDialogLoading.value = true
  row.validating = true
  try {
    await api.llmSettings.validatePreset(row.id, validateFile.value)
    ElMessage.success('端点校验已完成')
    validateDialogVisible.value = false
    await fetchPresets()
  } catch (error) {
    ElMessage.error(`端点校验失败：${formatApiError(error)}`)
  } finally {
    validateDialogLoading.value = false
    row.validating = false
  }
}

onMounted(() => {
  fetchSettings()
  fetchPresets()
  fetchLlmQuotaPolicy()
})
</script>

<style scoped>
.settings-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
}

.card-header--space {
  justify-content: space-between;
}

.logo-upload,
.background-upload {
  width: 100%;
}

.logo-preview,
.background-preview {
  margin-top: 15px;
}

.logo-preview img {
  max-width: 200px;
  max-height: 60px;
}

.background-preview img {
  max-width: 400px;
  max-height: 200px;
  border-radius: 8px;
}

.field-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.switch-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-card {
  margin-top: 20px;
}

.login-preview {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
}

.preview-background {
  width: 100%;
  height: 400px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
}

.preview-login-box {
  background: rgba(255, 255, 255, 0.95);
  padding: 40px;
  border-radius: 12px;
  width: 350px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.preview-logo {
  margin-bottom: 20px;
}

.preview-logo img {
  max-width: 200px;
  max-height: 60px;
}

.preview-title {
  margin: 10px 0;
  color: #333;
}

.preview-intro {
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
}

.preview-footer {
  position: absolute;
  bottom: 20px;
  color: #fff;
  font-size: 12px;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.llm-notice {
  margin-bottom: 16px;
}

@media (max-width: 768px) {
  .card-header--space {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
