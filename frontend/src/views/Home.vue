<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listLessons } from '@/api/lesson'
import { syncUser } from '@/api/platform'
import { trackProgress } from '@/api/progress'
import { useLessonStore } from '@/store/lessonStore'
import { useUserStore } from '@/store/userStore'

const router = useRouter()
const route = useRoute()
const lessonStore = useLessonStore()
const userStore = useUserStore()

const lessons = ref([])
const loadingLessons = ref(false)

const courseCoverUrls = {
  'machine-learning': '/images/course-machine-learning.png',
  '机器学习基础': '/images/course-machine-learning.png',
  algorithm: '/images/course-data-structure.png',
  '数据结构与算法': '/images/course-data-structure.png',
  python: '/images/course-python.png',
  'Python 程序设计': '/images/course-python.png',
}

const fallbackLessons = [
  {
    lessonId: 'ai-intro',
    lessonName: '人工智能导论',
    courseDesc: '第四章 机器学习基础',
    tag: '继续学习',
    progress: 68,
    lessonsDone: 8,
    lessonsTotal: 12,
    weeklyHours: 12,
    coverType: 'python',
  },
  {
    lessonId: 'machine-learning',
    lessonName: '机器学习基础',
    courseDesc: '本周学习 9 小时',
    tag: 'AI 热门',
    progress: 42,
    weeklyHours: 9,
    coverType: 'code',
  },
  {
    lessonId: 'algorithm',
    lessonName: '数据结构与算法',
    courseDesc: '本周学习 6 小时',
    progress: 15,
    weeklyHours: 6,
    accent: '#ff7d79',
    coverType: 'math',
  },
  {
    lessonId: 'python',
    lessonName: 'Python 程序设计',
    courseDesc: '本周学习 8 小时',
    progress: 34,
    weeklyHours: 8,
    coverType: 'python',
  },
]

const tasks = ref([
  { id: 1, text: '完成人工智能导论第三章练习', done: true, badge: '' },
  { id: 2, text: '复习机器学习核心概念', done: false, badge: '今天截止', urgent: true },
  { id: 3, text: 'Python 课后编程作业', done: false, badge: '本周' },
  { id: 4, text: '数据结构错题回顾', done: false, badge: '本周' },
])

const weeklyBars = [
  { day: '一', value: 3.5 },
  { day: '二', value: 5.2 },
  { day: '三', value: 2.1 },
  { day: '四', value: 6.0 },
  { day: '五', value: 4.5 },
  { day: '六', value: 4.8, active: true },
  { day: '日', value: 2.4 },
]

const completedCount = computed(() => tasks.value.filter((task) => task.done).length)

const userName = computed(() => {
  const queryName = normalizeString(route.query.userName)
  const raw = queryName || userStore.userInfo.userName || userStore.userInfo.userId || '王同学'
  return String(Array.isArray(raw) ? raw[0] : raw).trim() || '王同学'
})

const userInitial = computed(() => userName.value.slice(0, 1) || '王')

const todayText = computed(() => {
  const date = new Date()
  const week = ['日', '一', '二', '三', '四', '五', '六'][date.getDay()]
  return `今天是 ${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日，周${week}`
})

const normalizedLessons = computed(() => {
  const source = lessons.value.length ? lessons.value : fallbackLessons
  return source.map((item, index) => normalizeLesson(item, index))
})

const mainCourse = computed(() => normalizedLessons.value[0] || normalizeLesson(fallbackLessons[0], 0))
const courseCards = computed(() => normalizedLessons.value.slice(1, 4))

const recentRecords = computed(() => {
  const records = normalizedLessons.value.slice(0, 2)
  if (!records.length) return []
  return records.map((lesson, index) => ({
    ...lesson,
    icon: index === 0 ? 'play' : 'doc',
    time: index === 0 ? '今天 10:24' : '昨天 16:15',
    meta: index === 0 ? `学习 42 分钟 · 进度 ${lesson.progress}%` : '错题 21 题 · 正确率 30%',
  }))
})

const totalWeeklyHours = computed(() => weeklyBars.reduce((sum, item) => sum + item.value, 0).toFixed(1))
const averageDailyHours = computed(() => (Number(totalWeeklyHours.value) / 7).toFixed(1))

const normalizeString = (value, fallback = '') => {
  if (Array.isArray(value)) return normalizeString(value[0], fallback)
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function getCourseCoverUrl({ lessonId, name }) {
  return courseCoverUrls[lessonId] || courseCoverUrls[name] || ''
}

function inferProgress(item) {
  if (Number.isFinite(Number(item.progress))) return Number(item.progress)
  const status = normalizeString(item.coursewareStatus || item.status).toLowerCase()
  if (['published', 'completed'].includes(status)) return 68
  if (['rendering', 'generating', 'processing'].includes(status)) return 45
  if (['planning', 'plan_ready', 'draft'].includes(status)) return 30
  if (status === 'failed') return 12
  return 34
}

function normalizeLesson(item, index) {
  const fallback = fallbackLessons[index % fallbackLessons.length]
  const lessonId = normalizeString(item.lessonId || item.id, fallback.lessonId)
  const name = normalizeString(item.lessonName || item.name, fallback.lessonName)
  const desc = normalizeString(item.courseDesc || item.desc || item.chapter, fallback.courseDesc)
  const progress = Math.max(0, Math.min(100, Math.round(inferProgress(item))))
  const mappedCoverUrl = getCourseCoverUrl({ lessonId, name })

  return {
    id: lessonId,
    lessonId,
    name,
    chapter: desc,
    tag: normalizeString(item.tag, fallback.tag || ''),
    progress,
    lessonsDone: Number(item.lessonsDone || fallback.lessonsDone || Math.max(1, Math.round(progress / 10))),
    lessonsTotal: Number(item.lessonsTotal || fallback.lessonsTotal || 12),
    weeklyHours: Number(item.weeklyHours || fallback.weeklyHours || Math.max(3, Math.round(progress / 8))),
    accent: normalizeString(item.accent, fallback.accent || '#2f6bf6'),
    coverUrl: mappedCoverUrl || normalizeString(item.coverUrl, fallback.coverUrl || ''),
    coverType: normalizeString(item.coverType, fallback.coverType || ['code', 'math', 'python'][index % 3]),
    status: normalizeString(item.status || item.coursewareStatus, ''),
    renderedPptUrl: normalizeString(item.renderedPptUrl, ''),
  }
}

const barHeight = (value) => `${Math.max(27, value * 12)}px`

async function loadLessons() {
  loadingLessons.value = true
  try {
    const result = await listLessons('', { silent: true })
    lessons.value = Array.isArray(result?.lessons) ? result.lessons : Array.isArray(result) ? result : []
  } catch {
    lessons.value = []
  } finally {
    loadingLessons.value = false
  }
}

async function syncCurrentUser() {
  if (!userStore.userInfo.userId || !userStore.token) return
  try {
    await syncUser({
      silent: true,
      platformId: normalizeString(route.query.platformId, 'chaoxing'),
      userInfo: {
        userId: userStore.userInfo.userId,
        userName: userStore.userInfo.userName,
        role: userStore.userInfo.role || 'student',
        schoolId: userStore.userInfo.schoolId,
      },
    })
  } catch {
    // The home page can render without platform sync; request.js already surfaces failures.
  }
}

async function enterLesson(course = mainCourse.value) {
  lessonStore.setCourseInfo({
    courseId: course.id,
    courseName: course.name,
    courseDesc: course.chapter || '',
  })

  lessonStore.setLessonInfo({
    lessonId: course.lessonId,
  })

  try {
    await trackProgress({
      silent: true,
      schoolId: userStore.userInfo.schoolId || route.query.schoolId,
      userId: userStore.userInfo.userId || route.query.userId,
      courseId: course.id,
      lessonId: course.lessonId,
      progressPercent: course.progress,
    })
  } catch {
    // Do not block navigation if progress tracking is unavailable.
  }

  router.push({
    path: '/pc/lesson/player',
    query: {
      ...route.query,
      courseId: course.id,
      courseName: course.name,
      lessonId: course.lessonId,
    },
  })
}

onMounted(() => {
  syncCurrentUser()
  loadLessons()
})
</script>

<template>
  <div class="study-home">
    <header class="study-header">
      <div>
        <h1>
          上午好，{{ userName }}
          <svg class="sun" viewBox="0 0 64 38" aria-hidden="true">
            <path d="M15 29a17 17 0 0 1 34 0" />
            <path d="M6 29h10M48 29h10M32 3v10M12 10l7 7M52 10l-7 7" />
          </svg>
        </h1>
      </div>
      <div class="header-tools">
        <button class="plain-icon" type="button" aria-label="搜索">
          <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.7-3.7" /></svg>
        </button>
        <button class="plain-icon bell" type="button" aria-label="通知">
          <span></span>
          <svg viewBox="0 0 24 24"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></svg>
        </button>
        <div class="user-badge">{{ userInitial }}</div>
      </div>
    </header>

    <div class="dashboard-grid">
      <main class="dashboard-main">
        <section class="continue-card">
          <div class="continue-copy">
            <span class="section-label">继续学习</span>
            <h2>{{ mainCourse.name }}</h2>
            <p>{{ mainCourse.chapter }}</p>
            <div class="continue-actions">
              <button class="primary-btn" type="button" @click="enterLesson(mainCourse)">
                <svg viewBox="0 0 24 24" width="16" height="16"><circle cx="12" cy="12" r="10" fill="rgba(255,255,255,0.22)" stroke="none" /><path d="M10 8l6 4-6 4V8z" fill="#fff" /></svg>
                继续学习
              </button>
              <button class="secondary-btn" type="button">
                <svg viewBox="0 0 24 24" width="16" height="16"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /><line x1="9" y1="13" x2="15" y2="13" /><line x1="9" y1="17" x2="13" y2="17" /></svg>
                学习笔记
              </button>
            </div>
          </div>

          <div class="continue-visual" aria-hidden="true">
            <img src="/images/progress-goal-card.png" alt="" />
          </div>

          <div class="continue-meta">
            <span>
              <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
              本周学习 {{ mainCourse.weeklyHours }} 小时
            </span>
            <span>
              <svg viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" /></svg>
              已完成 {{ mainCourse.lessonsDone }} / {{ mainCourse.lessonsTotal }} 章
            </span>
            <span class="ai-status">
              <i class="ai-badge">
                <svg viewBox="0 0 24 24" width="14" height="14">
                  <rect x="5" y="8" width="14" height="11" rx="2.5" fill="#fff" />
                  <circle cx="9.5" cy="13" r="1.5" fill="#8b6cef" />
                  <circle cx="14.5" cy="13" r="1.5" fill="#8b6cef" />
                  <line x1="9" y1="8" x2="9" y2="5" stroke="#fff" stroke-width="1.5" stroke-linecap="round" />
                  <line x1="15" y1="8" x2="15" y2="5" stroke="#fff" stroke-width="1.5" stroke-linecap="round" />
                </svg>
              </i>
              AI 助学中
            </span>
          </div>
        </section>

        <section class="course-section">
          <div class="section-title-row">
            <h3>我的课程</h3>
            <button type="button" @click="router.push({ path: '/pc/my-courses', query: route.query })">查看全部 <span>→</span></button>
          </div>
          <div class="course-grid" :class="{ loading: loadingLessons }">
            <article
              v-for="course in courseCards"
              :key="course.id"
              class="course-card"
              @click="enterLesson(course)"
            >
              <div class="course-cover" :class="`cover-${course.coverType}`">
                <img v-if="course.coverUrl" :src="course.coverUrl" :alt="course.name" />
                <template v-else>
                  <span v-if="course.tag" class="course-tag">{{ course.tag }}</span>
                  <div v-if="course.coverType === 'math'" class="math-lines">
                    x<sub>1</sub> + x<sub>2</sub> - 3x<sub>3</sub> = -10<br />
                    6x<sub>2</sub> - 2x<sub>3</sub> + x<sub>4</sub> = 7<br />
                    2x<sub>2</sub> - 3x<sub>4</sub> = 13
                  </div>
                  <div v-if="course.coverType === 'python'" class="python-paper">PYTHON</div>
                </template>
              </div>
              <div class="course-body">
                <h4>{{ course.name }}</h4>
                <div class="course-progress">
                  <div><i :style="{ width: `${course.progress}%`, backgroundColor: course.accent }"></i></div>
                  <em>{{ course.progress }}%</em>
                </div>
                <p>本周学习 {{ course.weeklyHours }} 小时</p>
              </div>
            </article>
          </div>
        </section>

        <section class="suggest-card">
          <div class="suggest-copy">
            <h3>
              <span class="bulb-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M8.2 10.1a4.8 4.8 0 1 1 7.6 3.9c-.7.5-1.1 1.2-1.2 2H9.4c-.1-.8-.5-1.5-1.2-2a4.7 4.7 0 0 1-2-3.9Z" />
                  <path d="M9.5 18h5" />
                  <path d="M10.2 20h3.6" />
                  <path d="M12 13v3" />
                </svg>
              </span>
              学习建议
            </h3>
            <p>
              子网划分专项练习完成情况整体不错，正确率有提升（45%）。<br />
              建议你优先复习错题较多的知识点，同时继续保持每日学习节奏。
            </p>
            <div class="suggest-actions">
              <button class="suggest-practice" type="button" @click="router.push({ path: '/pc/lesson/game', query: route.query })">
                去练习 <span>→</span>
              </button>
              <button class="suggest-errors" type="button" @click="router.push({ path: '/pc/lesson/game', query: { ...route.query, mode: 'mistakes' } })">
                查看错题本 <span>›</span>
              </button>
            </div>
          </div>
          <div class="student-art" aria-hidden="true">
            <img src="/images/study-suggestion.png" alt="" />
          </div>
        </section>
      </main>

      <aside class="dashboard-side">
        <section class="side-card todo-card">
          <div class="side-title">
            <h3>今日待办</h3>
            <button type="button">...</button>
          </div>
          <div class="todo-list">
            <label v-for="task in tasks" :key="task.id" class="todo-item">
              <input v-model="task.done" type="checkbox" />
              <span class="fake-check"></span>
              <strong>{{ task.text }}</strong>
              <em v-if="task.badge" :class="{ urgent: task.urgent }">{{ task.badge }}</em>
            </label>
          </div>
          <p class="task-count">已完成 {{ completedCount }} / {{ tasks.length }} 项</p>
        </section>

        <section class="side-card stats-card">
          <h3>本周学习数据</h3>
          <div class="stats-numbers">
            <div><strong>{{ totalWeeklyHours }}</strong><span>小时</span><p>总学习时长</p></div>
            <div><strong>{{ averageDailyHours }}</strong><span>小时</span><p>日均学习<br /><em>超过 85% 同学</em></p></div>
          </div>
          <div class="bar-chart">
            <div v-for="bar in weeklyBars" :key="bar.day" class="bar-item" :class="{ active: bar.active }">
              <span>{{ bar.value }}</span>
              <i :style="{ height: barHeight(bar.value) }"></i>
              <b>{{ bar.day }}</b>
            </div>
          </div>
        </section>

        <section class="side-card recent-card">
          <h3>最近学习记录</h3>
          <div class="record-list">
            <article v-for="record in recentRecords" :key="record.id" class="record-item">
              <div class="record-icon" :class="record.icon">
                <svg v-if="record.icon === 'play'" viewBox="0 0 24 24"><path d="M9 7v10l8-5-8-5Z" /></svg>
                <svg v-else viewBox="0 0 24 24"><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v5h5" /></svg>
              </div>
              <div>
                <strong>{{ record.name }} <span>· {{ record.chapter }}</span></strong>
                <p>{{ record.meta }}</p>
              </div>
              <time>{{ record.time }}</time>
            </article>
          </div>
          <button class="record-link" type="button">查看全部记录 <span>→</span></button>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
:global(.app-shell--pc) {
  padding: 0;
  background: #f6f8fc;
}

:global(body:has(.study-home)) {
  overflow: hidden;
}

.study-home {
  width: 100%;
  height: calc(100vh / var(--design-scale, 1));
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  row-gap: clamp(12px, calc(1.6vh / var(--design-scale, 1)), 17px);
  overflow: hidden;
  padding: clamp(18px, calc(2.1vh / var(--design-scale, 1)), 23px) 44px 24px 52px;
  color: #111827;
  background: #ecf0f8;
  letter-spacing: 0;
  -webkit-font-smoothing: antialiased;
}

.study-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  max-width: 1760px;
  margin: 0;
}

.study-header h1 {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 0;
  color: #0f172a;
  font-size: 29px;
  font-weight: 850;
  line-height: 1;
  overflow: visible;
}

.study-header p {
  margin: 8px 0 0;
  color: #667286;
  font-size: 13px;
  font-weight: 560;
}

.sun {
  display: block;
  flex: 0 0 48px;
  width: 48px;
  height: 29px;
  margin-left: 2px;
  color: #f5aa1b;
  fill: none;
  stroke: currentColor;
  stroke-width: 3.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  transform: translateY(1px);
}

.header-tools {
  display: flex;
  align-items: center;
  gap: 24px;
  color: #556176;
  padding-top: 0;
}

.plain-icon {
  position: relative;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: 0;
  padding: 0;
  color: inherit;
  background: transparent;
}

.plain-icon svg,
.continue-meta > span > svg,
.record-icon svg {
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.plain-icon svg {
  width: 24px;
  height: 24px;
  stroke-width: 2.1;
}

.ai-badge svg {
  fill: revert;
  stroke: revert;
}

.bell span {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff3b30;
  box-shadow: 0 0 0 2px #f6f9fd;
}

.user-badge {
  width: 43px;
  height: 43px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #1f2937;
  background: #e7ebf2;
  font-size: 19px;
  font-weight: 800;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(860px, 1fr) 520px;
  gap: 28px;
  align-items: stretch;
  width: 100%;
  height: 100%;
  min-height: 0;
  max-width: 1760px;
}

.dashboard-main,
.dashboard-side {
  display: grid;
  gap: clamp(11px, calc(1.35vh / var(--design-scale, 1)), 14px);
  min-height: 0;
}

.dashboard-main {
  grid-template-rows: minmax(220px, 0.86fr) minmax(290px, 1.12fr) minmax(170px, 0.66fr);
}

.dashboard-side {
  grid-template-rows: minmax(205px, 0.82fr) minmax(265px, 1fr) minmax(190px, 0.74fr);
}

.continue-card,
.side-card,
.course-card,
.suggest-card {
  border: 1px solid #e0e6ef;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 4px 20px rgba(30, 50, 90, 0.04);
}

.continue-card {
  position: relative;
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(460px, 0.92fr);
  align-items: center;
  overflow: hidden;
  background: #fff;
}

.continue-copy {
  align-self: stretch;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 26px 32px 58px;
}

.section-label {
  color: #6b7a8d;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
}

.continue-copy h2 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 26px;
  line-height: 1.2;
  font-weight: 800;
}

.continue-copy p {
  margin: 0 0 20px;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
}

.continue-actions {
  display: flex;
  gap: 14px;
}

.primary-btn,
.secondary-btn {
  height: 40px;
  min-width: 0;
  padding: 0 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.primary-btn {
  color: #fff;
  border: 0;
  background: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.primary-btn svg {
  flex-shrink: 0;
}

.secondary-btn {
  color: #475569;
  border: 1px solid #d1d9e4;
  background: #f8fafc;
}

.secondary-btn svg {
  fill: none;
  stroke: #64748b;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}

.continue-visual {
  justify-self: end;
  align-self: center;
  width: min(520px, 100%);
  padding: 0 30px 46px 0;
}

.continue-visual img {
  display: block;
  width: 100%;
  height: auto;
}

.continue-meta {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 48px;
  display: flex;
  align-items: center;
  gap: 0;
  padding: 0 32px;
  border-top: 1px solid #edf1f7;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
}

.continue-meta > span {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-right: 22px;
  margin-right: 22px;
  border-right: 1px solid #e2e8f1;
}

.continue-meta > span:last-child {
  border-right: 0;
  padding-right: 0;
  margin-right: 0;
}

.continue-meta > span svg {
  width: 16px;
  height: 16px;
  stroke-width: 2;
  flex-shrink: 0;
}

.continue-meta > span:nth-child(1) svg {
  color: #3b82f6;
}

.continue-meta > span:nth-child(2) svg {
  color: #22c55e;
  stroke-width: 2.5;
}

.ai-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-badge {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  background: linear-gradient(135deg, #a78bfa, #7c3aed);
  font-style: normal;
  flex-shrink: 0;
}

.ai-badge svg line {
  stroke-linecap: round;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 4px;
}

.course-section {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 2px;
}

.section-title-row h3,
.side-card h3 {
  margin: 0;
  color: #05070d;
  font-size: 20px;
  font-weight: 860;
}

.section-title-row h3 {
  font-size: 19px;
  font-weight: 820;
}

.section-title-row button,
.record-link {
  border: 0;
  padding: 0;
  color: #2f6bf6;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  font-weight: 820;
  cursor: pointer;
}

.section-title-row button {
  color: #536075;
  font-size: 13px;
  font-weight: 650;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  min-height: 0;
  margin-top: -2px;
}

.course-grid.loading {
  opacity: 0.72;
}

.course-card {
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-rows: minmax(138px, 56%) minmax(112px, 1fr);
  overflow: hidden;
  cursor: pointer;
}

.course-cover {
  position: relative;
  height: auto;
  min-height: 0;
  overflow: hidden;
}

.course-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-code {
  background:
    linear-gradient(160deg, rgba(14, 32, 53, 0.32), transparent 42%),
    repeating-linear-gradient(172deg, transparent 0 10px, rgba(89, 230, 190, 0.35) 10px 12px),
    linear-gradient(135deg, #0b2537, #10131d 45%, #544532);
}

.cover-code::after {
  content: "function coffee_speed_eggteee_timer() \A   canvas.draw('#008cc') \A   return data.output to cne nc_ooo";
  white-space: pre;
  position: absolute;
  left: 32px;
  top: 28px;
  color: #ffffff;
  font: 700 12px/1.45 "SFMono-Regular", Consolas, monospace;
  transform: rotate(-17deg);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
}

.cover-math {
  background:
    linear-gradient(0deg, rgba(255, 255, 255, 0.25), rgba(255, 255, 255, 0.25)),
    repeating-linear-gradient(0deg, transparent 0 31px, rgba(60, 60, 60, 0.06) 31px 32px),
    #d9d9d9;
}

.math-lines {
  padding: 10px 34px;
  color: #1c2430;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 23px;
  line-height: 1.42;
}

.cover-python {
  background:
    radial-gradient(circle at 16% 40%, rgba(230, 160, 112, 0.85), transparent 22%),
    radial-gradient(circle at 86% 36%, rgba(47, 107, 246, 0.2), transparent 18%),
    linear-gradient(130deg, #172334, #0b1826 55%, #172338);
}

.python-paper {
  position: absolute;
  left: 94px;
  top: 10px;
  width: 74px;
  height: 70px;
  display: grid;
  place-items: center;
  transform: rotate(7deg);
  background: #fff1c8;
  color: #24506a;
  font-size: 24px;
  font-family: Georgia, serif;
  letter-spacing: 2px;
  box-shadow: 0 8px 14px rgba(0, 0, 0, 0.2);
}

.course-tag {
  position: absolute;
  left: 14px;
  bottom: 8px;
  z-index: 2;
  padding: 4px 10px;
  border-radius: 5px;
  color: #2f6bf6;
  background: #eaf1ff;
  font-size: 12px;
  font-weight: 750;
}

.course-body {
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 13px 20px 14px;
}

.course-body h4 {
  margin: 0 0 13px;
  color: #111827;
  font-size: 16px;
  font-weight: 820;
}

.course-progress {
  display: grid;
  grid-template-columns: 1fr 44px;
  gap: 12px;
  align-items: center;
  margin-bottom: 13px;
}

.course-progress div {
  height: 5px;
  border-radius: 999px;
  background: #e6ebf2;
  overflow: hidden;
}

.course-progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.course-progress em {
  color: #49566b;
  font-size: 13px;
  font-style: normal;
  font-weight: 650;
  text-align: right;
}

.course-body p {
  margin: 0;
  color: #687589;
  font-size: 13px;
  font-weight: 600;
}

.suggest-card {
  position: relative;
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-columns: 1fr 390px;
  align-items: end;
  padding: 0 0 0 32px;
  overflow: hidden;
}

.suggest-copy {
  align-self: center;
  padding: 22px 0;
}

.suggest-copy h3 {
  display: flex;
  align-items: center;
  gap: 13px;
  margin: 0 0 18px;
  color: #05070d;
  font-size: 18px;
  font-weight: 830;
}

.bulb-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background:
    radial-gradient(circle at center, #ffad2f 0 49%, transparent 50%),
    #fff3df;
}

.bulb-icon svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.suggest-copy p {
  max-width: 690px;
  margin: 0 0 18px;
  color: #59667a;
  font-size: 15px;
  line-height: 1.75;
  font-weight: 560;
}

.suggest-actions {
  display: flex;
  align-items: center;
  gap: 34px;
}

.suggest-practice,
.suggest-errors {
  height: 38px;
  border: 0;
  border-radius: 4px;
  font-family: inherit;
  font-size: 15px;
  font-weight: 650;
  cursor: pointer;
}

.suggest-practice {
  min-width: 128px;
  padding: 0 24px;
  color: #fff;
  background: linear-gradient(180deg, #3f7cff, #2f6bf6);
  box-shadow: 0 5px 12px rgba(47, 107, 246, 0.22);
}

.suggest-errors {
  padding: 0;
  color: #4777df;
  background: transparent;
}

.suggest-practice span,
.suggest-errors span {
  margin-left: 6px;
}

.student-art {
  width: 390px;
  height: 100%;
  align-self: end;
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  overflow: hidden;
}

.student-art img {
  display: block;
  width: 100%;
  max-height: 100%;
  object-fit: contain;
  object-position: right bottom;
}

.side-card {
  padding: 20px 30px 18px;
}

.todo-card {
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.side-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.side-title button {
  border: 0;
  color: #59667a;
  background: transparent;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 2px;
}

.todo-item {
  height: 38px;
  display: grid;
  grid-template-columns: 28px 1fr auto;
  gap: 10px;
  align-items: center;
  border-bottom: 1px solid #e8edf4;
  color: #202938;
  font-size: 14px;
  font-weight: 620;
  cursor: pointer;
}

.todo-item input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.fake-check {
  width: 19px;
  height: 19px;
  border-radius: 5px;
  border: 1px solid #d3dce8;
  background: #fff;
}

.todo-item input:checked + .fake-check {
  display: grid;
  place-items: center;
  border: 0;
  color: #fff;
  background: #2f6bf6;
}

.todo-item input:checked + .fake-check::after {
  content: "✓";
  font-size: 13px;
  font-weight: 800;
}

.todo-item strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-item em {
  padding: 6px 10px;
  border-radius: 5px;
  color: #6a7484;
  background: #f0f3f8;
  font-size: 12px;
  font-style: normal;
  font-weight: 780;
}

.todo-item em.urgent {
  color: #ff514f;
  background: #fff0ef;
}

.task-count {
  margin: 9px 0 0;
  color: #657186;
  font-size: 13px;
  font-weight: 650;
}

.stats-card {
  min-height: 0;
  height: 100%;
  padding-bottom: 17px;
  display: flex;
  flex-direction: column;
}

.stats-numbers {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 28px;
  margin: 18px 0 16px;
}

.stats-numbers strong {
  color: #090d15;
  font-size: 26px;
  line-height: 1;
  font-weight: 860;
}

.stats-numbers span {
  margin-left: 4px;
  color: #4b5668;
  font-size: 13px;
  font-weight: 700;
}

.stats-numbers p {
  margin: 8px 0 0;
  color: #7a8595;
  font-size: 12px;
  font-weight: 650;
}

.stats-numbers em {
  color: #22b95f;
  font-style: normal;
  font-weight: 800;
}

.bar-chart {
  flex: 1;
  min-height: 118px;
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 18px;
  align-items: end;
}

.bar-item {
  display: grid;
  justify-items: center;
  gap: 9px;
  color: #59667a;
  font-size: 13px;
  font-weight: 700;
}

.bar-item i {
  width: 34px;
  display: block;
  border-radius: 5px;
  background: linear-gradient(180deg, #e4e9f1, #d8dee8);
}

.bar-item span {
  color: #697589;
  font-size: 12px;
  font-weight: 650;
}

.bar-item.active,
.bar-item.active span,
.bar-item.active b {
  color: #2f6bf6;
}

.bar-item.active i {
  background: linear-gradient(180deg, #3d79ff, #145cf1);
  box-shadow: 0 8px 16px rgba(47, 107, 246, 0.22);
}

.recent-card {
  height: 100%;
  min-height: 0;
  margin-top: 0;
  overflow: hidden;
}

.record-list {
  margin-top: 12px;
}

.record-item {
  display: grid;
  grid-template-columns: 38px 1fr auto;
  gap: 13px;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e7ecf4;
}

.record-item:last-of-type {
  border-bottom: 0;
}

.record-icon {
  width: 33px;
  height: 33px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: #fff;
  background: #5b8dff;
}

.record-icon.doc {
  background: #ffc064;
}

.record-icon svg {
  width: 17px;
  height: 17px;
  stroke-width: 2.4;
}

.record-item strong {
  display: block;
  max-width: 245px;
  margin-bottom: 5px;
  color: #273142;
  font-size: 13px;
  font-weight: 820;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-item strong span {
  color: #596579;
  font-weight: 650;
}

.record-item p {
  margin: 0;
  color: #687589;
  font-size: 12px;
  font-weight: 630;
}

.record-item time {
  color: #5f6b7e;
  font-size: 13px;
  font-weight: 650;
  white-space: nowrap;
}

.record-link {
  margin-top: 7px;
}

button {
  font-family: inherit;
}

@media (max-width: 1280px) {
  :global(body:has(.study-home)) {
    overflow: auto;
  }

  .study-home {
    height: auto;
    min-height: 100vh;
    overflow: visible;
    padding: 28px;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-side {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .recent-card {
    grid-column: 1 / -1;
  }
}
</style>
