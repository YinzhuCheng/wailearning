<template>
  <el-card shadow="never" class="discussion-card">
    <template #header>
      <div class="discussion-head">
        <span>讨论区</span>
        <el-text v-if="canUseDiscussion" type="info" size="small">
          实名讨论，每页 {{ effectivePageSize }} 条回复
        </el-text>
      </div>
    </template>

    <el-alert
      v-if="!canUseDiscussion"
      type="warning"
      :closable="false"
      title="该条目未关联课程，无法在课程实例下讨论。请从课程内打开或联系管理员关联课程与班级。"
      show-icon
    />

    <template v-else>
      <div v-loading="loading" class="discussion-body">
        <div v-if="!entries.length && !loading" class="muted-text">暂无讨论，发表第一条回复吧。</div>
        <div v-for="row in entries" :key="row.id" class="discussion-row">
          <div class="discussion-row__meta">
            <span class="discussion-row__name">{{ displayAuthorName(row) }}</span>
            <el-tag v-if="row.message_kind === 'llm_assistant'" type="success" size="small" effect="plain">
              智能助教
            </el-tag>
            <el-tag v-else size="small" effect="plain">{{ roleLabel(row.author_role) }}</el-tag>
            <el-tag v-if="row.llm_invocation" type="warning" size="small" effect="plain">调用智能助教</el-tag>
            <span class="discussion-row__time">{{ formatTime(row.created_at) }}</span>
          </div>
          <div class="discussion-row__body">{{ row.body }}</div>
          <div v-if="canDelete(row)" class="discussion-row__actions">
            <el-button type="danger" link size="small" @click="removeEntry(row)">删除</el-button>
          </div>
        </div>

        <el-pagination
          v-if="total > effectivePageSize"
          v-model:current-page="page"
          class="discussion-pager"
          :page-size="effectivePageSize"
          :total="total"
          layout="total, prev, pager, next"
          small
          @current-change="loadList"
        />

        <div v-if="isStudent" class="discussion-llm-bar">
          <el-button size="small" :type="llmMode ? 'primary' : 'default'" plain @click="toggleLlmMode">
            请 LLM 回复
          </el-button>
          <el-text v-if="llmMode" type="info" size="small">
            将附带「@LLM」并消耗你的课程 LLM 额度；输出长度由教师在课程 LLM 设置中的 max_output_tokens 控制。
          </el-text>
        </div>
        <el-input
          v-model="draft"
          type="textarea"
          :rows="3"
          maxlength="8000"
          show-word-limit
          :placeholder="inputPlaceholder"
          class="discussion-input"
        />
        <el-button type="primary" :loading="posting" :disabled="!draft.trim()" @click="submit">
          {{ llmMode ? '发送（调用智能助教）' : '发表回复' }}
        </el-button>
      </div>
    </template>
  </el-card>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  targetType: {
    type: String,
    required: true,
    validator: v => v === 'homework' || v === 'material'
  },
  targetId: { type: Number, required: true },
  /** When set, used for API scope (course instance). */
  subjectId: { type: Number, default: null },
  classId: { type: Number, default: null },
  /** Backend hint: homework/material not linked to a subject. */
  discussionRequiresContext: { type: Boolean, default: false },
  /** Student UI: show "请 LLM 回复" and allow invoke_llm. Teachers post plain comments only. */
  isStudent: { type: Boolean, default: false }
})

const userStore = useUserStore()

const selectedCourse = computed(() => userStore.selectedCourse)

const resolvedSubjectId = computed(() => {
  if (props.subjectId != null && props.subjectId !== '') return Number(props.subjectId)
  const c = selectedCourse.value
  return c?.id != null ? Number(c.id) : null
})

const resolvedClassId = computed(() => {
  if (props.classId != null && props.classId !== '') return Number(props.classId)
  const c = selectedCourse.value
  return c?.class_id != null ? Number(c.class_id) : null
})

const canUseDiscussion = computed(() => {
  if (props.discussionRequiresContext) return false
  return resolvedSubjectId.value != null && resolvedClassId.value != null
})

const effectivePageSize = computed(() => {
  const raw = userStore.userInfo?.discussion_page_size
  const n = raw != null ? Number(raw) : 10
  if (Number.isFinite(n) && n >= 5 && n <= 50) return n
  return 10
})

const loading = ref(false)
const posting = ref(false)
const page = ref(1)
const total = ref(0)
const entries = ref([])
const draft = ref('')
const llmMode = ref(false)

let pollTimer = null
let pollAbort = null

const inputPlaceholder = computed(() => {
  if (llmMode.value) {
    return '首行已自动包含 @LLM（勿删），下一行起输入要向智能助教说明的问题…'
  }
  return '输入讨论内容（需登录，不支持匿名）'
})

const roleLabel = role =>
  ({ admin: '管理员', class_teacher: '班主任', teacher: '教师', student: '学生' }[role] || role || '—')

const displayAuthorName = row => {
  if (row.message_kind === 'llm_assistant') return '智能助教'
  return row.author_real_name
}

const formatTime = v => {
  if (!v) return ''
  try {
    return new Date(v).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return String(v)
  }
}

const canDelete = row => {
  const uid = userStore.userInfo?.id
  if (uid != null && Number(row.author_user_id) === Number(uid)) return true
  if (userStore.isAdmin) return true
  if (userStore.isStudent) return false
  return userStore.canManageTeaching
}

const stopPolling = () => {
  if (pollTimer != null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  if (pollAbort) {
    try {
      pollAbort.abort()
    } catch {
      /* ignore */
    }
    pollAbort = null
  }
}

const loadList = async () => {
  if (!canUseDiscussion.value) return
  loading.value = true
  try {
    const res = await api.discussions.list({
      target_type: props.targetType,
      target_id: props.targetId,
      subject_id: resolvedSubjectId.value,
      class_id: resolvedClassId.value,
      page: page.value,
      page_size: effectivePageSize.value
    })
    total.value = res?.total ?? 0
    entries.value = res?.data ?? []
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || '加载讨论失败')
  } finally {
    loading.value = false
  }
}

const pollUntilAssistant = async (afterUserEntryId, maxSeconds = 90) => {
  stopPolling()
  const ac = new AbortController()
  pollAbort = ac
  const deadline = Date.now() + maxSeconds * 1000
  pollTimer = setInterval(async () => {
    if (Date.now() > deadline) {
      stopPolling()
      ElMessage.warning('智能助教响应超时，请稍后刷新页面查看。')
      return
    }
    try {
      const res = await api.discussions.listSignal(
        {
          target_type: props.targetType,
          target_id: props.targetId,
          subject_id: resolvedSubjectId.value,
          class_id: resolvedClassId.value,
          page: 1,
          page_size: Math.min(50, Math.max(effectivePageSize.value, 20))
        },
        ac.signal
      )
      const list = res?.data ?? []
      const hasAssistantAfter = list.some(r => r.message_kind === 'llm_assistant' && r.id > afterUserEntryId)
      if (hasAssistantAfter) {
        stopPolling()
        const lastPage = Math.max(1, Math.ceil((res?.total ?? total.value) / effectivePageSize.value))
        page.value = lastPage
        await loadList()
        ElMessage.success('智能助教已回复')
      }
    } catch (e) {
      if (e?.name === 'CanceledError' || e?.code === 'ERR_CANCELED') return
      console.error(e)
    }
  }, 1500)
}

const FORBIDDEN_AT = /@(?!LLM\b)/i

watch(draft, val => {
  if (typeof val !== 'string') return
  if (FORBIDDEN_AT.test(val)) {
    draft.value = val.replace(FORBIDDEN_AT, '@')
    ElMessage.warning('讨论区不支持 @ 其他用户或助教，已自动移除。')
  }
})

const ensureLlmPrefix = () => {
  const t = draft.value || ''
  if (!/^\s*@LLM\b/i.test(t)) {
    draft.value = t.trim() ? `@LLM\n${t}` : '@LLM\n'
  }
}

const toggleLlmMode = () => {
  llmMode.value = !llmMode.value
  if (llmMode.value) ensureLlmPrefix()
  else {
    draft.value = (draft.value || '').replace(/^\s*@LLM\s*\n?/i, '').trimStart()
  }
}

const submit = async () => {
  const text = draft.value.trim()
  if (!text || !canUseDiscussion.value) return
  if (llmMode.value && props.isStudent) {
    const inner = text.replace(/^\s*@LLM\s*\n?/i, '').trim()
    if (!inner) {
      ElMessage.warning('请填写要向智能助教说明的内容（@LLM 之后不能为空）。')
      return
    }
  }
  posting.value = true
  try {
    const invokeLlm = Boolean(llmMode.value && props.isStudent)
    const res = await api.discussions.create({
      target_type: props.targetType,
      target_id: props.targetId,
      subject_id: resolvedSubjectId.value,
      class_id: resolvedClassId.value,
      body: text,
      invoke_llm: invokeLlm
    })
    draft.value = ''
    llmMode.value = false
    const lastPage = Math.max(1, Math.ceil((total.value + 1) / effectivePageSize.value))
    page.value = lastPage
    await loadList()
    ElMessage.success(invokeLlm ? '已提交，正在请求智能助教…' : '已发表')
    if (invokeLlm && res?.id != null) {
      pollUntilAssistant(Number(res.id))
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '发表失败')
  } finally {
    posting.value = false
  }
}

const removeEntry = async row => {
  try {
    await ElMessageBox.confirm('确定删除这条讨论吗？', '确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.discussions.delete(row.id)
    ElMessage.success('已删除')
    await loadList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

watch(
  () => [props.targetId, props.targetType, props.subjectId, props.classId, props.discussionRequiresContext],
  () => {
    stopPolling()
    page.value = 1
    loadList()
  }
)

watch(
  () => userStore.userInfo?.discussion_page_size,
  () => {
    stopPolling()
    page.value = 1
    loadList()
  }
)

watch(
  () => [resolvedSubjectId.value, resolvedClassId.value],
  () => {
    stopPolling()
    page.value = 1
    loadList()
  }
)

onBeforeUnmount(() => {
  stopPolling()
})

loadList()
</script>

<style scoped>
.discussion-card {
  margin-top: 16px;
  border-radius: 12px;
}

.discussion-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.discussion-body {
  min-height: 80px;
}

.discussion-row {
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.discussion-row:last-of-type {
  border-bottom: none;
}

.discussion-row__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
}

.discussion-row__name {
  font-weight: 600;
  color: #0f172a;
}

.discussion-row__time {
  color: #94a3b8;
  font-size: 12px;
}

.discussion-row__body {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.55;
  color: #334155;
}

.discussion-row__actions {
  margin-top: 6px;
}

.discussion-pager {
  margin: 12px 0;
  justify-content: flex-end;
}

.discussion-llm-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.discussion-input {
  margin: 12px 0;
}

.muted-text {
  color: #94a3b8;
  font-size: 14px;
}
</style>
