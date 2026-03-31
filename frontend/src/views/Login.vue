<template>
  <div class="login-container" :class="{ 'has-background': hasBackground }" :style="backgroundStyle">
    <div class="login-card">
      <div class="login-header">
        <div v-if="settings.system_logo" class="logo-container">
          <img :src="settings.system_logo" alt="Logo" class="system-logo" />
        </div>
        <h1 class="system-name">{{ settings.system_name }}</h1>
        <p class="system-desc">{{ settings.system_intro }}</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" class="login-form">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名 / Username"
            :prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码 / Password"
            :prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleLogin"
            class="login-btn"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        {{ settings.copyright }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'

import { normalizeSystemSettings } from '@/utils/branding'
import { useUserStore } from '@/stores/user'

const api = axios.create({ baseURL: '/api' })
const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const bingBackground = ref('')

const settings = ref({
  system_name: 'BIMSA-CLASS 大学生教学管理系统',
  system_logo: '',
  system_intro: '面向大学生的教学管理系统',
  login_background: '',
  copyright: '(c) 2026 BIMSA-CLASS',
  use_bing_background: true
})

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const backgroundStyle = computed(() => {
  if (settings.value.use_bing_background && bingBackground.value) {
    return {
      backgroundImage: `url(${bingBackground.value})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center'
    }
  }
  if (settings.value.login_background) {
    return {
      backgroundImage: `url(${settings.value.login_background})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center'
    }
  }
  return {}
})

const hasBackground = computed(() => {
  return (settings.value.use_bing_background && bingBackground.value) || settings.value.login_background
})

const fetchBingBackground = async () => {
  try {
    const res = await api.get('/bing-background')
    if (res.data.url) {
      bingBackground.value = res.data.url
    }
  } catch (error) {
    console.error('获取 Bing 背景失败', error)
  }
}

const fetchSettings = async () => {
  try {
    const res = await api.get('/settings/public')
    const normalizedSettings = normalizeSystemSettings(res.data)
    settings.value = normalizedSettings
    document.title = normalizedSettings?.system_name || 'BIMSA-CLASS 管理端'
  } catch (error) {
    console.error('获取系统设置失败', error)
  }
}

const handleLogin = async () => {
  await formRef.value.validate(async valid => {
    if (!valid) return

    loading.value = true
    try {
      const userData = await userStore.login(form.username, form.password)
      if (userData?.role === 'teacher' || userData?.role === 'class_teacher') {
        await userStore.ensureSelectedCourse(true)
      }
      ElMessage.success('登录成功')

      if (userData?.role === 'admin') {
        router.push('/students')
        return
      }

      if (userData?.role === 'teacher' || userData?.role === 'class_teacher') {
        router.push('/dashboard')
        return
      }

      router.push('/courses')
    } catch (error) {
      console.error(error)
      ElMessage.error('登录失败，请检查用户名和密码')
    } finally {
      loading.value = false
    }
  })
}

onMounted(async () => {
  await Promise.all([fetchSettings(), fetchBingBackground()])
})
</script>

<style scoped>
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 50%, #38bdf8 100%);
  position: relative;
  overflow: hidden;
}

.login-container.has-background {
  background-size: cover !important;
  background-position: center !important;
}

.login-container.has-background::before,
.login-container.has-background::after {
  display: none;
}

.login-container:not(.has-background)::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 80%, rgba(56, 189, 248, 0.28) 0%, transparent 48%),
    radial-gradient(circle at 80% 20%, rgba(96, 165, 250, 0.2) 0%, transparent 45%);
}

.login-card {
  width: 420px;
  padding: 40px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(16px);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.24);
  border: 1px solid rgba(255, 255, 255, 0.35);
  position: relative;
  z-index: 1;
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.logo-container {
  margin-bottom: 16px;
}

.system-logo {
  max-width: 200px;
  max-height: 60px;
}

.system-name {
  margin: 0 0 12px;
  font-size: 28px;
  color: #0f172a;
}

.system-desc {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.login-btn {
  width: 100%;
  height: 46px;
  border-radius: 14px;
}

.login-footer {
  margin-top: 16px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 768px) {
  .login-card {
    width: calc(100% - 32px);
    padding: 28px 22px;
  }
}
</style>
