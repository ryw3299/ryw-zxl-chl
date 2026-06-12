<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listLessons } from '@/api/lesson'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const backendLessons = ref([])
const keyword = ref('')
const activeTab = ref('all')

const demoCourses = [
  {
    lessonId: 'teacher-network',
    lessonName: '计算机网络',
    courseDesc: '第5章 传输层协议（TCP/UDP）',
    coverUrl: '/images/course-machine-learning.png',
    status: '进行中',
    accent: '#1769ff',
    progress: 78,
    lessons: 24,
    students: 128,
    homework: 24,
    averageScore: 86,
    recentActivity: '今天 10:15',
  },
  {
    lessonId: 'teacher-data-structure',
    lessonName: '数据结构与算法',
    courseDesc: '第6章 树与图',
    coverUrl: '/images/course-data-structure.png',
    status: '进行中',
    accent: '#10b981',
    progress: 55,
    lessons: 18,
    students: 96,
    homework: 18,
    averageScore: 79,
    recentActivity: '昨天 16:45',
  },
  {
    lessonId: 'teacher-python',
    lessonName: 'Python 程序设计',
    courseDesc: '第8章 函数与模块',
    coverUrl: '/images/course-python.png',
    status: '进行中',
    accent: '#8b5cf6',
    progress: 86,
    lessons: 32,
    students: 156,
    homework: 32,
    averageScore: 88,
    recentActivity: '今天 09:42',
  },
]

const normalizeString = (value, fallback = '') => {
  if (Array.isArray(value)) return normalizeString(value[0], fallback)
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

const metricSeed = (index) => demoCourses[index % demoCourses.length]

const normalizeCourse = (item, index) => {
  const fallback = metricSeed(index)
  const lessonId = normalizeString(item?.lessonId || item?.id, fallback.lessonId)
  const name = normalizeString(item?.lessonName || item?.name, fallback.lessonName)
  const progress = Number.isFinite(Number(item?.progress))
    ? Math.max(1, Math.min(99, Math.round(Number(item.progress))))
    : fallback.progress

  return {
    id: lessonId,
    lessonId,
    courseId: normalizeString(item?.courseId, lessonId),
    lessonName: name,
    courseDesc: normalizeString(item?.courseDesc || item?.desc || item?.tag, fallback.courseDesc),
    coverUrl: normalizeString(item?.coverUrl, fallback.coverUrl),
    status: normalizeString(item?.statusText, fallback.status),
    accent: fallback.accent,
    progress,
    lessons: Number(item?.sectionCount || item?.lessons || fallback.lessons),
    students: Number(item?.students || fallback.students),
    homework: Number(item?.homework || fallback.homework),
    averageScore: Number(item?.averageScore || fallback.averageScore),
    recentActivity: normalizeString(item?.updatedAt || item?.createdAt, fallback.recentActivity),
    scriptId: normalizeString(item?.scriptId),
    audioId: normalizeString(item?.audioId),
  }
}

const sourceCourses = computed(() => {
  const merged = backendLessons.value.length
    ? [...backendLessons.value, ...demoCourses].slice(0, Math.max(3, backendLessons.value.length))
    : demoCourses
  return merged.map(normalizeCourse)
})

const filteredCourses = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  let courses = sourceCourses.value
  if (activeTab.value === 'active') courses = courses.filter((item) => item.progress < 100)
  if (activeTab.value === 'done') courses = courses.filter((item) => item.progress >= 100)
  if (!value) return courses
  return courses.filter((item) => (
    item.lessonName.toLowerCase().includes(value)
    || item.courseDesc.toLowerCase().includes(value)
  ))
})

const tabs = computed(() => [
  { key: 'all', label: '全部课程', count: sourceCourses.value.length },
  { key: 'active', label: '进行中', count: sourceCourses.value.filter((item) => item.progress < 100).length },
  { key: 'done', label: '已结束', count: sourceCourses.value.filter((item) => item.progress >= 100).length },
])

const loadCourses = async () => {
  loading.value = true
  try {
    const result = await listLessons('published', { silent: true })
    backendLessons.value = Array.isArray(result?.lessons) ? result.lessons : []
  } catch {
    backendLessons.value = []
  } finally {
    loading.value = false
  }
}

const goCreate = () => {
  router.push({ path: '/pc/teacher/upload', query: route.query })
}

const openCourse = (course) => {
  router.push({
    path: '/pc/lesson/player',
    query: {
      ...route.query,
      courseId: course.courseId,
      courseName: course.lessonName,
      lessonId: course.lessonId,
      scriptId: course.scriptId || undefined,
      audioId: course.audioId || undefined,
    },
  })
}

const manageCourse = (course) => {
  router.push({
    path: '/pc/teacher/upload',
    query: {
      ...route.query,
      lessonId: course.lessonId,
      courseId: course.courseId,
      courseName: course.lessonName,
    },
  })
}

onMounted(loadCourses)
</script>

<template>
  <div class="teacher-courses-page">
    <header class="courses-topbar">
      <div class="greeting">
        <span class="sun" aria-hidden="true">☀</span>
        <div>
          <h2>上午好，教师管理员</h2>
          <p>专注教学，助力成长</p>
        </div>
      </div>

      <label class="global-search" aria-label="搜索课程、学生或资源">
        <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.7-3.7" /></svg>
        <input v-model="keyword" type="search" placeholder="搜索课程、学生或资源" />
      </label>

      <div class="profile-chip">
        <span class="bell">♢<i>3</i></span>
        <span class="avatar">教</span>
        <strong>教师管理员</strong>
        <span>⌄</span>
      </div>
    </header>

    <main class="courses-main">
      <section class="courses-heading">
        <h1>我的课程</h1>
        <div class="heading-actions">
          <button class="primary-action" type="button" @click="goCreate">
            <span>＋</span> 创建课程
          </button>
          <button class="ghost-action" type="button">
            <span>▣</span> 课程分组
          </button>
        </div>
      </section>

      <section class="filter-row">
        <div class="tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}（{{ tab.count }}）
          </button>
        </div>
        <label class="course-search" aria-label="搜索我的课程">
          <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.7-3.7" /></svg>
          <input v-model="keyword" type="search" placeholder="搜索我的课程" />
        </label>
      </section>

      <section class="course-list" :class="{ loading }">
        <article v-for="course in filteredCourses" :key="course.id" class="course-card">
          <div class="cover-wrap">
            <img :src="course.coverUrl" :alt="course.lessonName" />
            <span class="status-badge">{{ course.status }}</span>
          </div>

          <div class="course-info">
            <div class="course-title-row">
              <div>
                <h2>{{ course.lessonName }}</h2>
                <p>{{ course.courseDesc }}</p>
              </div>
              <div class="progress-box">
                <span>教学进度</span>
                <div class="progress-track">
                  <i :style="{ width: `${course.progress}%`, background: course.accent }"></i>
                </div>
                <strong>{{ course.progress }}%</strong>
              </div>
              <span class="activity">最近活动：{{ course.recentActivity }}</span>
              <button class="more-btn" type="button" aria-label="更多操作">•••</button>
            </div>

            <div class="metrics-row">
              <div class="metric-item blue">
                <span class="metric-icon">▣</span>
                <strong>{{ course.lessons }}</strong>
                <em>次课</em>
              </div>
              <div class="metric-item green">
                <span class="metric-icon">♙</span>
                <strong>{{ course.students }}</strong>
                <em>名学生</em>
              </div>
              <div class="metric-item orange">
                <span class="metric-icon">▤</span>
                <strong>{{ course.homework }}</strong>
                <em>份待批作业</em>
              </div>
              <div class="metric-item purple">
                <span class="metric-icon">↗</span>
                <strong>{{ course.averageScore }}%</strong>
                <em>平均成绩</em>
              </div>
            </div>

            <div class="course-actions">
              <button type="button" @click="openCourse(course)">查看详情 <span>›</span></button>
              <button type="button" @click="manageCourse(course)">⚙ 管理课程</button>
              <button type="button">✈ 发布作业</button>
            </div>
          </div>
        </article>
      </section>
    </main>
  </div>
</template>

<style scoped>
.teacher-courses-page {
  min-height: 100%;
  padding: 0 22px 28px;
  color: #0f1b33;
  background: #f6f8fc;
}

.courses-topbar {
  height: 92px;
  display: grid;
  grid-template-columns: 1fr minmax(320px, 360px) auto;
  align-items: center;
  gap: 28px;
  border-bottom: 1px solid #e3e9f4;
  background: rgba(255, 255, 255, 0.88);
  margin: 0 -22px 26px;
  padding: 0 32px;
}

.greeting {
  display: flex;
  align-items: center;
  gap: 16px;
}

.sun {
  color: #f5a400;
  font-size: 31px;
  line-height: 1;
}

.greeting h2 {
  margin: 0 0 6px;
  font-size: 22px;
  line-height: 1.2;
  font-weight: 860;
}

.greeting p {
  margin: 0;
  color: #7b879b;
  font-size: 13px;
  font-weight: 650;
}

.global-search,
.course-search {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 46px;
  border: 1px solid #dce4f1;
  border-radius: 999px;
  background: #fff;
  padding: 0 17px;
  color: #7f8ba3;
}

.global-search svg,
.course-search svg {
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
}

.global-search input,
.course-search input {
  min-width: 0;
  width: 100%;
  border: 0;
  outline: 0;
  color: #17223a;
  background: transparent;
  font: inherit;
  font-size: 14px;
}

.profile-chip {
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
  font-size: 14px;
}

.bell {
  position: relative;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid #dce4f1;
  color: #173154;
  font-size: 24px;
}

.bell i {
  position: absolute;
  top: -4px;
  right: -2px;
  width: 17px;
  height: 17px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background: #ff3b48;
  font-size: 10px;
  font-style: normal;
}

.avatar {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #1769ff;
  background: #eaf2ff;
  font-weight: 860;
}

.courses-main {
  max-width: 1580px;
  margin: 0 auto;
}

.courses-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 22px;
}

.courses-heading h1 {
  margin: 0;
  font-size: 34px;
  line-height: 1.1;
  font-weight: 900;
  letter-spacing: 0;
}

.heading-actions {
  display: flex;
  align-items: center;
  gap: 18px;
}

.primary-action,
.ghost-action {
  height: 48px;
  border-radius: 9px;
  padding: 0 28px;
  font-family: inherit;
  font-size: 15px;
  font-weight: 760;
  cursor: pointer;
}

.primary-action {
  border: 0;
  color: #fff;
  background: linear-gradient(180deg, #2478ff, #0f65f3);
  box-shadow: 0 8px 18px rgba(23, 105, 255, 0.22);
}

.ghost-action {
  border: 1px solid #dce4f1;
  color: #24324a;
  background: #fff;
}

.filter-row {
  display: grid;
  grid-template-columns: 1fr 300px;
  align-items: end;
  gap: 22px;
  margin-bottom: 16px;
}

.tabs {
  display: flex;
  align-items: center;
  gap: 30px;
}

.tabs button {
  position: relative;
  border: 0;
  padding: 0 0 15px;
  color: #5c6a82;
  background: transparent;
  font-family: inherit;
  font-size: 15px;
  font-weight: 760;
  cursor: pointer;
}

.tabs button.active {
  color: #1769ff;
}

.tabs button.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 3px;
  border-radius: 999px;
  background: #1769ff;
}

.course-search {
  height: 44px;
  border-radius: 8px;
}

.course-list {
  display: grid;
  gap: 14px;
  opacity: 1;
  transition: opacity 0.2s ease;
}

.course-list.loading {
  opacity: 0.72;
}

.course-card {
  min-height: 192px;
  display: grid;
  grid-template-columns: 370px minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid #dde5f0;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 30px rgba(18, 37, 72, 0.07);
}

.cover-wrap {
  position: relative;
  min-height: 192px;
  overflow: hidden;
  background: #dfe7f2;
}

.cover-wrap img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.status-badge {
  position: absolute;
  top: 17px;
  left: 17px;
  display: inline-flex;
  align-items: center;
  height: 30px;
  padding: 0 13px;
  border-radius: 8px;
  color: #fff;
  background: #12c971;
  font-size: 13px;
  font-weight: 860;
}

.course-info {
  min-width: 0;
  padding: 22px 28px 0;
  display: flex;
  flex-direction: column;
}

.course-title-row {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 280px 180px 32px;
  align-items: start;
  gap: 18px;
}

.course-title-row h2 {
  margin: 0 0 10px;
  font-size: 23px;
  line-height: 1.18;
  font-weight: 900;
  letter-spacing: 0;
}

.course-title-row p {
  margin: 0;
  color: #53627a;
  font-size: 14px;
  font-weight: 680;
}

.progress-box {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  padding-top: 8px;
  color: #69778d;
  font-size: 13px;
  font-weight: 720;
}

.progress-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf2f8;
}

.progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.progress-box strong {
  color: #17223a;
  font-size: 14px;
}

.activity {
  padding-top: 8px;
  color: #7a879d;
  font-size: 14px;
  font-weight: 680;
  white-space: nowrap;
}

.more-btn {
  border: 0;
  padding: 5px 0 0;
  color: #0f1b33;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  margin-top: 20px;
}

.metric-item {
  min-height: 58px;
  display: grid;
  grid-template-columns: 46px auto 1fr;
  align-items: center;
  column-gap: 11px;
  border-right: 1px solid #e3e9f2;
}

.metric-item:last-child {
  border-right: 0;
}

.metric-icon {
  color: var(--metric-color);
  font-size: 25px;
  font-weight: 850;
  text-align: center;
}

.metric-item strong {
  color: #101b31;
  font-size: 23px;
  line-height: 1;
  font-weight: 900;
}

.metric-item em {
  align-self: end;
  margin-bottom: 8px;
  color: #7a879d;
  font-size: 14px;
  font-style: normal;
  font-weight: 680;
}

.metric-item.blue { --metric-color: #1769ff; }
.metric-item.green { --metric-color: #12b76a; }
.metric-item.orange { --metric-color: #ff9600; }
.metric-item.purple { --metric-color: #8b5cf6; }

.course-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-top: auto;
  border-top: 1px solid #e7edf5;
}

.course-actions button {
  height: 50px;
  border: 0;
  border-right: 1px solid #e7edf5;
  color: #1769ff;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  font-weight: 780;
  cursor: pointer;
}

.course-actions button:last-child {
  border-right: 0;
}

@media (max-width: 1280px) {
  .courses-topbar {
    grid-template-columns: 1fr;
    height: auto;
    gap: 16px;
    padding: 20px 24px;
  }

  .profile-chip {
    display: none;
  }

  .course-card {
    grid-template-columns: 340px minmax(0, 1fr);
  }

  .course-title-row {
    grid-template-columns: 1fr;
  }
}
</style>
