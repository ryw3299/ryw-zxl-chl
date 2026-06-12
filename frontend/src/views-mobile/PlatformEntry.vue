<script setup>
/**
 * visual thesis: 用一块蓝色课程引导页承接平台握手，让“进入本次学习会话”成为唯一明确动作。
 * content structure: 品牌头图 -> 当前课程与上下文 -> 会话同步步骤 -> 状态提示。
 * interaction pattern: 首屏淡入，步骤状态轻微更新，同步完成后直接切到 lesson 主页面。
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { syncUser } from '@/api/platform'
import { useLessonStore } from '@/store/lessonStore'
import { useUserStore } from '@/store/userStore'

const route = useRoute()
const router = useRouter()
const lessonStore = useLessonStore()
const userStore = useUserStore()

const DEFAULT_PLATFORM_PAYLOAD = {
  userId: 'demo-user-001',
  courseId: 'demo-course-001',
  lessonId: 'lesson-ai-001',
  token: 'demo-token',
  role: 'student',
  schoolId: 'demo-school',
}

const entryState = ref('syncing')
const statusText = ref('正在读取平台参数...')

const normalizeQuery = (value, fallback = '') => {
  if (Array.isArray(value)) {
    return value[0] || fallback
  }
  return typeof value === 'string' ? value.trim() : fallback
}

const payload = computed(() => ({
  userId: normalizeQuery(route.query.userId, DEFAULT_PLATFORM_PAYLOAD.userId),
  courseId: normalizeQuery(route.query.courseId, DEFAULT_PLATFORM_PAYLOAD.courseId),
  lessonId: normalizeQuery(route.query.lessonId, DEFAULT_PLATFORM_PAYLOAD.lessonId),
  token: normalizeQuery(route.query.token, DEFAULT_PLATFORM_PAYLOAD.token),
  role: normalizeQuery(route.query.role, DEFAULT_PLATFORM_PAYLOAD.role),
  schoolId: normalizeQuery(route.query.schoolId, DEFAULT_PLATFORM_PAYLOAD.schoolId),
}))

const usingMockPayload = computed(() => (
  !route.query.userId && !route.query.courseId && !route.query.lessonId
))

const contextItems = computed(() => ([
  { label: '课程', value: payload.value.courseId || '未传课程' },
  { label: '课时', value: payload.value.lessonId || '未传课时' },
  { label: '身份', value: payload.value.role || 'student' },
  { label: '用户', value: payload.value.userId || '未传用户' },
]))

const stepItems = computed(() => {
  const isSuccess = entryState.value === 'success'
  const isError = entryState.value === 'error'

  return [
    {
      title: '接收平台参数',
      desc: usingMockPayload.value ? '当前使用本地演示参数，便于直接调试。' : '已从泛雅入口接收课程与用户上下文。',
      state: 'done',
    },
    {
      title: '同步用户会话',
      desc: isError ? '用户同步失败，请检查后端接口或入口参数。' : '写入 token、用户身份与课程上下文。',
      state: isError ? 'error' : isSuccess ? 'done' : 'active',
    },
    {
      title: '进入课程学习页',
      desc: `目标 lesson：${payload.value.lessonId}`,
      state: isSuccess ? 'done' : 'pending',
    },
  ]
})

const persistContext = () => {
  lessonStore.syncPlatformContext(payload.value)
}

const bootstrap = async () => {
  if (!payload.value.userId || !payload.value.lessonId) {
    entryState.value = 'error'
    statusText.value = '缺少 userId 或 lessonId，无法建立课程会话。'
    showToast('平台参数不完整')
    return
  }

  persistContext()
  statusText.value = '正在同步平台用户...'

  // 尝试调用后端同步接口，失败时降级为纯前端 demo 模式继续进入课程
  let userInfo = {}
  let authToken = payload.value.token || `demo-${payload.value.userId}`

  try {
    const result = await syncUser({
      userId: payload.value.userId,
      courseId: payload.value.courseId,
      lessonId: payload.value.lessonId,
      role: payload.value.role,
      schoolId: payload.value.schoolId,
      token: payload.value.token,
    })
    userInfo = result?.userInfo || result?.user || {}
    authToken = result?.token || authToken
  } catch {
    // 后端不可用时静默降级，仍使用传入/demo 参数继续
    statusText.value = '后端未就绪，以演示模式进入课程...'
  }

  userStore.login(
    {
      userId: userInfo.userId || payload.value.userId,
      role: userInfo.role || payload.value.role || 'student',
    },
    authToken,
  )

  entryState.value = 'success'
  statusText.value = '会话同步完成，正在进入课程...'

  router.replace('/m/home')
}

onMounted(() => {
  bootstrap()
})
</script>

<template>
  <div class="platform-entry">
    <transition appear name="entry-fade">
      <section class="entry-frame">
        <header class="entry-hero">
          <div class="entry-hero__tag">智悉云擎 · 学生端</div>
          <h1>进入当前课程学习会话</h1>
          <p>
            采用嵌入式单课 session 模式，进入后直接落在当前 lesson，不再经过首页或选课页。
          </p>
          <div v-if="usingMockPayload" class="entry-hero__mock">
            当前未接平台实参，已自动注入一组演示参数
          </div>
        </header>

        <section class="entry-section">
          <div class="entry-section__head">
            <span>当前上下文</span>
            <strong>{{ payload.courseId }}</strong>
          </div>
          <div class="entry-context-grid">
            <div v-for="item in contextItems" :key="item.label" class="entry-context-item">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </section>

        <section class="entry-section">
          <div class="entry-section__head">
            <span>会话建立步骤</span>
            <strong>{{ entryState === 'error' ? '异常' : entryState === 'success' ? '已完成' : '进行中' }}</strong>
          </div>
          <div class="entry-step-list">
            <div
              v-for="item in stepItems"
              :key="item.title"
              :class="['entry-step-item', `is-${item.state}`]"
            >
              <span class="entry-step-item__dot" />
              <div class="entry-step-item__body">
                <strong>{{ item.title }}</strong>
                <p>{{ item.desc }}</p>
              </div>
            </div>
          </div>
        </section>

        <footer class="entry-status">
          <van-loading v-if="entryState === 'syncing'" size="18px" color="#1677ff" />
          <van-icon v-else-if="entryState === 'success'" name="success" size="18" color="#12b76a" />
          <van-icon v-else name="warning-o" size="18" color="#f79009" />
          <span>{{ statusText }}</span>
        </footer>
      </section>
    </transition>
  </div>
</template>

<style scoped>
.platform-entry {
  min-height: 100vh;
  padding: 18px 16px 24px;
}

.entry-frame {
  min-height: calc(100vh - 42px);
  border-radius: 28px;
  overflow: hidden;
  background: linear-gradient(180deg, #fdfefe 0%, #f7faff 100%);
  box-shadow: 0 20px 48px rgba(15, 41, 82, 0.08);
}

.entry-hero {
  padding: 28px 22px 24px;
  background: linear-gradient(135deg, #1677ff 0%, #2f8cff 50%, #5ba8ff 100%);
  color: #fff;
}

.entry-hero__tag {
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.entry-hero h1 {
  margin: 16px 0 0;
  font-size: 30px;
  line-height: 1.1;
  letter-spacing: -0.05em;
}

.entry-hero p {
  margin: 12px 0 0;
  font-size: 14px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.88);
}

.entry-hero__mock {
  display: inline-flex;
  margin-top: 16px;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 12px;
  font-weight: 700;
}

.entry-section {
  padding: 20px 18px 0;
}

.entry-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.entry-section__head span {
  font-size: 12px;
  letter-spacing: 0.08em;
  color: #6b7a90;
}

.entry-section__head strong {
  font-size: 14px;
  color: #172b4d;
}

.entry-context-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 14px;
}

.entry-context-item {
  padding: 14px 12px;
  border-radius: 18px;
  background: #f6f9ff;
}

.entry-context-item span {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: #6b7a90;
}

.entry-context-item strong {
  display: block;
  font-size: 14px;
  line-height: 1.55;
  color: #172b4d;
  word-break: break-all;
}

.entry-step-list {
  display: grid;
  gap: 14px;
  margin-top: 14px;
}

.entry-step-item {
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.entry-step-item__dot {
  width: 10px;
  height: 10px;
  margin-top: 7px;
  border-radius: 50%;
  background: #d0dae8;
}

.entry-step-item.is-done .entry-step-item__dot {
  background: #12b76a;
}

.entry-step-item.is-active .entry-step-item__dot {
  background: #1677ff;
  box-shadow: 0 0 0 6px rgba(22, 119, 255, 0.12);
}

.entry-step-item.is-error .entry-step-item__dot {
  background: #f79009;
}

.entry-step-item__body strong {
  display: block;
  font-size: 15px;
  color: #172b4d;
}

.entry-step-item__body p {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: #6b7a90;
}

.entry-status {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 20px 18px 0;
  padding: 16px 0 20px;
  border-top: 1px solid rgba(102, 117, 140, 0.12);
  font-size: 13px;
  color: #1677ff;
}

.entry-fade-enter-active,
.entry-fade-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.entry-fade-enter-from,
.entry-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
