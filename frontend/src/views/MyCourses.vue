<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listLessons } from '@/api/lesson'
import { trackProgress } from '@/api/progress'
import { useLessonStore } from '@/store/lessonStore'
import { useUserStore } from '@/store/userStore'

const route = useRoute()
const router = useRouter()
const lessonStore = useLessonStore()
const userStore = useUserStore()

const loading = ref(false)
const backendLessons = ref([])
const keyword = ref('')

const ongoingFallback = [
  {
    lessonId: 'ai-intro',
    courseId: 'ai-intro',
    lessonName: '人工智能导论',
    courseDesc: '第4章 机器学习基础',
    progress: 68,
    studiedHours: 12,
    totalHours: 20,
    statusText: '继续学习',
    coverType: 'ai',
  },
  {
    lessonId: 'python',
    courseId: 'python',
    lessonName: 'Python 程序设计',
    courseDesc: '第3章 函数与模块',
    progress: 42,
    studiedHours: 8,
    totalHours: 19,
    statusText: '继续学习',
    coverType: 'python',
    coverUrl: '/images/course-python.png',
  },
  {
    lessonId: 'algorithm',
    courseId: 'algorithm',
    lessonName: '数据结构与算法',
    courseDesc: '第5章 树与二叉树',
    progress: 25,
    studiedHours: 6,
    totalHours: 24,
    statusText: '继续学习',
    coverType: 'structure',
    coverUrl: '/images/course-data-structure.png',
  },
]

const completedFallback = [
  {
    lessonId: 'network',
    courseId: 'network',
    lessonName: '计算机网络原理',
    courseDesc: '已学完全部内容',
    studiedHours: 18.6,
    completedAt: '2024-04-12',
    coverType: 'paper',
  },
  {
    lessonId: 'os-basic',
    courseId: 'os-basic',
    lessonName: '操作系统基础',
    courseDesc: '已学完全部内容',
    studiedHours: 22.1,
    completedAt: '2024-03-28',
    coverType: 'mountain',
  },
  {
    lessonId: 'database',
    courseId: 'database',
    lessonName: '数据库系统概论',
    courseDesc: '已学完全部内容',
    studiedHours: 16.3,
    completedAt: '2024-03-15',
    coverType: 'hall',
  },
]

const normalizeString = (value, fallback = '') => {
  if (Array.isArray(value)) return normalizeString(value[0], fallback)
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function inferProgress(item, index) {
  if (Number.isFinite(Number(item.progress))) return Number(item.progress)
  if (Number.isFinite(Number(item.totalProgress))) return Number(item.totalProgress)
  const status = normalizeString(item.coursewareStatus || item.status).toLowerCase()
  if (['published', 'completed'].includes(status)) return ongoingFallback[index % ongoingFallback.length].progress
  if (['rendering', 'generating', 'processing'].includes(status)) return 42
  return ongoingFallback[index % ongoingFallback.length].progress
}

function normalizeOngoingCourse(item, index) {
  const fallback = ongoingFallback[index % ongoingFallback.length]
  const lessonId = normalizeString(item.lessonId || item.id, fallback.lessonId)
  const courseId = normalizeString(item.courseId, lessonId)
  const name = normalizeString(item.lessonName || item.name, fallback.lessonName)
  const progress = Math.max(1, Math.min(99, Math.round(inferProgress(item, index))))
  const totalHours = Number(item.totalHours || fallback.totalHours || 20)
  const studiedHours = Number(item.studiedHours || Math.max(1, Math.round(totalHours * progress / 100)))

  return {
    id: lessonId,
    lessonId,
    courseId,
    name,
    desc: normalizeString(item.courseDesc || item.desc || item.chapter, fallback.courseDesc),
    progress,
    studiedHours,
    totalHours,
    statusText: normalizeString(item.statusText || item.tag, fallback.statusText),
    coverType: normalizeString(item.coverType, fallback.coverType),
    coverUrl: normalizeString(item.coverUrl, fallback.coverUrl || ''),
  }
}

function normalizeCompletedCourse(item) {
  return {
    ...item,
    progress: 100,
    statusText: '已学完',
  }
}

const sourceOngoingCourses = computed(() => {
  const source = backendLessons.value.length ? backendLessons.value : ongoingFallback
  return source.slice(0, 3).map((item, index) => normalizeOngoingCourse(item, index))
})

const completedCourses = computed(() => completedFallback.map(normalizeCompletedCourse))

const filteredOngoingCourses = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  if (!value) return sourceOngoingCourses.value
  return sourceOngoingCourses.value.filter(course => course.name.toLowerCase().includes(value))
})

const filteredCompletedCourses = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  if (!value) return completedCourses.value
  return completedCourses.value.filter(course => course.lessonName.toLowerCase().includes(value))
})

async function loadCourses() {
  loading.value = true
  try {
    const result = await listLessons('published', { silent: true })
    backendLessons.value = Array.isArray(result?.lessons) ? result.lessons : Array.isArray(result) ? result : []
  } catch {
    backendLessons.value = []
  } finally {
    loading.value = false
  }
}

async function enterCourse(course) {
  if (!course) return
  const courseId = course.courseId || course.lessonId
  const courseName = course.name || course.lessonName

  lessonStore.setCourseInfo({
    courseId,
    courseName,
    courseDesc: course.desc || course.courseDesc || '',
  })
  lessonStore.setLessonInfo({ lessonId: course.lessonId })

  try {
    await trackProgress({
      silent: true,
      schoolId: userStore.userInfo.schoolId || route.query.schoolId,
      userId: userStore.userInfo.userId || route.query.userId,
      courseId,
      lessonId: course.lessonId,
      progressPercent: course.progress || 100,
    })
  } catch {
    // 演示模式下后端不可用时仍允许进入课程。
  }

  router.push({
    path: '/pc/lesson/player',
    query: {
      ...route.query,
      courseId,
      courseName,
      lessonId: course.lessonId,
    },
  })
}

onMounted(loadCourses)
</script>

<template>
  <div class="my-courses-page">
    <header class="my-courses-topbar">
      <h1>我的课程</h1>

      <label class="search-box" aria-label="搜索课程名称">
        <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.7-3.7" /></svg>
        <input v-model="keyword" type="search" placeholder="搜索课程名称" />
      </label>

      <div class="top-actions">
        <button class="sort-button" type="button">
          最近学习
          <svg viewBox="0 0 24 24"><path d="m7 10 5 5 5-5" /></svg>
        </button>
        <button class="view-button active" type="button" aria-label="网格视图">
          <svg viewBox="0 0 24 24"><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" /></svg>
        </button>
        <button class="view-button" type="button" aria-label="列表视图">
          <svg viewBox="0 0 24 24"><path d="M8 6h12M8 12h12M8 18h12" /><path d="M4 6h.01M4 12h.01M4 18h.01" /></svg>
        </button>
      </div>
    </header>

    <main class="courses-content">
      <section class="courses-section learning-section">
        <div class="section-head">
          <h2>正在学习</h2>
          <button type="button">查看全部（{{ sourceOngoingCourses.length + 2 }}）<span>›</span></button>
        </div>

        <div class="learning-grid" :class="{ loading }">
          <article
            v-for="course in filteredOngoingCourses"
            :key="course.id"
            class="learning-card"
            @click="enterCourse(course)"
          >
            <div class="learning-cover" :class="`cover-${course.coverType}`">
              <img v-if="course.coverUrl" :src="course.coverUrl" :alt="course.name" />
              <span>{{ course.statusText }}</span>
            </div>
            <div class="learning-body">
              <div class="card-title-row">
                <div>
                  <h3>{{ course.name }}</h3>
                  <p>{{ course.desc }}</p>
                </div>
                <button class="more-button" type="button" @click.stop aria-label="更多操作">⋮</button>
              </div>
              <div class="progress-line">
                <div><i :style="{ width: `${course.progress}%` }"></i></div>
                <b>{{ course.progress }}%</b>
              </div>
              <p class="hours-text">学习至 {{ course.studiedHours }} 小时 / 共 {{ course.totalHours }} 小时</p>
            </div>
          </article>
        </div>
      </section>

      <section class="courses-section completed-section">
        <div class="section-head">
          <h2>已学完</h2>
          <button type="button">查看全部（{{ completedCourses.length + 5 }}）<span>›</span></button>
        </div>

        <div class="completed-list">
          <article v-for="course in filteredCompletedCourses" :key="course.lessonId" class="completed-row">
            <div class="completed-cover" :class="`done-${course.coverType}`"></div>
            <div class="completed-title">
              <h3>{{ course.lessonName }}</h3>
              <p>{{ course.courseDesc }}</p>
            </div>
            <span>学习时长 {{ course.studiedHours }} 小时</span>
            <time>完成时间&nbsp; {{ course.completedAt }}</time>
            <button type="button" @click="enterCourse(course)">复习</button>
            <button class="row-more" type="button" aria-label="更多操作">⋮</button>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.my-courses-page {
  min-height: calc(100vh / var(--design-scale, 1));
  padding: 40px 56px 52px;
  color: #182235;
  background:
    radial-gradient(circle at 58% 2%, rgba(51, 112, 255, 0.045), transparent 25%),
    #f6f7f9;
}

.my-courses-topbar {
  display: grid;
  grid-template-columns: 1fr 420px 360px;
  gap: 26px;
  align-items: center;
  max-width: 1520px;
  margin: 0 auto 36px;
}

.my-courses-topbar h1 {
  margin: 0;
  color: #151c2c;
  font-size: 31px;
  line-height: 1;
  font-weight: 780;
  letter-spacing: -0.02em;
}

.search-box {
  height: 52px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  border: 1px solid #edf0f4;
  border-radius: 10px;
  background: #fffffe;
  box-shadow: 0 8px 24px rgba(29, 37, 55, 0.035);
}

.search-box svg,
.sort-button svg,
.view-button svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.search-box {
  color: #9aa4b2;
}

.search-box input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  color: #253044;
  background: transparent;
  font: 560 14px/1.4 inherit;
}

.search-box input::placeholder {
  color: #a9b1bd;
}

.top-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
}

.sort-button,
.view-button {
  height: 52px;
  border: 1px solid #edf0f4;
  border-radius: 10px;
  color: #5c6676;
  background: #fffffe;
  font-family: inherit;
  font-weight: 650;
  box-shadow: 0 8px 24px rgba(29, 37, 55, 0.035);
  cursor: pointer;
}

.sort-button {
  min-width: 170px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  font-size: 15px;
}

.view-button {
  width: 52px;
  display: grid;
  place-items: center;
}

.view-button.active {
  color: #152235;
}

.courses-content {
  max-width: 1520px;
  margin: 0 auto;
}

.courses-section {
  border: 1px solid #eef1f5;
  border-radius: 12px;
  background: rgba(255, 255, 254, 0.96);
  box-shadow: 0 8px 28px rgba(30, 42, 62, 0.035);
}

.learning-section {
  padding: 36px 32px 30px;
}

.completed-section {
  margin-top: 22px;
  padding: 28px 32px 30px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
}

.section-head h2 {
  margin: 0;
  color: #141c2b;
  font-size: 23px;
  line-height: 1;
  font-weight: 760;
}

.section-head button {
  border: 0;
  color: #4d596b;
  background: transparent;
  font: 650 14px/1 inherit;
  cursor: pointer;
}

.section-head button span {
  margin-left: 8px;
  font-size: 22px;
  vertical-align: -2px;
}

.learning-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 34px;
}

.learning-grid.loading {
  opacity: 0.7;
}

.learning-card {
  min-height: 342px;
  overflow: hidden;
  border: 1px solid #e8edf3;
  border-radius: 7px;
  background: #fffffe;
  cursor: pointer;
}

.learning-cover {
  position: relative;
  height: 168px;
  overflow: hidden;
  background: #dfe5ec;
}

.learning-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.9) contrast(0.95);
}

.learning-cover span {
  position: absolute;
  left: 18px;
  top: 17px;
  height: 29px;
  padding: 0 12px;
  border-radius: 5px;
  color: #fffffe;
  background: rgba(58, 69, 84, 0.72);
  font-size: 13px;
  font-weight: 650;
  line-height: 29px;
}

.cover-ai {
  background:
    radial-gradient(ellipse at 18% 8%, rgba(255, 255, 255, 0.7), transparent 10%),
    radial-gradient(ellipse at 46% 70%, rgba(68, 139, 255, 0.8), transparent 26%),
    repeating-linear-gradient(170deg, transparent 0 12px, rgba(86, 146, 255, 0.35) 12px 14px),
    linear-gradient(135deg, #06112a, #07111f 52%, #0e244c);
}

.cover-python {
  background:
    linear-gradient(0deg, rgba(5, 29, 36, 0.34), rgba(5, 29, 36, 0.34)),
    linear-gradient(130deg, #143b3f, #0b1f26 58%, #2d4d42);
}

.cover-structure {
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.68), rgba(255, 255, 255, 0.08)),
    repeating-radial-gradient(circle at 82% 66%, transparent 0 42px, rgba(70, 78, 92, 0.18) 43px 44px),
    #e6eaef;
}

.learning-body {
  padding: 20px 22px 22px;
}

.card-title-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 24px;
  gap: 12px;
}

.card-title-row h3,
.completed-title h3 {
  margin: 0;
  color: #1e2737;
  font-size: 19px;
  line-height: 1.25;
  font-weight: 760;
}

.card-title-row p,
.completed-title p,
.hours-text {
  margin: 11px 0 0;
  color: #647184;
  font-size: 14px;
  font-weight: 540;
}

.more-button,
.row-more {
  border: 0;
  color: #6b7480;
  background: transparent;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.progress-line {
  display: grid;
  grid-template-columns: 1fr 44px;
  gap: 12px;
  align-items: center;
  margin-top: 26px;
}

.progress-line div {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: #e8eaed;
}

.progress-line i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #2f7df4;
}

.progress-line b {
  color: #344153;
  font-size: 14px;
  font-weight: 650;
  text-align: right;
}

.completed-list {
  overflow: hidden;
  border: 1px solid #edf0f3;
  border-radius: 8px;
  background: #fffffe;
}

.completed-row {
  display: grid;
  grid-template-columns: 128px minmax(240px, 1fr) 150px 190px 74px 28px;
  gap: 28px;
  align-items: center;
  min-height: 104px;
  padding: 14px 28px 14px 18px;
  border-bottom: 1px solid #edf0f3;
}

.completed-row:last-child {
  border-bottom: 0;
}

.completed-cover {
  width: 128px;
  height: 72px;
  border-radius: 6px;
  background: #e4e8ed;
}

.done-paper {
  background:
    linear-gradient(165deg, rgba(255, 255, 255, 0.6), transparent 48%),
    repeating-linear-gradient(172deg, #d4c3a6 0 7px, #cbb997 7px 12px);
}

.done-mountain {
  background:
    linear-gradient(140deg, rgba(255, 255, 255, 0.65), transparent 40%),
    linear-gradient(135deg, #c7e3f4, #edf4f8 46%, #b9cedc);
}

.done-hall {
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.8), transparent 38%),
    radial-gradient(circle at 78% 32%, #cbd3dc, transparent 26%),
    #e5e8ec;
}

.completed-title h3 {
  font-size: 17px;
}

.completed-title p {
  margin-top: 10px;
  font-size: 13px;
}

.completed-row span,
.completed-row time {
  color: #5d6878;
  font-size: 14px;
  font-weight: 540;
}

.completed-row button:not(.row-more) {
  height: 38px;
  border: 1px solid #dfe5ec;
  border-radius: 6px;
  color: #435065;
  background: #fffffe;
  font: 650 14px/1 inherit;
  cursor: pointer;
}

@media (max-width: 1280px) {
  .my-courses-topbar {
    grid-template-columns: 1fr;
  }

  .top-actions {
    justify-content: flex-start;
  }

  .learning-grid {
    grid-template-columns: 1fr;
  }

  .completed-row {
    grid-template-columns: 110px minmax(0, 1fr) 86px 28px;
  }

  .completed-row span,
  .completed-row time {
    display: none;
  }
}
</style>
