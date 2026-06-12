<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listLessons } from '@/api/lesson'
import { syncUser } from '@/api/platform'
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
  algorithm: '/images/course-data-structure.png',
  python: '/images/course-python.png',
}

const fallbackLessons = [
  {
    lessonId: 'teacher-current',
    lessonName: '\u8ba1\u7b97\u673a\u7f51\u7edc',
    courseDesc: '\u7b2c5\u7ae0 \u4f20\u8f93\u5c42\u534f\u8bae · \u672c\u5468\u6388\u8bfe\u91cd\u70b9',
    tag: '\u7ee7\u7eed\u6388\u8bfe',
    progress: 68,
    lessonsDone: 8,
    lessonsTotal: 12,
    weeklyHours: 12,
    coverType: 'python',
  },
  {
    lessonId: 'machine-learning',
    lessonName: '\u673a\u5668\u5b66\u4e60\u57fa\u7840',
    courseDesc: '32 \u540d\u5b66\u751f\u5df2\u52a0\u5165',
    tag: '\u5907\u8bfe\u4e2d',
    progress: 78,
    weeklyHours: 9,
    coverType: 'code',
  },
  {
    lessonId: 'algorithm',
    lessonName: '\u6570\u636e\u7ed3\u6784\u4e0e\u7b97\u6cd5',
    courseDesc: '24 \u4efd\u4f5c\u4e1a\u5f85\u6279\u6539',
    progress: 55,
    weeklyHours: 6,
    accent: '#ff7d79',
    coverType: 'math',
  },
  {
    lessonId: 'python',
    lessonName: 'Python \u7a0b\u5e8f\u8bbe\u8ba1',
    courseDesc: '\u8bfe\u4ef6\u5df2\u53d1\u5e03',
    progress: 86,
    weeklyHours: 8,
    coverType: 'python',
  },
]
const tasks = ref([
  { id: 1, text: '\u68c0\u67e5\u7b2c\u56db\u7ae0\u5269\u4f59\u6559\u5b66\u5185\u5bb9', done: true, badge: '' },
  { id: 2, text: '\u66f4\u65b0\u673a\u5668\u5b66\u4e60\u57fa\u7840\u8bfe\u4ef6', done: false, badge: '\u4eca\u5929\u622a\u6b62', urgent: true },
  { id: 3, text: '\u6279\u6539 Python \u8bfe\u540e\u7f16\u7a0b\u4f5c\u4e1a', done: false, badge: '\u672c\u5468' },
  { id: 4, text: '\u67e5\u770b\u6570\u636e\u7ed3\u6784\u9519\u9898\u5206\u5e03', done: false, badge: '\u672c\u5468' },
])
const completedCount = computed(() => tasks.value.filter((task) => task.done).length)

const userName = computed(() => {
  const queryName = normalizeString(route.query.userName)
  const raw = queryName || userStore.userInfo.userName || userStore.userInfo.userId || '\u738b\u8001\u5e08'
  return String(Array.isArray(raw) ? raw[0] : raw).trim() || '\u738b\u8001\u5e08'
})

const userInitial = computed(() => userName.value.slice(0, 1) || '\u6559')

const teacherOverview = [
  { id: 1, label: '\u5728\u5b66\u5b66\u751f', value: '128', unit: '\u4eba' },
  { id: 2, label: '\u6559\u5b66\u73ed\u7ea7', value: '6', unit: '\u4e2a' },
  { id: 3, label: '\u5f85\u6279\u4f5c\u4e1a', value: '24', unit: '\u4efd' },
]

const overviewMetrics = [
  { id: 'classes', label: '\u6388\u8bfe\u73ed\u7ea7', value: '3', unit: '\u4e2a\u73ed\u7ea7', note: '128 \u540d\u5b66\u751f', icon: 'users' },
  { id: 'homework', label: '\u5f85\u6279\u6539\u4f5c\u4e1a', value: '24', unit: '\u4efd', note: '\u5f85\u6279\u6539', icon: 'paper' },
  { id: 'quiz', label: '\u6d4b\u9a8c/\u8003\u8bd5', value: '1', unit: '\u4e2a\u6d4b\u9a8c', note: '\u5f85\u67e5\u770b\u7ed3\u679c', icon: 'check' },
  { id: 'discussion', label: '\u8bfe\u5802\u4e92\u52a8', value: '86', unit: '\u6761', note: '\u672c\u5468\u8ba8\u8bba\u6570', icon: 'chat' },
]

const teachingDataStats = [
  { id: 'hours', label: '\u603b\u6559\u5b66\u65f6\u957f', value: '28.5', unit: '\u5c0f\u65f6', icon: 'clock' },
  { id: 'complete', label: '\u5e73\u5747\u5b8c\u6210\u7387', value: '85', unit: '%', icon: 'gauge' },
  { id: 'engage', label: '\u5b66\u751f\u53c2\u4e0e\u7387', value: '78', unit: '%', icon: 'users' },
  { id: 'rating', label: '\u6559\u5b66\u6ee1\u610f\u5ea6', value: '4.8', unit: '/ 5', icon: 'star' },
]

const demoCourseCards = [
  {
    lessonId: 'computer-network',
    name: '\u8ba1\u7b97\u673a\u7f51\u7edc',
    chapter: '\u7b2c5\u7ae0 \u4f20\u8f93\u5c42\u534f\u8bae',
    progress: 78,
    weeklyHours: 9,
    students: 128,
    classes: 3,
    accent: '#2f6bf6',
    coverUrl: '/images/course-machine-learning.png',
    coverType: 'code',
  },
  {
    lessonId: 'data-structure',
    name: '\u6570\u636e\u7ed3\u6784\u4e0e\u7b97\u6cd5',
    chapter: '\u7b2c6\u7ae0 \u6811\u4e0e\u56fe',
    progress: 55,
    weeklyHours: 6,
    students: 96,
    classes: 2,
    accent: '#ff7d79',
    coverUrl: '/images/course-data-structure.png',
    coverType: 'math',
  },
  {
    lessonId: 'python-programming',
    name: 'Python \u7a0b\u5e8f\u8bbe\u8ba1',
    chapter: '\u7b2c8\u7ae0 \u51fd\u6570\u4e0e\u6a21\u5757',
    progress: 86,
    weeklyHours: 8,
    students: 156,
    classes: 4,
    accent: '#2f6bf6',
    coverUrl: '/images/course-python.png',
    coverType: 'python',
  },
]

const teachingTrend = [
  { day: '\u4e00', value: 3.2, x: 8, y: 72 },
  { day: '\u4e8c', value: 4.1, x: 22, y: 58 },
  { day: '\u4e09', value: 2.8, x: 36, y: 78 },
  { day: '\u56db', value: 5.6, x: 50, y: 34 },
  { day: '\u4e94', value: 4.3, x: 64, y: 56 },
  { day: '\u516d', value: 6.8, x: 78, y: 18, active: true },
  { day: '\u65e5', value: 3.4, x: 92, y: 68 },
]

const teachingTrendPath = `M ${teachingTrend.map((item) => `${item.x} ${item.y}`).join(' L ')}`

const recentTeachingRecords = [
  { id: 'publish-homework', icon: 'play', title: '\u53d1\u5e03\u4e86\u300a\u7b2c5\u7ae0\u8bfe\u540e\u4f5c\u4e1a\u300b', meta: '2\u73ed\u30013\u73ed\u30014\u73ed', time: '\u4eca\u5929 10:24' },
  { id: 'quiz-graded', icon: 'doc', title: '\u5b8c\u6210\u300a\u7b2c5\u7ae0\u968f\u5802\u6d4b\u9a8c\u300b\u6279\u6539', meta: '96 \u4efd\u5df2\u6279\u6539', time: '\u4eca\u5929 09:15' },
  { id: 'resource-update', icon: 'file', title: '\u66f4\u65b0\u4e86\u8bfe\u7a0b\u8d44\u6599\u300a\u4f20\u8f93\u5c42\u534f\u8bae\u8be6\u89e3\u300b', meta: '\u8d44\u6e90\u7a7a\u95f4', time: '\u6628\u5929 16:45' },
]

const todayFocusItems = [
  { id: 'grade', title: '\u6279\u6539\u4f5c\u4e1a', desc: '24 \u4efd\u4f5c\u4e1a\u5f85\u6279\u6539', icon: 'check' },
  { id: 'notice', title: '\u53d1\u5e03\u901a\u77e5', desc: '\u5411\u6240\u6709\u73ed\u7ea7\u53d1\u5e03\u8bfe\u7a0b\u901a\u77e5', icon: 'megaphone' },
  { id: 'analytics', title: '\u67e5\u770b\u8bfe\u5802\u6570\u636e', desc: '\u5206\u6790\u672c\u5468\u8bfe\u5802\u8868\u73b0', icon: 'chart' },
  { id: 'adjust', title: '\u8c03\u6574\u6559\u5b66\u8fdb\u5ea6', desc: '\u7b2c5\u7ae0\u5269\u4f59\u8bfe\u7a0b\u5b89\u6392', icon: 'calendar' },
]

const activityItems = [
  { id: 'reply', title: '\u8bfe\u7a0b\u7b54\u7591\u63d0\u9192', desc: '\u6709 3 \u6761\u65b0\u7b54\u7591\u5f85\u56de\u590d', time: '10:15', tone: 'blue' },
  { id: 'class', title: '2 \u73ed\u8bfe\u5802\u4e92\u52a8\u6d3b\u8dc3', desc: '\u8ba8\u8bba\u6570\u8f83\u6628\u65e5\u589e\u957f 35%', time: '09:42', tone: 'green' },
  { id: 'homework', title: '\u4f5c\u4e1a\u63d0\u4ea4\u63d0\u9192', desc: '\u300a\u7b2c5\u7ae0\u8bfe\u540e\u4f5c\u4e1a\u300b\u6709 18 \u4eba\u672a\u63d0\u4ea4', time: '\u6628\u5929', tone: 'orange' },
  { id: 'quiz', title: '\u6d4b\u9a8c\u7ed3\u679c\u5df2\u751f\u6210', desc: '\u300a\u7b2c5\u7ae0\u968f\u5802\u6d4b\u9a8c\u300b\u7ed3\u679c\u53ef\u67e5\u770b', time: '\u6628\u5929', tone: 'purple' },
]

const todayText = computed(() => {
  const date = new Date()
  const week = ['\u65e5', '\u4e00', '\u4e8c', '\u4e09', '\u56db', '\u4e94', '\u516d'][date.getDay()]
  return `\u4eca\u5929\u662f ${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}\uff0c\u5468${week}`
})
const normalizedLessons = computed(() => {
  const source = lessons.value.length ? lessons.value : fallbackLessons
  return source.map((item, index) => normalizeLesson(item, index))
})

const mainCourse = computed(() => normalizedLessons.value[0] || normalizeLesson(fallbackLessons[0], 0))
const courseCards = computed(() => demoCourseCards)

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
        role: userStore.userInfo.role || 'teacher',
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

  router.push({
    path: '/pc/teacher/script-editor',
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
          &#19978;&#21320;&#22909;&#65292;{{ userName }}
          <svg class="sun" viewBox="0 0 64 38" aria-hidden="true">
            <path d="M15 29a17 17 0 0 1 34 0" />
            <path d="M6 29h10M48 29h10M32 3v10M12 10l7 7M52 10l-7 7" />
          </svg>
        </h1>
      </div>
      <div class="header-tools">
        <button class="plain-icon" type="button" aria-label="鎼滅储">
          <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.7-3.7" /></svg>
        </button>
        <button class="plain-icon bell" type="button" aria-label="閫氱煡">
          <span></span>
          <svg viewBox="0 0 24 24"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></svg>
        </button>
        <div class="user-badge">{{ userInitial }}</div>
      </div>
    </header>

    <div class="dashboard-grid">
      <section class="teacher-top-grid">
        <article class="teacher-panel overview-panel">
          <div class="top-panel-title">
            <h3>本周教学概览</h3>
            <span>进行中</span>
          </div>
          <div class="overview-body">
            <div class="overview-course">
              <div class="overview-course-cover">
                <img v-if="mainCourse.coverUrl" :src="mainCourse.coverUrl" :alt="mainCourse.name" />
                <div v-else class="overview-course-fallback"></div>
                <div>
                  <h4>{{ mainCourse.name }}</h4>
                  <p>{{ mainCourse.chapter }}</p>
                </div>
              </div>
              <div class="overview-progress">
                <span>教学进度</span>
                <div><i :style="{ width: `${mainCourse.progress}%` }"></i></div>
                <strong>{{ mainCourse.progress }}%</strong>
              </div>
              <p class="overview-sub">本周已授课 {{ mainCourse.lessonsDone || 3 }} / {{ mainCourse.lessonsTotal || 4 }} 课时</p>
            </div>
            <div class="overview-metrics">
              <div v-for="item in overviewMetrics" :key="item.id" class="metric-tile">
                <span class="metric-icon">
                  <svg v-if="item.icon === 'users'" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 11.5a3.5 3.5 0 1 0 0-7" /></svg>
                  <svg v-else-if="item.icon === 'paper'" viewBox="0 0 24 24"><path d="M7 3h10l3 3v15H4V3h3Z" /><path d="M14 3v5h6M8 13h8M8 17h5" /></svg>
                  <svg v-else-if="item.icon === 'check'" viewBox="0 0 24 24"><path d="M7 3h10l3 3v15H4V3h3Z" /><path d="m8 15 2.5 2.5L16 12" /></svg>
                  <svg v-else viewBox="0 0 24 24"><path d="M4 5h16v12H7l-3 3V5Z" /><path d="M8 9h8M8 13h5" /></svg>
                </span>
                <div>
                  <p>{{ item.label }}</p>
                  <strong>{{ item.value }} <em>{{ item.unit }}</em></strong>
                  <small>{{ item.note }}</small>
                </div>
              </div>
            </div>
          </div>
          <div class="overview-actions">
            <button class="primary-btn" type="button" @click="enterLesson(mainCourse)">
              <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7Z" /></svg>
              进入课程
            </button>
            <button class="secondary-btn" type="button" @click="router.push({ path: '/pc/teacher/upload', query: route.query })">
              <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
              发布作业
            </button>
            <button class="secondary-btn" type="button">
              <svg viewBox="0 0 24 24"><path d="M7 3h10l3 3v15H4V3h3Z" /><path d="M8 13h8M8 17h5" /></svg>
              发起测验
            </button>
            <button class="secondary-btn" type="button">
              <svg viewBox="0 0 24 24"><rect x="5" y="8" width="14" height="10" rx="3" /><path d="M12 8V5M9 13h.01M15 13h.01" /></svg>
              备课助手
            </button>
          </div>
        </article>

        <article class="teacher-panel focus-panel">
          <h3>今日待办</h3>
          <div class="focus-list">
            <button v-for="item in todayFocusItems" :key="item.id" type="button" class="focus-item">
              <span>
                <svg v-if="item.icon === 'check'" viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg>
                <svg v-else-if="item.icon === 'megaphone'" viewBox="0 0 24 24"><path d="M3 11v2a2 2 0 0 0 2 2h3l5 4V5L8 9H5a2 2 0 0 0-2 2Z" /><path d="M16 9a4 4 0 0 1 0 6" /></svg>
                <svg v-else-if="item.icon === 'chart'" viewBox="0 0 24 24"><path d="M4 19V5M4 19h16" /><path d="M8 16v-5M13 16V8M18 16v-7" /></svg>
                <svg v-else viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M8 2v4M16 2v4M3 10h18" /></svg>
              </span>
              <strong>{{ item.title }}</strong>
              <em>{{ item.desc }}</em>
            </button>
          </div>
          <button class="panel-link" type="button">查看全部待办 <span>→</span></button>
        </article>

        <article class="teacher-panel activity-panel">
          <h3>课程提醒 / 班级动态</h3>
          <div class="activity-list">
            <div v-for="item in activityItems" :key="item.id" class="activity-item">
              <span :class="['activity-icon', item.tone]">
                <svg viewBox="0 0 24 24"><path d="M8 5h8l4 4v10H4V5h4Z" /><path d="M8 13h8M8 17h5" /></svg>
              </span>
              <div>
                <strong>{{ item.title }}</strong>
                <p>{{ item.desc }}</p>
              </div>
              <time>{{ item.time }}</time>
            </div>
          </div>
          <button class="panel-link" type="button">查看全部动态 <span>→</span></button>
        </article>
      </section>

      <main class="dashboard-main">
        <section class="course-section">
          <div class="section-title-row">
            <h3>我的课程</h3>
            <button type="button" @click="router.push({ path: '/pc/teacher/resources', query: route.query })">管理课程 <span>›</span></button>
          </div>
          <div class="course-grid" :class="{ loading: loadingLessons }">
            <article
              v-for="course in courseCards"
              :key="course.lessonId"
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
                <div class="course-meta-row">
                  <span>
                    <svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /></svg>
                    {{ course.classes }} 个班级
                  </span>
                  <span>
                    <svg viewBox="0 0 24 24"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /></svg>
                    {{ course.students }} 名学生
                  </span>
                </div>
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
              &#25945;&#23398;&#24314;&#35758;
            </h3>
            <p>
              &#26412;&#21608;&#26426;&#22120;&#23398;&#20064;&#22522;&#30784;&#31456;&#33410;&#25972;&#20307;&#25484;&#25569;&#24230;&#36739;&#22909;&#65292;&#20173;&#26377; 24 &#20221;&#20316;&#19994;&#38656;&#35201;&#20851;&#27880;&#12290;<br />
              &#24314;&#35758;&#35838;&#21069;&#20808;&#35762;&#35299;&#39640;&#39057;&#38169;&#39064;&#65292;&#20877;&#32467;&#21512; AI &#21161;&#25945;&#29983;&#25104;&#19968;&#32452;&#20998;&#23618;&#32451;&#20064;&#12290;
            </p>
            <div class="suggest-actions">
              <button class="suggest-practice" type="button" @click="router.push({ path: '/pc/teacher/upload', query: route.query })">
                &#21019;&#24314;&#35838;&#31243; <span>&#8594;</span>
              </button>
              <button class="suggest-errors" type="button" @click="router.push({ path: '/pc/learning-analytics', query: route.query })">
                &#26597;&#30475;&#23398;&#24773; <span>&#8250;</span>
              </button>
            </div>
          </div>
          <div class="student-art" aria-hidden="true">
            <img src="/images/teacher-suggestion-laptop.png" alt="" />
          </div>
        </section>
      </main>

      <aside class="dashboard-side">
        <section class="side-card stats-card">
          <div class="stats-head">
            <h3>教学数据概览</h3>
            <button type="button">本周 <span>⌄</span></button>
          </div>
          <div class="teaching-data-row">
            <div v-for="item in teachingDataStats" :key="item.id">
              <span class="data-icon">
                <svg v-if="item.icon === 'clock'" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
                <svg v-else-if="item.icon === 'gauge'" viewBox="0 0 24 24"><path d="M4 14a8 8 0 1 1 16 0" /><path d="m12 14 4-4" /><path d="M6 20h12" /></svg>
                <svg v-else-if="item.icon === 'users'" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /></svg>
                <svg v-else viewBox="0 0 24 24"><path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1L12 16.9 6.6 19.8l1-6.1-4.4-4.3 6.1-.9L12 3Z" /></svg>
              </span>
              <strong>{{ item.value }}</strong><span>{{ item.unit }}</span>
              <p>{{ item.label }}</p>
            </div>
          </div>
          <h3 class="activity-heading">本周课堂活跃趋势 <span>ⓘ</span></h3>
          <p class="trend-unit">互动数（条）</p>
          <div class="trend-chart">
            <svg viewBox="0 0 100 88" preserveAspectRatio="none" aria-hidden="true">
              <defs>
                <linearGradient id="teacherTrendFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#2f6bf6" stop-opacity="0.22" />
                  <stop offset="100%" stop-color="#2f6bf6" stop-opacity="0.02" />
                </linearGradient>
              </defs>
              <path :d="`${teachingTrendPath} L 92 86 L 8 86 Z`" fill="url(#teacherTrendFill)" />
              <path :d="teachingTrendPath" fill="none" stroke="#2f6bf6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
              <circle v-for="item in teachingTrend" :key="item.day" :cx="item.x" :cy="item.y" :r="item.active ? 2.4 : 1.8" fill="#fff" stroke="#2f6bf6" stroke-width="1.4" vector-effect="non-scaling-stroke" />
            </svg>
            <div class="trend-values">
              <span v-for="item in teachingTrend" :key="`value-${item.day}`" :class="{ active: item.active }">{{ item.value }}</span>
            </div>
            <div class="trend-days">
              <span v-for="item in teachingTrend" :key="`day-${item.day}`" :class="{ active: item.active }">{{ item.day }}</span>
            </div>
          </div>
        </section>

        <section class="side-card recent-card">
          <h3>最近教学记录</h3>
          <div class="record-list">
            <article v-for="record in recentTeachingRecords.slice(0, 2)" :key="record.id" class="record-item">
              <div class="record-icon" :class="record.icon">
                <svg v-if="record.icon === 'play'" viewBox="0 0 24 24"><path d="M9 7v10l8-5-8-5Z" /></svg>
                <svg v-else viewBox="0 0 24 24"><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v5h5" /></svg>
              </div>
              <div>
                <strong>{{ record.title }}</strong>
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
  row-gap: clamp(8px, calc(1.05vh / var(--design-scale, 1)), 12px);
  overflow: hidden;
  padding: clamp(10px, calc(1.35vh / var(--design-scale, 1)), 16px) 44px 20px 52px;
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
  grid-template-columns: minmax(880px, 1fr) minmax(430px, 500px);
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px 22px;
  align-items: stretch;
  width: 100%;
  height: 100%;
  min-height: 0;
  max-width: 1760px;
}

.teacher-top-grid {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: minmax(630px, 1.38fr) minmax(260px, 0.56fr) minmax(390px, 0.85fr);
  gap: 18px;
  min-height: 0;
}

.teacher-panel {
  border: 1px solid #e0e6ef;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 4px 20px rgba(30, 50, 90, 0.04);
}

.top-panel-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.top-panel-title h3,
.teacher-panel h3 {
  margin: 0;
  color: #05070d;
  font-size: 18px;
  font-weight: 860;
}

.top-panel-title span {
  padding: 4px 10px;
  border-radius: 999px;
  color: #17a65a;
  background: #dcf8e7;
  font-size: 12px;
  font-weight: 800;
}

.overview-panel {
  padding: 20px 24px 16px;
}

.overview-body {
  display: grid;
  grid-template-columns: minmax(260px, 0.84fr) minmax(300px, 1fr);
  gap: 24px;
  align-items: stretch;
}

.overview-course {
  min-width: 0;
  border: 1px solid #e0e7f1;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}

.overview-course-cover {
  position: relative;
  height: 116px;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(135deg, #0d2a76, #103b91);
}

.overview-course-cover img,
.overview-course-fallback {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.overview-course-fallback {
  background:
    radial-gradient(circle at 76% 32%, rgba(80, 160, 255, 0.7), transparent 4%),
    radial-gradient(circle at 62% 52%, rgba(80, 160, 255, 0.6), transparent 3%),
    linear-gradient(135deg, #12337d, #081d54);
}

.overview-course-cover div:last-child {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 18px;
  background: linear-gradient(90deg, rgba(7, 22, 65, 0.55), rgba(7, 22, 65, 0.12));
}

.overview-course h4 {
  margin: 0 0 10px;
  font-size: 22px;
  font-weight: 900;
}

.overview-course p {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}

.overview-progress {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 13px 16px 0;
  color: #4f5d73;
  font-size: 13px;
  font-weight: 700;
}

.overview-progress div {
  height: 5px;
  border-radius: 999px;
  background: #e6ebf2;
  overflow: hidden;
}

.overview-progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #2f6bf6;
}

.overview-progress strong {
  color: #24324a;
}

.overview-sub {
  padding: 12px 16px 14px;
  color: #687589;
  font-size: 13px;
  font-weight: 650;
}

.overview-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.metric-tile {
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 12px;
  align-items: center;
  padding: 14px;
  border: 1px solid #e0e7f1;
  border-radius: 10px;
  background: #fff;
}

.metric-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  color: #2f6bf6;
  background: #edf4ff;
}

.metric-icon svg,
.focus-item svg,
.activity-icon svg {
  width: 21px;
  height: 21px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.1;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.metric-tile p {
  margin: 0 0 4px;
  color: #5f6d82;
  font-size: 12px;
  font-weight: 700;
}

.metric-tile strong {
  display: block;
  color: #111827;
  font-size: 20px;
  font-weight: 880;
  line-height: 1.05;
}

.metric-tile em {
  color: #39465a;
  font-size: 13px;
  font-style: normal;
  font-weight: 700;
}

.metric-tile small {
  display: block;
  margin-top: 5px;
  color: #687589;
  font-size: 12px;
  font-weight: 650;
}

.overview-actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 16px;
}

.focus-panel,
.activity-panel {
  padding: 20px 22px 17px;
}

.focus-list {
  display: grid;
  gap: 12px;
  margin-top: 17px;
}

.focus-item {
  display: grid;
  grid-template-columns: 34px 1fr;
  column-gap: 12px;
  row-gap: 2px;
  border: 0;
  padding: 0;
  text-align: left;
  color: inherit;
  background: transparent;
  font-family: inherit;
}

.focus-item span {
  grid-row: span 2;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  color: #5d6d84;
}

.focus-item svg {
  width: 22px;
  height: 22px;
}

.focus-item strong,
.activity-item strong {
  color: #182033;
  font-size: 14px;
  font-weight: 820;
}

.focus-item em,
.activity-item p {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  font-style: normal;
  font-weight: 650;
}

.panel-link {
  margin-top: 18px;
  border: 0;
  padding: 0;
  color: #2f6bf6;
  background: transparent;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
}

.activity-list {
  margin-top: 17px;
}

.activity-item {
  display: grid;
  grid-template-columns: 38px 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #e8edf4;
}

.activity-item:last-child {
  border-bottom: 0;
}

.activity-icon {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: #fff;
}

.activity-icon.blue { background: #3b82f6; }
.activity-icon.green { background: #35be75; }
.activity-icon.orange { background: #ffad3d; }
.activity-icon.purple { background: #8b5cf6; }

.activity-icon svg {
  width: 17px;
  height: 17px;
}

.activity-item time {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.dashboard-main,
.dashboard-side {
  display: grid;
  gap: clamp(11px, calc(1.35vh / var(--design-scale, 1)), 14px);
  min-height: 0;
}

.dashboard-main {
  grid-column: 1;
  grid-row: 2;
  grid-template-rows: minmax(320px, 1.05fr) minmax(198px, 0.56fr);
}

.dashboard-side {
  grid-column: 2;
  grid-row: 2;
  grid-template-rows: minmax(300px, 0.98fr) minmax(198px, 0.54fr);
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
  height: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  background: #fff;
}

.continue-card-old {
  display: none;
}

.continue-card-redesign {
  border-radius: 14px;
  border-color: #dde5f0;
  background: #fff;
  box-shadow: 0 5px 18px rgba(30, 50, 90, 0.04);
}

.continue-main {
  flex: 0 0 auto;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(420px, 1fr) minmax(390px, 420px);
  align-items: stretch;
  justify-content: space-between;
  gap: 30px;
  padding: 18px 32px 12px;
}

.continue-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-width: 500px;
  min-height: 150px;
  padding: 0;
}

.section-label {
  align-self: flex-start;
  padding: 6px 12px;
  border-radius: 8px;
  color: #155ac7;
  background: #e6f0ff;
  font-size: 14px;
  font-weight: 850;
  line-height: 1;
  margin-bottom: 11px;
}

.continue-copy h2 {
  margin: 0 0 7px;
  color: #0f172a;
  font-size: 30px;
  line-height: 1.05;
  font-weight: 900;
}

.continue-copy p {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 0 0 15px;
  color: #5e6675;
  font-size: 15px;
  font-weight: 520;
}

.continue-copy p i {
  width: 1px;
  height: 18px;
  background: #d6dce6;
}

.continue-actions {
  display: flex;
  gap: 14px;
}

.primary-btn,
.secondary-btn {
  height: 42px;
  min-width: 126px;
  padding: 0 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 760;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.primary-btn {
  color: #fff;
  border: 0;
  background: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.primary-btn svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}

.secondary-btn {
  color: #384153;
  border: 1px solid #d1d9e4;
  background: #fff;
}

.secondary-btn svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: #5d6678;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}

.week-plan-card {
  align-self: stretch;
  width: 100%;
  min-height: 150px;
  padding: 15px 18px 12px;
  border: 1px solid #dfe6f0;
  border-radius: 12px;
  color: #4f5868;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 251, 255, 0.92));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.95), 0 10px 24px rgba(30, 50, 90, 0.04);
}

.week-plan-card h3 {
  margin: 0 0 11px;
  color: #101827;
  font-size: 18px;
  font-weight: 880;
}

.week-plan-card ul {
  list-style: none;
  display: grid;
  gap: 7px;
  margin: 0;
  padding: 0 0 10px;
  border-bottom: 1px solid #e3e7ef;
}

.week-plan-card li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #5d6573;
  font-size: 13px;
  font-weight: 520;
}

.week-plan-card li span {
  width: 17px;
  height: 17px;
  border: 2px solid #aab4c2;
  border-radius: 50%;
  flex-shrink: 0;
}

.week-plan-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 9px;
  color: #5f6878;
  font-size: 11px;
  font-weight: 540;
  white-space: nowrap;
}

.week-plan-foot span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.week-plan-foot svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: #667085;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.week-plan-foot i {
  width: 1px;
  height: 18px;
  background: #dce1ea;
}

.continue-visual {
  justify-self: end;
  align-self: center;
  width: min(570px, 100%);
  height: calc(100% - 50px);
  max-height: 304px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 20px 44px 0;
}

.continue-visual img {
  display: block;
  width: auto;
  height: 100%;
  max-width: 100%;
  max-height: 292px;
  object-fit: contain;
}

.continue-meta {
  position: static;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 24px 0 28px;
  border-top: 1px solid #edf1f7;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  background: #fbfcff;
}

.continue-meta > span {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1 1 0;
  min-width: 0;
  height: auto;
  padding: 0 16px 0 0;
  margin-right: 0;
  border: 0;
  border-right: 1px solid #e2e8f1;
  border-radius: 0;
  background: transparent;
}

.continue-meta > span:last-child {
  border: 0;
  padding-right: 0;
  margin-right: 0;
}

.continue-meta > span svg {
  width: 28px;
  height: 28px;
  color: #1f63c6;
  stroke-width: 1.9;
  flex-shrink: 0;
}

.overview-stat b {
  display: block;
  color: #4e5666;
  font-style: normal;
  font-weight: 520;
  line-height: 1.12;
  white-space: nowrap;
}

.overview-stat strong {
  margin-right: 5px;
  color: #2f6bf6;
  font-size: 26px;
  line-height: 1;
  font-weight: 850;
  vertical-align: baseline;
}

.overview-stat em {
  display: block;
  margin-top: 2px;
  color: #4e5666;
  font-size: 12px;
  font-style: normal;
  font-weight: 520;
  white-space: nowrap;
}

.ai-assistant-pill {
  height: 40px;
  min-width: 156px;
  border: 0;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #3e4553;
  background: #f1f5fa;
  font-family: inherit;
  font-size: 14px;
  font-weight: 720;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.86);
}

.ai-assistant-pill svg {
  width: 19px;
  height: 19px;
  fill: none;
  stroke: #2f6bf6;
  stroke-width: 2.1;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.ai-assistant-pill svg:last-child {
  width: 17px;
  height: 17px;
  stroke: #9aa3b3;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0;
}

.course-section {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  padding: 18px 22px 18px;
  border: 1px solid #e0e6ef;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 4px 20px rgba(30, 50, 90, 0.04);
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
  gap: 28px;
  min-height: 0;
  margin-top: 0;
}

.course-grid.loading {
  opacity: 0.72;
}

.course-card {
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-rows: minmax(128px, 56%) minmax(82px, 1fr);
  overflow: hidden;
  border: 1px solid #e0e6ef;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 3px 12px rgba(30, 50, 90, 0.035);
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
  justify-content: flex-start;
  padding: 10px 16px 11px;
}

.course-body h4 {
  margin: 0;
  color: #111827;
  font-size: 16px;
  font-weight: 820;
}

.course-progress {
  display: grid;
  grid-template-columns: 1fr 44px;
  gap: 12px;
  align-items: center;
  order: 2;
  margin: 10px 0 8px;
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

.course-meta-row {
  order: 3;
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: auto;
  margin-bottom: 0;
  color: #5f6d82;
  font-size: 12px;
  font-weight: 650;
}

.course-meta-row span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.course-meta-row svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.suggest-card {
  position: relative;
  min-height: 198px;
  height: 100%;
  display: grid;
  grid-template-columns: minmax(430px, 1fr) 460px;
  align-items: stretch;
  padding: 10px 0 8px 30px;
  overflow: hidden;
}

.suggest-copy {
  align-self: center;
  min-width: 0;
  padding: 0;
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
  margin: 0 0 16px;
  color: #59667a;
  font-size: 15px;
  line-height: 1.68;
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
  width: 460px;
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
  max-height: 194px;
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
  padding: 14px 18px 14px;
  display: flex;
  flex-direction: column;
}

.stats-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 0 0 auto;
}

.stats-head button {
  height: 28px;
  border: 1px solid #dce4ef;
  border-radius: 8px;
  padding: 0 10px;
  color: #607086;
  background: #f8fbff;
  font-family: inherit;
  font-size: 12px;
  font-weight: 750;
}

.teaching-data-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  flex: 0 0 auto;
  gap: 0;
  margin: 13px 0 18px;
  border: 1px solid #dfe7f2;
  border-radius: 8px;
  overflow: hidden;
  background: #fbfdff;
}

.teaching-data-row div {
  min-width: 0;
  display: grid;
  grid-template-columns: 24px auto auto;
  align-items: center;
  justify-content: center;
  column-gap: 4px;
  row-gap: 5px;
  padding: 12px 8px 11px;
  border-right: 1px solid #e3e9f2;
  border-radius: 0;
  text-align: center;
  background: transparent;
}

.teaching-data-row div:last-child {
  border-right: 0;
}

.data-icon {
  grid-row: span 2;
  width: 23px;
  height: 23px;
  display: grid;
  place-items: center;
  color: #2f6bf6;
}

.teaching-data-row div:nth-child(2) .data-icon,
.teaching-data-row div:nth-child(3) .data-icon {
  color: #4778ff;
}

.teaching-data-row div:nth-child(4) .data-icon {
  color: #ffb11f;
}

.data-icon svg {
  width: 21px;
  height: 21px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.1;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.teaching-data-row strong {
  color: #13213a;
  font-size: 18px;
  line-height: 1;
  font-weight: 860;
}

.teaching-data-row span {
  margin-left: 3px;
  color: #2f6bf6;
  font-size: 11px;
  font-weight: 800;
}

.teaching-data-row p {
  grid-column: 2 / 4;
  margin: 7px 0 0;
  color: #6b7688;
  font-size: 11px;
  font-weight: 650;
  white-space: nowrap;
}

.activity-heading {
  margin-top: 0 !important;
  font-size: 16px !important;
}

.activity-heading span {
  color: #8a97aa;
  font-size: 12px;
}

.trend-unit {
  margin: 5px 0 0;
  color: #6d7a8d;
  font-size: 12px;
  font-weight: 650;
}

.trend-chart {
  position: relative;
  flex: 1;
  min-height: 108px;
  margin-top: 3px;
  padding: 0 8px 0;
  border: 1px solid #e3e9f2;
  border-radius: 8px;
  background: linear-gradient(180deg, #fff, #fbfdff);
}

.trend-chart svg {
  display: block;
  width: 100%;
  height: 82px;
  margin-top: 17px;
}

.trend-values,
.trend-days {
  position: absolute;
  left: 16px;
  right: 16px;
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
}

.trend-values {
  top: 15px;
  color: #516178;
  font-size: 12px;
  font-weight: 760;
}

.trend-days {
  bottom: 8px;
  color: #5c6a80;
  font-size: 13px;
  font-weight: 720;
}

.trend-values .active,
.trend-days .active {
  color: #2f6bf6;
}

.recent-card {
  height: 100%;
  min-height: 0;
  margin-top: 0;
  overflow: hidden;
  padding: 16px 22px 15px;
}

.record-list {
  margin-top: 13px;
}

.record-item {
  display: grid;
  grid-template-columns: 38px 1fr auto;
  gap: 13px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #e7ecf4;
}

.record-item:last-of-type {
  border-bottom: 0;
}

.record-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: #fff;
  background: #5b8dff;
}

.record-icon.doc {
  background: #35be75;
}

.record-icon.file {
  background: #ffad3d;
}

.record-icon svg {
  width: 17px;
  height: 17px;
  stroke-width: 2.4;
}

.record-item strong {
  display: block;
  max-width: 305px;
  margin-bottom: 5px;
  color: #273142;
  font-size: 14px;
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
  margin-top: 8px;
  color: #2f6bf6;
  font-size: 13px;
  font-weight: 820;
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



