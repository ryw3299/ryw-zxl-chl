<template>
  <div class="home-page">
    <aside class="home-sidebar">
      <div class="sidebar-brand" @click="router.push('/')">
        <div class="brand-mark">
          <svg width="30" height="30" viewBox="0 0 30 30" fill="none" aria-hidden="true">
            <rect x="2" y="2" width="26" height="26" rx="8" fill="#2563eb" />
            <path d="M9.5 15.5L13 19L20.5 11.5" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <div class="brand-copy">
          <div class="brand-name">智学工坊</div>
          <div class="brand-tagline">AI赋能学习，成长看得见</div>
        </div>
      </div>

      <nav class="sidebar-nav">
        <button
          v-for="item in navItems"
          :key="item.label"
          type="button"
          :class="['nav-item', { active: item.active }]"
          @click="router.push(item.to)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-bottom">
        <div class="streak-card">
          <div class="streak-heading">
            <span>连续学习</span>
            <span class="streak-fire">热</span>
          </div>
          <div class="streak-main">
            <strong>16</strong>
            <span>天</span>
          </div>
          <div class="streak-meta">
            <span>累计学习</span>
            <strong>128 小时</strong>
          </div>
          <button type="button" class="ghost-wide-button" @click="goDashboard">学习日历</button>
        </div>
        <button type="button" class="logout-btn" @click="handleLogout">
          <el-icon><Switch /></el-icon>
          <span>退出登录</span>
        </button>
      </div>
    </aside>

    <div class="page-shell">
      <header class="page-header">
        <div class="header-search">
          <el-icon><Search /></el-icon>
          <input
            v-model="searchText"
            type="text"
            placeholder="搜索课程、资源、题目或知识点"
            @keyup.enter="onSearch"
          />
        </div>

        <div class="header-actions">
          <div class="header-user" @click="router.push(userStore.isLogin ? '/settings' : '/login')">
            <div class="user-avatar">{{ (userStore.username || '')[0] || '同' }}</div>
            <div class="user-meta">
              <span class="user-name">{{ userStore.username || '同学' }}</span>
              <span class="user-level">Lv.6</span>
            </div>
            <el-icon class="user-arrow"><ArrowDown /></el-icon>
          </div>
        </div>
      </header>

      <main class="page-content">
        <section class="hero-card">
          <div class="hero-content">
            <p class="hero-label">学习总览</p>
            <h1>AI 让学习更懂你</h1>
            <p class="hero-description">
              基于你的学习数据和兴趣偏好，智能推荐合适的内容与路径，让每一次学习都更高效，更有收获。
            </p>
            <div class="hero-actions">
              <router-link :to="userStore.isLogin ? '/dashboard' : '/login'" class="primary-button">
                开始学习
              </router-link>
              <button type="button" class="secondary-button" @click="scrollToRecommendations">
                制定学习计划
              </button>
            </div>
          </div>

          <div class="hero-illustration" aria-hidden="true">
            <div class="illustration-chart">
              <span class="chart-label">学习进度</span>
              <svg viewBox="0 0 180 94" fill="none">
                <path d="M10 68C22 66 31 46 46 43C60 40 63 62 78 61C92 60 100 24 117 22C135 20 141 45 170 30" stroke="#4f8bff" stroke-width="4" stroke-linecap="round" />
              </svg>
            </div>
            <div class="illustration-stat">
              <span>知识掌握度</span>
              <div class="stat-ring">
                <div class="stat-ring-inner">72%</div>
              </div>
            </div>
            <div class="robot-stage">
              <div class="robot-hat"></div>
              <div class="robot-head">
                <span class="robot-eye"></span>
                <span class="robot-eye"></span>
              </div>
              <div class="robot-body"></div>
            </div>
            <div class="illustration-card"></div>
            <div class="illustration-card small"></div>
          </div>
        </section>

        <section class="feature-grid" ref="recommendationsRef">
          <button
            v-for="feature in features"
            :key="feature.title"
            type="button"
            class="feature-card"
            @click="feature.action"
          >
            <div class="feature-icon" :style="{ background: feature.tint }">
              <el-icon><component :is="feature.icon" /></el-icon>
            </div>
            <div class="feature-text">
              <strong>{{ feature.title }}</strong>
              <span>{{ feature.desc }}</span>
            </div>
          </button>
        </section>

        <section class="content-grid">
          <article class="surface-card section-card">
            <div class="section-head">
              <h2>推荐学习资源</h2>
              <button type="button" class="text-button" @click="router.push('/resources')">更多</button>
            </div>

            <div class="resource-list">
              <button
                v-for="resource in displayedResources"
                :key="resource.id"
                type="button"
                class="resource-item"
                @click="openResource(resource)"
              >
                <div class="resource-cover" :style="{ background: getCoverBg(resource.resource_type) }">
                  <span>{{ resource.typeLabel }}</span>
                </div>
                <div class="resource-body">
                  <div class="resource-title">{{ resource.title }}</div>
                  <div class="resource-meta">
                    <span>{{ resource.typeLabel }}</span>
                    <span>4.8</span>
                    <span>{{ resource.learners }}</span>
                  </div>
                  <div class="resource-progress-row">
                    <div class="resource-progress">
                      <div class="resource-progress-bar" :style="{ width: resource.progress + '%' }"></div>
                    </div>
                    <span>{{ resource.progress }}%</span>
                  </div>
                </div>
              </button>
            </div>
          </article>

          <article class="surface-card section-card">
            <div class="section-head">
              <h2>今日任务</h2>
              <button type="button" class="text-button" @click="goDashboard">更多</button>
            </div>

            <div class="task-list">
              <div v-for="task in tasks" :key="task.title" class="task-item">
                <div :class="['task-status', { done: task.done }]">
                  <el-icon v-if="task.done"><Check /></el-icon>
                </div>
                <div class="task-main">
                  <div class="task-title-row">
                    <span class="task-title">{{ task.title }}</span>
                    <el-tag :type="task.done ? 'success' : task.tagType" effect="plain" size="small">
                      {{ task.tag }}
                    </el-tag>
                  </div>
                  <div class="task-subline">
                    <span>预计 {{ task.time }}</span>
                    <span>{{ task.finished }}/{{ task.total }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="calendar-card">
              <div class="calendar-head">
                <span>学习日历</span>
                <div class="calendar-nav">
                  <button type="button" @click="changeMonth(-1)">
                    <el-icon><ArrowLeft /></el-icon>
                  </button>
                  <span>{{ calYear }}年{{ calMonth }}月</span>
                  <button type="button" @click="changeMonth(1)">
                    <el-icon><ArrowRight /></el-icon>
                  </button>
                </div>
              </div>
              <div class="calendar-grid">
                <span v-for="weekday in weekdays" :key="weekday" class="calendar-weekday">{{ weekday }}</span>
                <button
                  v-for="(day, index) in calendarDays"
                  :key="`${index}-${day || 'empty'}`"
                  type="button"
                  :disabled="!day"
                  :class="['calendar-day', { active: day === todayDate }]"
                  @click="day && goDashboard()"
                >
                  {{ day || '' }}
                </button>
              </div>
            </div>
          </article>

          <article class="surface-card section-card">
            <div class="section-head">
              <h2>最近学习记录</h2>
              <button type="button" class="text-button" @click="router.push('/resources')">更多</button>
            </div>

            <div class="recent-list">
              <div v-for="item in recentRecords" :key="item.name" class="recent-item" @click="goToResource(item)">
                <div class="recent-icon" :style="{ background: item.iconBg }">
                  <span style="color:white;font-weight:600">{{ (item.name || '?')[0] }}</span>
                </div>
                <div class="recent-main">
                  <div class="recent-name">{{ item.name }}</div>
                  <div class="recent-subline">上次学习：{{ item.chapter }}</div>
                </div>
                <div class="recent-side">
                  <span class="recent-link">继续学</span>
                  <span class="recent-percent">{{ item.percent }}%</span>
                </div>
              </div>
            </div>
          </article>
        </section>

        <section class="advice-bar">
          <div class="advice-copy">
            <div class="advice-icon">
              <el-icon><Sunny /></el-icon>
            </div>
            <div>
              <strong>学习建议</strong>
              <p>基于你的学习情况，我们为你生成了本周学习建议。</p>
            </div>
          </div>
          <button type="button" class="advice-button" @click="router.push(userStore.isLogin ? '/learning-path' : '/login')">
            查看建议
          </button>
        </section>
      </main>

    <AssistantPanel />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Check,
  Collection,
  Compass,
  DataAnalysis,
  FolderOpened,
  Histogram,
  HomeFilled,
  MagicStick,
  Management,
  Opportunity,
  Promotion,
  Reading,
  RefreshRight,
  Search,
  Setting,
  Sunny,
  Switch,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/store/userStore'
import { getResources } from '@/api/resource'
import AssistantPanel from '@/components/AssistantPanel.vue'

const router = useRouter()
const userStore = useUserStore()

const recommendationsRef = ref(null)
const searchText = ref('')
const assistantDraft = ref('')
const resourceItems = ref([])
const tasks = ref([])
const recentRecords = ref([])

const navItems = computed(() => [
  { label: '首页', to: '/', icon: HomeFilled, active: true },
  { label: '工作台', to: '/dashboard', icon: Histogram },
  { label: '个性化路径', to: '/learning-path', icon: Compass },
  { label: '资源中心', to: '/resources', icon: FolderOpened },
  { label: '学习报告', to: '/profile', icon: DataAnalysis },
  { label: '设置', to: '/settings', icon: Setting },
])

const features = [
  {
    title: '智能推荐',
    desc: '为你推荐个性化学习内容',
    icon: Opportunity,
    tint: 'rgba(37, 99, 235, 0.10)',
    action: () => router.push('/resources'),
  },
  {
    title: 'AI答疑',
    desc: '7x24小时智能解答问题',
    icon: Promotion,
    tint: 'rgba(16, 185, 129, 0.12)',
    action: () => goAssistant(),
  },
  {
    title: '学习报告',
    desc: '学习数据可视化分析',
    icon: DataAnalysis,
    tint: 'rgba(139, 92, 246, 0.12)',
    action: () => router.push('/profile'),
  },
  {
    title: '个性化路径',
    desc: '定制专属学习路线',
    icon: Compass,
    tint: 'rgba(245, 158, 11, 0.14)',
    action: () => router.push('/learning-path'),
  },
]

const helperQuestionGroups = [
  ['如何提高数学解题速度？', '推荐一些机器学习入门资料', '今天的学习重点是什么？'],
  ['帮我规划本周的学习任务', '这门课程应该先学哪部分？', '能根据我的进度推荐资源吗？'],
  ['给我出3道复习检测题', '这段知识点能再讲一遍吗？', '我适合先做题还是先看视频？'],
]
const questionGroupIndex = ref(0)
const helperQuestions = computed(() => helperQuestionGroups[questionGroupIndex.value])

const fallbackResources = [
  { id: 'fallback-course-1', title: 'Python基础入门', resource_type: 'course' },
  { id: 'fallback-course-2', title: '机器学习经典算法', resource_type: 'course' },
  { id: 'fallback-course-3', title: '数据结构与算法（Python版）', resource_type: 'course' },
]

const resourceTypeMap = {
  course: '课程',
  document: '文档',
  video: '视频',
  quiz: '题库',
  project: '项目',
  ppt: 'PPT',
  mindmap: '思维导图',
}

const resourceTypeCovers = {
  course: 'linear-gradient(135deg, #3b82f6 0%, #5b8cff 100%)',
  document: 'linear-gradient(135deg, #10b981 0%, #34d399 100%)',
  video: 'linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%)',
  quiz: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)',
  project: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)',
  ppt: 'linear-gradient(135deg, #2563eb 0%, #60a5fa 100%)',
  mindmap: 'linear-gradient(135deg, #4f46e5 0%, #818cf8 100%)',
}

const resourceStats = [
  { progress: 65, learners: '32.5万人学习' },
  { progress: 40, learners: '18.7万人学习' },
  { progress: 20, learners: '25.1万人学习' },
]

const displayedResources = computed(() => {
  const source = resourceItems.value.length ? resourceItems.value.slice(0, 3) : fallbackResources
  return source.map((item, index) => ({
    ...item,
    typeLabel: resourceTypeMap[item.resource_type] || '课程',
    progress: resourceStats[index]?.progress || 30,
    learners: resourceStats[index]?.learners || '12.6万人学习',
  }))
})

const now = new Date()
const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const calYear = ref(now.getFullYear())
const calMonth = ref(now.getMonth() + 1)
const todayDate = now.getDate()

const calendarDays = computed(() => {
  const firstWeekday = new Date(calYear.value, calMonth.value - 1, 1).getDay()
  const totalDays = new Date(calYear.value, calMonth.value, 0).getDate()
  const days = []

  for (let i = 0; i < firstWeekday; i += 1) days.push(null)
  for (let day = 1; day <= totalDays; day += 1) days.push(day)

  return days
})

function scrollToRecommendations() {
  recommendationsRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function onSearch() {
  const keyword = searchText.value.trim()
  if (!keyword) return
  router.push(`/resources?keyword=${encodeURIComponent(keyword)}`)
}

function goDashboard() {
  router.push(userStore.isLogin ? '/dashboard' : '/login')
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

function goAssistant() {
  router.push(userStore.isLogin ? '/dashboard' : '/login')
}

function goToResource(item) {
  if (item.resource_id) {
    // Store last position
    localStorage.setItem('lastRead_' + item.resource_id, JSON.stringify({ chapter: item.chapter, percent: item.percent }))
    router.push('/resources/' + item.resource_id + '/read')
  } else {
    router.push('/resources')
  }
}

function fillQuestion(question) {
  assistantDraft.value = question
}

function rotateQuestions() {
  questionGroupIndex.value = (questionGroupIndex.value + 1) % helperQuestionGroups.length
}

function changeMonth(step) {
  const current = new Date(calYear.value, calMonth.value - 1 + step, 1)
  calYear.value = current.getFullYear()
  calMonth.value = current.getMonth() + 1
}

function getCoverBg(resourceType) {
  return resourceTypeCovers[resourceType] || resourceTypeCovers.course
}

function openResource(resource) {
  if (typeof resource.id === 'number') {
    router.push(`/resources/${resource.id}`)
    return
  }
  router.push('/resources')
}

onMounted(async () => {
  try {
    const [res, taskRes, recordRes] = await Promise.allSettled([
      getResources({ page_size: 6 }),
      import('@/api/task').then(m => m.getTasks()),
      import('@/api/studyRecord').then(m => m.getStudyRecords()),
    ])
    if (res.status === 'fulfilled') resourceItems.value = res.value.items || []
    if (taskRes.status === 'fulfilled') tasks.value = taskRes.value.slice(0, 3)
    if (recordRes.status === 'fulfilled') {
      recentRecords.value = (recordRes.value || []).slice(0, 4).map(r => ({
        name: r.resource_title || '',
        chapter: r.chapter || '',
        percent: r.progress_percent || 0,
        iconBg: 'rgba(37, 99, 235, 0.14)',
        resource_id: r.resource_id || null,
      }))
    }
  } catch {}
})
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  background: #f5f7fb;
  color: var(--text-primary);
}

.home-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  background: #fff;
  border-right: 1px solid #e8edf5;
  padding: 18px 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.brand-copy {
  min-width: 0;
}

.brand-name {
  font-size: 1.375rem;
  font-weight: 700;
  color: #2b6cff;
  line-height: 1.1;
}

.brand-tagline {
  margin-top: 3px;
  font-size: 0.75rem;
  color: #98a2b3;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-item {
  width: 100%;
  height: 44px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: #4f5f79;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  font: inherit;
  cursor: pointer;
  transition: background-color 0.18s ease, color 0.18s ease;
}

.nav-item:hover {
  background: #f5f8ff;
  color: #2b6cff;
}

.nav-item.active {
  background: #edf3ff;
  color: #2b6cff;
  font-weight: 600;
}

.nav-item .el-icon {
  font-size: 16px;
}

.sidebar-bottom {
  margin-top: auto;
}

.streak-card {
  border: 1px solid #e8edf5;
  border-radius: 16px;
  background: #fff;
  padding: 14px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.03);
}

.streak-heading,
.streak-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.streak-heading {
  font-size: 0.78rem;
  color: #7b8798;
}

.streak-fire {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 20px;
  border-radius: 999px;
  background: #fff3df;
  color: #e08c1a;
  font-size: 0.72rem;
}

.streak-main {
  margin: 10px 0 8px;
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.streak-main strong {
  font-size: 2.25rem;
  line-height: 1;
  color: #16223b;
}

.streak-main span {
  color: #7b8798;
}

.streak-meta {
  font-size: 0.78rem;
  color: #7b8798;
}

.streak-meta strong {
  color: #35445d;
  font-size: 0.82rem;
  font-weight: 600;
}

.ghost-wide-button {
  width: 100%;
  margin-top: 14px;
  height: 36px;
  border: 1px solid #e0e7f2;
  border-radius: 999px;
  background: #f8fafc;
  color: #4f5f79;
  font: inherit;
  cursor: pointer;
  transition: border-color 0.18s ease, color 0.18s ease;
}

.ghost-wide-button:hover {
  border-color: #2b6cff;
  color: #2b6cff;
}

.logout-btn {
  width: 100%; height: 36px; margin-top: 8px;
  border: 1px solid #fee2e2; border-radius: 10px;
  background: #fff; color: #ef4444; font: inherit; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  font-size: 0.82rem;
}
.logout-btn:hover { background: #fef2f2; }

.page-shell {
  min-width: 0;
}

.page-header {
  grid-column: 1 / -1;
  height: 74px;
  padding: 18px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  background: rgba(245, 247, 251, 0.92);
  backdrop-filter: blur(8px);
  position: sticky;
  top: 0;
  z-index: 20;
}

.header-search {
  width: min(560px, 100%);
  height: 42px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  border: 1px solid #dde5f0;
  border-radius: 999px;
  background: #fff;
  color: #8b98ab;
  box-shadow: 0 8px 20px rgba(59, 86, 145, 0.04);
}

.header-search input {
  flex: 1;
  border: 0;
  outline: none;
  background: transparent;
  font: inherit;
  color: #334155;
}

.header-search input::placeholder {
  color: #98a2b3;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.notify-badge {
  position: absolute;
  top: -3px;
  right: -1px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #ff5b6e;
  color: #fff;
  font-size: 0.7rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 4px;
}

.user-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #89a9ff, #5b8cff);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.user-name {
  font-size: 0.92rem;
  font-weight: 600;
  color: #1e293b;
}

.user-level {
  width: fit-content;
  margin-top: 3px;
  padding: 2px 6px;
  border-radius: 999px;
  background: #2b6cff;
  color: #fff;
  font-size: 0.68rem;
}

.user-arrow {
  color: #94a3b8;
}

.page-content {
  padding: 6px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero-card,
.surface-card,
.assistant-card,
.advice-bar {
  background: #fff;
  border: 1px solid #e7edf6;
  box-shadow: 0 14px 36px rgba(52, 72, 108, 0.05);
}

.hero-card {
  border-radius: 22px;
  padding: 24px;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
  gap: 20px;
  background: linear-gradient(135deg, #edf4ff 0%, #f5f9ff 55%, #eef5ff 100%);
}

.hero-content {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.hero-label {
  width: fit-content;
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(43, 108, 255, 0.08);
  color: #5b7bc8;
  font-size: 0.74rem;
  margin-bottom: 12px;
}

.hero-content h1 {
  font-size: 2.6rem;
  line-height: 1.16;
  letter-spacing: -0.02em;
  color: #16223b;
}

.hero-description {
  max-width: 450px;
  margin-top: 14px;
  font-size: 0.95rem;
  line-height: 1.8;
  color: #5e6d84;
}

.hero-actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}

.primary-button,
.secondary-button,
.advice-button {
  height: 42px;
  padding: 0 20px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}

.primary-button {
  background: #2b6cff;
  color: #fff !important;
  box-shadow: 0 12px 24px rgba(43, 108, 255, 0.22);
}

.primary-button:hover {
  background: #1f5ff1;
}

.secondary-button {
  border: 1px solid #bad0ff;
  background: #fff;
  color: #2b6cff;
}

.secondary-button:hover {
  border-color: #2b6cff;
}

.hero-illustration {
  position: relative;
  min-height: 250px;
}

.illustration-chart,
.illustration-stat,
.illustration-card {
  position: absolute;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(204, 219, 245, 0.9);
  border-radius: 18px;
  box-shadow: 0 18px 34px rgba(91, 123, 200, 0.10);
}

.illustration-chart {
  top: 0;
  left: 12px;
  width: 220px;
  padding: 14px 14px 10px;
}

.chart-label {
  display: block;
  margin-bottom: 10px;
  font-size: 0.72rem;
  color: #6d7b92;
}

.illustration-chart svg {
  width: 100%;
  height: 90px;
}

.illustration-stat {
  left: 28px;
  bottom: 34px;
  width: 120px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.75rem;
  color: #597089;
}

.stat-ring {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: conic-gradient(#2b6cff 0 72%, #d9e8ff 72% 100%);
}

.stat-ring-inner {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #fff;
  display: grid;
  place-items: center;
  color: #2b6cff;
  font-size: 0.66rem;
  font-weight: 700;
}

.robot-stage {
  position: absolute;
  right: 28px;
  top: 28px;
  width: 190px;
  height: 200px;
}

.robot-head,
.robot-body {
  margin: 0 auto;
  border: 1px solid rgba(185, 206, 244, 0.9);
  background: linear-gradient(180deg, #ffffff, #eef4ff);
  box-shadow: 0 20px 34px rgba(84, 124, 217, 0.14);
}

.robot-hat {
  position: absolute;
  right: 10px;
  top: -4px;
  width: 58px;
  height: 22px;
  border-radius: 8px 8px 18px 18px;
  background: linear-gradient(135deg, #6f96ff, #3c72ff);
  transform: rotate(22deg);
}

.robot-head {
  width: 118px;
  height: 118px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
}

.robot-eye {
  width: 18px;
  height: 24px;
  border-radius: 999px;
  background: radial-gradient(circle at 50% 50%, #77deff 0, #77deff 28%, #275bff 78%, #275bff 100%);
  box-shadow: 0 0 18px rgba(72, 195, 255, 0.45);
}

.robot-body {
  width: 134px;
  height: 52px;
  margin-top: 10px;
  border-radius: 18px;
}

.illustration-card {
  right: 2px;
  bottom: 42px;
  width: 90px;
  height: 72px;
}

.illustration-card::before,
.illustration-card::after,
.illustration-card.small::before,
.illustration-card.small::after {
  content: '';
  position: absolute;
  left: 14px;
  right: 14px;
  height: 6px;
  border-radius: 999px;
  background: rgba(84, 124, 217, 0.18);
}

.illustration-card::before {
  top: 18px;
}

.illustration-card::after {
  top: 34px;
}

.illustration-card.small {
  width: 68px;
  height: 54px;
  right: 56px;
  top: 74px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.feature-card,
.assistant-question {
  border: 1px solid #e7edf6;
  background: #fff;
  font: inherit;
}

.feature-card {
  min-width: 0;
  border-radius: 16px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.feature-card:hover {
  transform: translateY(-1px);
  border-color: #d4e0f6;
  box-shadow: 0 12px 28px rgba(45, 68, 110, 0.06);
}

.feature-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #2b6cff;
  flex: none;
}

.feature-icon .el-icon {
  font-size: 20px;
}

.feature-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
}

.feature-text strong {
  font-size: 0.9rem;
  color: #1e293b;
}

.feature-text span {
  font-size: 0.76rem;
  line-height: 1.45;
  color: #7b8798;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr) minmax(0, 0.94fr);
  gap: 18px;
  align-items: start;
}

.surface-card {
  border-radius: 18px;
}

.section-card {
  padding: 18px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 16px;
}

.section-head h2 {
  font-size: 1.02rem;
  color: #1e293b;
}

.text-button {
  border: 0;
  background: transparent;
  color: #6d7b92;
  font: inherit;
  cursor: pointer;
}

.text-button:hover {
  color: #2b6cff;
}

.resource-list,
.task-list,
.recent-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.resource-item {
  border: 0;
  background: transparent;
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 12px;
  padding: 0;
  text-align: left;
  cursor: pointer;
}

.resource-cover {
  height: 72px;
  border-radius: 14px;
  padding: 14px;
  color: #fff;
  font-size: 0.86rem;
  font-weight: 600;
  display: flex;
  align-items: flex-start;
}

.resource-body {
  min-width: 0;
}

.resource-title {
  font-size: 0.94rem;
  font-weight: 600;
  color: #1e293b;
}

.resource-meta,
.resource-progress-row,
.task-subline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.resource-meta {
  margin-top: 6px;
  font-size: 0.74rem;
  color: #7b8798;
}

.resource-progress-row {
  margin-top: 10px;
  font-size: 0.72rem;
  color: #8b98ab;
}

.resource-progress {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: #ebf0f7;
  overflow: hidden;
}

.resource-progress-bar {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2b6cff, #6f96ff);
}

.task-item {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.task-status {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1.5px solid #d5deeb;
  background: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.task-status.done {
  background: #22c55e;
  border-color: #22c55e;
}

.task-main {
  min-width: 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #edf2f8;
}

.task-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.task-title {
  font-size: 0.88rem;
  color: #27364f;
}

.task-subline {
  margin-top: 6px;
  font-size: 0.75rem;
  color: #8b98ab;
}

.calendar-card {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #edf2f8;
}

.calendar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.calendar-head span {
  font-size: 0.85rem;
  color: #1e293b;
}

.calendar-nav {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.76rem;
  color: #7b8798;
}

.calendar-nav button {
  width: 24px;
  height: 24px;
  border: 1px solid #e1e8f2;
  border-radius: 50%;
  background: #fff;
  color: #7b8798;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px 6px;
}

.calendar-weekday {
  text-align: center;
  font-size: 0.72rem;
  color: #98a2b3;
}

.calendar-day {
  width: 30px;
  height: 30px;
  margin: 0 auto;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #4f5f79;
  font: inherit;
  cursor: pointer;
}

.calendar-day:disabled {
  cursor: default;
}

.calendar-day.active {
  background: #2b6cff;
  color: #fff;
}

.recent-item {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.recent-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  color: #2b6cff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.recent-main {
  min-width: 0;
}

.recent-name {
  font-size: 0.88rem;
  color: #22324b;
  font-weight: 600;
}

.recent-subline {
  margin-top: 5px;
  font-size: 0.74rem;
  color: #8b98ab;
}

.recent-side {
  min-width: 58px;
  text-align: right;
}

.recent-link {
  font-size: 0.74rem;
}

.recent-percent {
  display: block;
  margin-top: 4px;
  font-size: 0.72rem;
  color: #8b98ab;
}

.advice-bar {
  border-radius: 16px;
  padding: 16px 18px;
  background: #fffaf2;
  border-color: #f6dfb5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.advice-copy {
  display: flex;
  align-items: center;
  gap: 12px;
}

.advice-icon {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: #ffe4b7;
  color: #dd8a12;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.advice-copy strong {
  display: block;
  margin-bottom: 2px;
  color: #7b4d00;
}

.advice-copy p {
  color: #9a6a14;
  font-size: 0.84rem;
}

.advice-button {
  border: 1px solid #efc67b;
  background: #fff;
  color: #7b4d00;
}

.assistant-panel {
  padding: 6px 24px 24px 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 18px;
}

.assistant-card {
  border-radius: 20px;
  padding: 18px;
}

.assistant-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.assistant-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  color: #27364f;
}

.assistant-star,
.assistant-collapse {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.assistant-star {
  background: rgba(43, 108, 255, 0.10);
  color: #2b6cff;
}

.assistant-collapse {
  border: 0;
  background: #f1f5fb;
  color: #8b98ab;
}

.assistant-body {
  border: 1px solid #edf2f8;
  border-radius: 18px;
  background: #fafcff;
  padding: 14px;
}

.assistant-greeting {
  margin-bottom: 12px;
  font-size: 0.84rem;
  line-height: 1.7;
  color: #5a6b84;
}

.assistant-question {
  width: 100%;
  min-height: 40px;
  border-radius: 12px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #2b6cff;
  cursor: pointer;
  text-align: left;
}

.assistant-question + .assistant-question {
  margin-top: 10px;
}

.assistant-refresh {
  width: 100%;
  height: 38px;
  margin-top: 12px;
  border: 1px solid #e1e8f2;
  border-radius: 12px;
  background: #fff;
  color: #5f7190;
  font: inherit;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
}

.assistant-input {
  margin-top: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #e1e8f2;
  border-radius: 14px;
  background: #fff;
  padding: 10px 10px 10px 14px;
}

.assistant-input input {
  flex: 1;
  border: 0;
  outline: none;
  background: transparent;
  font: inherit;
  color: #334155;
}

.assistant-input button {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 10px;
  background: #2b6cff;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.assistant-fab {
  margin-left: auto;
  width: 78px;
  height: 78px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, #f8fbff, #d8e7ff 70%);
  border: 1px solid #d6e2f5;
  box-shadow: 0 16px 36px rgba(81, 120, 202, 0.18);
  display: grid;
  place-items: center;
}

.assistant-fab-core {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(180deg, #fff, #eef4ff);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: inset 0 -8px 14px rgba(43, 108, 255, 0.08);
}

.assistant-fab-core span {
  width: 8px;
  height: 12px;
  border-radius: 999px;
  background: radial-gradient(circle at 50% 50%, #77deff 0, #77deff 30%, #275bff 80%, #275bff 100%);
}

@media (max-width: 1220px) {
  .feature-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 980px) {
  .home-page {
    grid-template-columns: 1fr;
  }

  .home-sidebar {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid #e8edf5;
  }

  .sidebar-nav {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .page-header {
    height: auto;
    padding: 16px;
    flex-direction: column;
    align-items: stretch;
  }

  .header-search {
    width: 100%;
  }

  .header-actions {
    justify-content: space-between;
  }

  .page-content,
  .assistant-panel {
    padding: 0 16px 16px;
  }

  .feature-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero-content h1 {
    font-size: 2rem;
  }

  .hero-actions,
  .advice-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .recent-item,
  .resource-item {
    grid-template-columns: 1fr;
  }

  .resource-cover {
    height: 60px;
  }
}
</style>
