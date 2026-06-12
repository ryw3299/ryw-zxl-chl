<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listLessons } from '@/api/lesson'
import { useUserStore } from '@/store/userStore'

const router = useRouter()
const userStore = useUserStore()

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6)  return '夜深了，注意休息'
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const userName = computed(() => {
  const id = userStore.userInfo.userId || '同学'
  if (/^demo/.test(id)) return '同学'
  return id.length > 6 ? id.slice(0, 6) : id
})

const COURSE_COLORS = [
  ['#2563eb', '#60a5fa'],
  ['#0891b2', '#22d3ee'],
  ['#7c3aed', '#a78bfa'],
  ['#059669', '#34d399'],
  ['#d97706', '#fbbf24'],
  ['#dc2626', '#f87171'],
]
const DEFAULT_PUBLISHED_COVER = 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=600&q=80'

// Mock 课程数据保留；后端已发布智课会合并到列表中。
const courses = ref([
  {
    lessonId: 'course-1',
    courseId: 'course-1',
    title: '人工智能导论',
    subtitle: '从零开始理解 AI 核心原理',
    img: 'https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=600&q=80',
    subjectTag: 'AI · 入门',
    progress: 68,
    totalSections: 24,
    doneSections: 16,
    tag: '进行中',
    tagColor: '#1677ff',
    tagBg: '#eef4ff',
    accentColor: '#2563eb',
    gradientFrom: '#2563eb',
    gradientTo: '#60a5fa',
    lastStudied: '昨天',
  },
  {
    lessonId: 'course-2',
    courseId: 'course-2',
    title: '机器学习基础',
    subtitle: '掌握监督学习与模型评估方法',
    img: 'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=600&q=80',
    subjectTag: 'ML · 进阶',
    progress: 42,
    totalSections: 32,
    doneSections: 13,
    tag: '进行中',
    tagColor: '#1677ff',
    tagBg: '#eef4ff',
    accentColor: '#0891b2',
    gradientFrom: '#0891b2',
    gradientTo: '#22d3ee',
    lastStudied: '2天前',
  },
  {
    lessonId: 'course-3',
    courseId: 'course-3',
    title: '数据结构与算法',
    subtitle: '系统学习树、图与动态规划',
    img: 'https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=600&q=80',
    subjectTag: 'CS · 核心',
    progress: 15,
    totalSections: 40,
    doneSections: 6,
    tag: '刚开始',
    tagColor: '#f59e0b',
    tagBg: '#fffbeb',
    accentColor: '#7c3aed',
    gradientFrom: '#7c3aed',
    gradientTo: '#a78bfa',
    lastStudied: '3天前',
  },
  {
    lessonId: 'course-4',
    courseId: 'course-4',
    title: 'Python 程序设计',
    subtitle: '面向对象编程与真实项目案例',
    img: 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=600&q=80',
    subjectTag: 'Python · 基础',
    progress: 90,
    totalSections: 28,
    doneSections: 25,
    tag: '接近完成',
    tagColor: '#12b76a',
    tagBg: '#ecfdf3',
    accentColor: '#059669',
    gradientFrom: '#059669',
    gradientTo: '#34d399',
    lastStudied: '今天',
  },
])

const mapPublishedLesson = (lesson, index) => {
  const [from, to] = COURSE_COLORS[index % COURSE_COLORS.length]
  const sectionCount = Number(lesson.sectionCount || 0)
  return {
    lessonId: lesson.lessonId,
    courseId: lesson.courseId || lesson.lessonId,
    scriptId: lesson.scriptId || '',
    parseId: lesson.parseId || '',
    audioId: lesson.audioId || '',
    title: lesson.lessonName || lesson.lessonId,
    subtitle: lesson.courseDesc || (sectionCount ? `已生成 ${sectionCount} 个章节讲解脚本` : '已发布智课，点击开始学习'),
    coverUrl: lesson.coverUrl || DEFAULT_PUBLISHED_COVER,
    progress: 0,
    totalSections: sectionCount || 1,
    doneSections: 0,
    tag: lesson.tag || '已发布',
    tagColor: '#12b76a',
    tagBg: '#ecfdf3',
    accentColor: from,
    gradientFrom: from,
    gradientTo: to,
    lastStudied: lesson.createdAt || '新课程',
    isPublished: true,
  }
}

const loadPublishedCourses = async () => {
  try {
    const res = await listLessons('published')
    const lessons = Array.isArray(res?.lessons) ? res.lessons : []
    const existingIds = new Set(courses.value.map((course) => course.lessonId))
    const published = lessons
      .filter((lesson) => lesson?.lessonId && !existingIds.has(lesson.lessonId))
      .map(mapPublishedLesson)
    courses.value = [...published, ...courses.value]
  } catch {
    // 后端不可用时保留本地 mock 课程。
  }
}

const lastCourse = computed(() => courses.value.find((c) => c.progress < 100 && c.progress > 0))

const goLesson = (course) => {
  const lessonId = typeof course === 'string' ? course : course.lessonId
  const query = typeof course === 'string'
    ? {}
    : {
        courseId: course.courseId || course.lessonId,
        courseName: course.title,
        scriptId: course.scriptId || undefined,
        parseId: course.parseId || undefined,
        audioId: course.audioId || undefined,
      }
  router.push({ path: `/lesson/${encodeURIComponent(lessonId)}`, query })
}

const goLeaderboard = () => router.push('/m/leaderboard')

onMounted(loadPublishedCourses)
</script>

<template>
  <div class="student-home">

    <!-- 问候横幅 -->
    <div class="greeting-card">
      <div class="greeting-card__text">
        <p class="greeting-sub">{{ greeting }}，</p>
        <h2 class="greeting-name">{{ userName }}</h2>
        <p class="greeting-hint">继续保持，你已完成 {{ courses.filter(c=>c.progress===100).length }} 门课程</p>
      </div>
      <div class="greeting-card__deco">
        <div class="deco-ring deco-ring--1" />
        <div class="deco-ring deco-ring--2" />
        <van-icon name="award-o" size="44" color="rgba(255,255,255,0.35)" />
      </div>
    </div>

    <!-- 排行榜入口 -->
    <button class="leaderboard-entry" @click="goLeaderboard">
      <div class="lb-entry-left">
        <div class="lb-entry-icon">
          <van-icon name="medal-o" size="20" color="#fff" />
        </div>
        <div>
          <strong>班级排行榜</strong>
          <p>查看你的学习名次与动态</p>
        </div>
      </div>
      <van-icon name="arrow" size="14" color="#c5cdd8" />
    </button>

    <!-- 继续学习快捷入口 -->
    <div v-if="lastCourse" class="section">
      <div class="section__head">
        <span>继续学习</span>
      </div>
      <div class="continue-card" @click="goLesson(lastCourse)">
        <div class="continue-card__icon" :style="{ background: `linear-gradient(135deg, ${lastCourse.gradientFrom}, ${lastCourse.gradientTo})` }">
          <van-icon name="play-circle-o" size="26" color="#fff" />
        </div>
        <div class="continue-card__body">
          <strong>{{ lastCourse.title }}</strong>
          <p>{{ lastCourse.subtitle }}</p>
          <van-progress
            :percentage="lastCourse.progress"
            :color="lastCourse.accentColor"
            stroke-width="4"
            :show-pivot="false"
            class="continue-progress"
          />
        </div>
        <div class="continue-card__pct" :style="{ color: lastCourse.accentColor }">
          {{ lastCourse.progress }}%
        </div>
      </div>
    </div>

    <!-- 全部课程 -->
    <div class="section">
      <div class="section__head">
        <span>我的课程</span>
        <em>{{ courses.length }} 门</em>
      </div>
      <div class="course-list">
        <div
          v-for="course in courses"
          :key="course.lessonId"
          class="course-card"
          @click="goLesson(course)"
        >
          <!-- 左色条 -->
          <div class="course-card__bar" :style="{ background: `linear-gradient(180deg, ${course.gradientFrom}, ${course.gradientTo})` }" />

          <!-- 封面图 -->
          <div class="course-card__cover-wrap">
            <img class="course-card__cover" :src="course.img || course.coverUrl" :alt="course.title" loading="lazy">
            <span v-if="course.subjectTag" class="course-card__subject-tag">{{ course.subjectTag }}</span>
          </div>

          <div class="course-card__body">
            <div class="course-card__row">
              <strong class="course-title">{{ course.title }}</strong>
            </div>
            <p class="course-sub">{{ course.subtitle }}</p>
            <div class="course-stats">
              <van-progress
                :percentage="course.progress"
                :color="course.accentColor"
                stroke-width="5"
                :show-pivot="false"
                class="course-progress"
              />
              <span class="course-meta">{{ course.doneSections }}/{{ course.totalSections }} 节 · {{ course.lastStudied }}</span>
              <span class="course-teacher">
                <van-icon name="manager-o" size="11" />
                演示教师
              </span>
            </div>
          </div>

          <van-icon name="arrow" size="14" color="#c5cdd8" style="flex-shrink:0;margin-top:auto;margin-bottom:16px" />
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.student-home {
  padding: 16px 14px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── 问候横幅 ── */
.greeting-card {
  border-radius: 22px;
  background: linear-gradient(135deg, #1677ff 0%, #2a8aff 55%, #46aaff 100%);
  padding: 22px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  overflow: hidden;
  position: relative;
  box-shadow: 0 8px 28px rgba(22, 119, 255, 0.3);
}

.greeting-card__text {
  position: relative;
  z-index: 1;
}

.greeting-sub {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
}

.greeting-name {
  margin: 4px 0 8px;
  font-size: 26px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.03em;
}

.greeting-hint {
  margin: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.greeting-card__deco {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.deco-ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.15);
}
.deco-ring--1 { width: 70px; height: 70px; }
.deco-ring--2 { width: 100px; height: 100px; }

/* ── Section ── */
.section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section__head span {
  font-size: 15px;
  font-weight: 800;
  color: #1a2035;
}

.section__head em {
  font-style: normal;
  font-size: 12px;
  color: #9aa3b2;
}

/* ── 继续学习卡 ── */
.continue-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: transform 0.15s;
}

.continue-card:active {
  transform: scale(0.98);
}

.continue-card__icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.continue-card__body {
  flex: 1;
  min-width: 0;
}

.continue-card__body strong {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: #1a2035;
  margin-bottom: 2px;
}

.continue-card__body p {
  margin: 0 0 8px;
  font-size: 12px;
  color: #9aa3b2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.continue-progress {
  width: 100%;
}

.continue-card__pct {
  font-size: 18px;
  font-weight: 800;
  flex-shrink: 0;
}

/* ── 课程列表 ── */
.course-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.course-card {
  display: flex;
  align-items: flex-start;
  gap: 0;
  background: #fff;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: transform 0.15s;
  padding-right: 16px;
}

.course-card:active {
  transform: scale(0.98);
}

.course-card__bar {
  width: 5px;
  align-self: stretch;
  flex-shrink: 0;
  margin-right: 14px;
}

.course-card__cover-wrap {
  position: relative;
  width: 78px;
  height: 96px;
  align-self: center;
  flex-shrink: 0;
  margin: 12px 12px 12px 0;
  border-radius: 14px;
  overflow: hidden;
  background: #eef2f7;
}

.course-card__cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.course-card__subject-tag {
  position: absolute;
  bottom: 6px;
  left: 0;
  right: 0;
  margin: 0 auto;
  width: fit-content;
  max-width: calc(100% - 8px);
  font-size: 9.5px;
  font-weight: 700;
  color: #fff;
  background: rgba(15, 23, 42, 0.52);
  backdrop-filter: blur(6px);
  padding: 2px 7px;
  border-radius: 999px;
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.course-card__body {
  flex: 1;
  min-width: 0;
  padding: 14px 0 14px;
}

.course-card__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.course-title {
  font-size: 16px;
  font-weight: 700;
  color: #1a2035;
}

.course-tag {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 999px;
}

.course-sub {
  margin: 0 0 10px;
  font-size: 12px;
  color: #9aa3b2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.course-stats {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.course-progress {
  width: 100%;
}

.course-meta {
  font-size: 11px;
  color: #b0b9c8;
}

.course-teacher {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: #9aa3b2;
}

/* ── 排行榜入口 ── */
.leaderboard-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 14px 16px;
  background: #fff;
  border: none;
  border-radius: 18px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  text-align: left;
  transition: transform 0.15s;
}

.leaderboard-entry:active { transform: scale(0.98); }

.lb-entry-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.lb-entry-icon {
  width: 42px; height: 42px;
  border-radius: 13px;
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.lb-entry-left strong {
  display: block;
  font-size: 15px; font-weight: 700; color: #1a2035;
  margin-bottom: 2px;
}

.lb-entry-left p {
  margin: 0;
  font-size: 12px; color: #9aa3b2;
}
</style>
