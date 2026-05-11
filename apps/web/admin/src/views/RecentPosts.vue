<template>
  <div class="recent-posts-page">
    <header class="recent-posts-head">
      <div class="author-block">
        <el-avatar :size="56" :src="authorAvatarSrc || undefined" class="author-avatar">
          {{ authorInitial }}
        </el-avatar>
        <div class="author-text">
          <div class="author-title-row">
            <h1>{{ authorName }}</h1>
            <el-tag effect="plain" size="small">{{ roleText(author?.role) }}</el-tag>
          </div>
          <div class="author-meta">
            <span>{{ author?.username || '-' }}</span>
            <span v-if="author?.class_name">{{ author.class_name }}</span>
          </div>
        </div>
      </div>

      <div class="head-actions">
        <el-radio-group v-model="kind" size="small" @change="reloadFirstPage">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="comment">评论</el-radio-button>
          <el-radio-button label="note">笔记</el-radio-button>
          <el-radio-button label="material">资料</el-radio-button>
          <el-radio-button label="homework">作业</el-radio-button>
          <el-radio-button label="course">课程</el-radio-button>
        </el-radio-group>
      </div>
    </header>

    <section class="filters-row">
      <el-date-picker
        v-model="dateRange"
        type="datetimerange"
        unlink-panels
        range-separator="至"
        start-placeholder="开始时间"
        end-placeholder="结束时间"
        format="YYYY-MM-DD HH:mm"
        value-format="YYYY-MM-DDTHH:mm:ssZ"
        @change="reloadFirstPage"
      />
    </section>

    <main v-loading="loading" class="recent-posts-list">
      <el-empty v-if="!items.length && !loading" description="暂无可查看的发表内容" />

      <article v-for="item in items" :key="item.id" class="post-row">
        <div class="post-row__icon" :class="`post-row__icon--${item.kind}`">
          <el-icon>
            <component :is="kindIcon(item.kind)" />
          </el-icon>
        </div>

        <div class="post-row__body">
          <div class="post-row__topline">
            <el-tag size="small" effect="plain" :type="kindTagType(item.kind)">
              {{ kindText(item.kind) }}
            </el-tag>
            <span class="post-row__time">{{ formatTime(item.created_at) }}</span>
          </div>
          <h2>{{ item.title }}</h2>
          <p v-if="item.body_preview" class="post-row__preview">{{ item.body_preview }}</p>
          <div class="post-row__meta">
            <span v-if="item.subject_name">{{ item.subject_name }}</span>
            <span v-if="item.class_name">{{ item.class_name }}</span>
            <span v-if="item.context_title">{{ item.context_title }}</span>
            <el-tag v-if="item.has_attachment" size="small" type="info" effect="plain">附件</el-tag>
          </div>
        </div>

        <el-button type="primary" link :icon="ArrowRight" @click="openItem(item)">打开</el-button>
      </article>
    </main>

    <footer v-if="total > pageSize" class="pager-row">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        background
        @current-change="loadFeed"
      />
    </footer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, ChatDotRound, Collection, Document, EditPen, Reading } from '@element-plus/icons-vue'

import api from '@/api'
import { useUserStore } from '@/stores/user'
import { fetchAttachmentBlobUrl } from '@/utils/attachments'
import { openDiscussionLinkedTarget } from '@/utils/discussionLinkTargets'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const author = ref(null)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const kind = ref('all')
const dateRange = ref([])
const authorAvatarSrc = ref('')
let authorAvatarBlobUrl = ''

const isMine = computed(() => route.name === 'RecentPostsMine')
const routeUserId = computed(() => Number(route.params.userId || 0))

const authorName = computed(() => author.value?.real_name || author.value?.username || '用户')
const authorInitial = computed(() => authorName.value.trim().charAt(0) || 'U')

const roleText = role =>
  ({
    admin: '管理员',
    class_teacher: '班主任',
    teacher: '教师',
    student: '学生'
  }[role] || role || '-')

const kindText = value =>
  ({
    comment: '评论',
    note: '笔记',
    material: '资料',
    homework: '作业',
    course: '课程'
  }[value] || '发表')

const kindTagType = value =>
  ({
    comment: 'primary',
    note: 'success',
    material: 'warning',
    homework: 'danger',
    course: 'info'
  }[value] || 'info')

const kindIcon = value =>
  ({
    comment: ChatDotRound,
    note: EditPen,
    material: Collection,
    homework: Document,
    course: Reading
  }[value] || ChatDotRound)

const revokeAuthorAvatar = () => {
  if (authorAvatarBlobUrl) {
    URL.revokeObjectURL(authorAvatarBlobUrl)
    authorAvatarBlobUrl = ''
  }
  authorAvatarSrc.value = ''
}

const loadAuthorAvatar = async () => {
  revokeAuthorAvatar()
  if (!author.value?.avatar_url) {
    return
  }
  try {
    authorAvatarBlobUrl = await fetchAttachmentBlobUrl(author.value.avatar_url)
    authorAvatarSrc.value = authorAvatarBlobUrl
  } catch {
    revokeAuthorAvatar()
  }
}

const buildParams = () => {
  const params = {
    page: page.value,
    page_size: pageSize,
    kind: kind.value
  }
  if (Array.isArray(dateRange.value) && dateRange.value.length === 2) {
    params.from_created_at = dateRange.value[0]
    params.to_created_at = dateRange.value[1]
  }
  return params
}

const loadFeed = async () => {
  loading.value = true
  try {
    const result = isMine.value
      ? await api.recentPosts.mine(buildParams())
      : await api.recentPosts.user(routeUserId.value, buildParams())
    author.value = result?.author || null
    items.value = result?.data || []
    total.value = Number(result?.total || 0)
    await loadAuthorAvatar()
  } finally {
    loading.value = false
  }
}

const reloadFirstPage = async () => {
  page.value = 1
  await loadFeed()
}

const openItem = async item => {
  if (!item?.target?.available) {
    ElMessage.info('当前无法打开该内容')
    return
  }
  await openDiscussionLinkedTarget(item.target, router, userStore)
}

const formatTime = value => {
  if (!value) return ''
  try {
    return new Date(value).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return String(value)
  }
}

watch(
  () => [route.name, route.params.userId],
  () => {
    page.value = 1
    loadFeed()
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  revokeAuthorAvatar()
})
</script>

<style scoped>
.recent-posts-page {
  width: min(100%, 980px);
  margin: 0 auto;
  padding: 24px 28px 48px;
}

.recent-posts-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid #e5e7eb;
}

.author-block {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 14px;
}

.author-avatar {
  flex-shrink: 0;
  background: #2563eb;
  color: #fff;
  font-weight: 700;
}

.author-text {
  min-width: 0;
}

.author-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.author-title-row h1 {
  margin: 0;
  color: #111827;
  font-size: 24px;
  font-weight: 720;
  line-height: 1.25;
}

.author-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 5px;
  color: #64748b;
  font-size: 13px;
}

.head-actions {
  display: flex;
  flex-shrink: 0;
  max-width: 100%;
  overflow-x: auto;
  padding-bottom: 2px;
}

.head-actions :deep(.el-radio-group) {
  flex-wrap: nowrap;
}

.filters-row {
  display: flex;
  justify-content: flex-end;
  padding: 14px 0;
}

.recent-posts-list {
  min-height: 240px;
}

.post-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: start;
  gap: 14px;
  padding: 16px 0;
  border-bottom: 1px solid #eef2f7;
}

.post-row__icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 8px;
}

.post-row__icon--comment {
  background: #dbeafe;
  color: #1d4ed8;
}

.post-row__icon--note {
  background: #dcfce7;
  color: #15803d;
}

.post-row__icon--material {
  background: #fef3c7;
  color: #b45309;
}

.post-row__icon--homework {
  background: #fee2e2;
  color: #b91c1c;
}

.post-row__icon--course {
  background: #e0f2fe;
  color: #0369a1;
}

.post-row__body {
  min-width: 0;
}

.post-row__topline {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.post-row__time {
  color: #64748b;
  font-size: 13px;
}

.post-row h2 {
  margin: 0;
  color: #0f172a;
  font-size: 16px;
  font-weight: 680;
  line-height: 1.35;
}

.post-row__preview {
  margin: 7px 0 0;
  color: #334155;
  font-size: 14px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.post-row__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  color: #64748b;
  font-size: 13px;
}

.pager-row {
  display: flex;
  justify-content: center;
  padding-top: 18px;
}

@media (max-width: 720px) {
  .recent-posts-page {
    padding: 16px 14px 36px;
  }

  .recent-posts-head {
    align-items: stretch;
    flex-direction: column;
  }

  .filters-row {
    justify-content: stretch;
  }

  .filters-row :deep(.el-date-editor) {
    width: 100%;
  }

  .post-row {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .post-row > .el-button {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
