<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { deleteLesson, listLessons } from '@/api/lesson'
import { useUserStore } from '@/store/userStore'

const router = useRouter()
const userStore = useUserStore()
const DEFAULT_PUBLISHED_COVER = 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=600&q=80'

const LESSON_COLORS = [
  ['#2563eb', '#60a5fa'],
  ['#0891b2', '#22d3ee'],
  ['#7c3aed', '#a78bfa'],
  ['#059669', '#34d399'],
  ['#d97706', '#fbbf24'],
  ['#dc2626', '#f87171'],
]

// Mock 已生成的智课列表保留；后端已发布智课会合并到列表中。
const lessonList = ref([
  {
    lessonId: 'lesson-ai-001',
    title: '人工智能导论',
    img: 'https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=600&q=80',
    subjectTag: 'AI · 入门',
    barGradient: 'linear-gradient(180deg, #2563eb, #60a5fa)',
    status: 'completed',
    sections: 24,
    createdAt: '2026-04-15',
    previewReady: true,
  },
  {
    lessonId: 'lesson-ai-002',
    title: '机器学习基础',
    img: 'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=600&q=80',
    subjectTag: 'ML · 进阶',
    barGradient: 'linear-gradient(180deg, #0891b2, #22d3ee)',
    status: 'completed',
    sections: 32,
    createdAt: '2026-04-12',
    previewReady: true,
  },
  {
    lessonId: 'lesson-ai-003',
    title: '数据结构与算法',
    img: 'https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=600&q=80',
    subjectTag: 'CS · 核心',
    barGradient: 'linear-gradient(180deg, #7c3aed, #a78bfa)',
    status: 'completed',
    sections: 36,
    createdAt: '2026-04-18',
    previewReady: true,
  },
  {
    lessonId: 'lesson-ai-004',
    title: 'Python 程序设计',
    img: 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=600&q=80',
    subjectTag: 'Python · 基础',
    barGradient: 'linear-gradient(180deg, #059669, #34d399)',
    status: 'completed',
    sections: 28,
    createdAt: '2026-04-08',
    previewReady: true,
  },
])

const mapPublishedLesson = (lesson, index) => {
  const [from, to] = LESSON_COLORS[index % LESSON_COLORS.length]
  return {
    lessonId: lesson.lessonId,
    courseId: lesson.courseId || lesson.lessonId,
    scriptId: lesson.scriptId || '',
    parseId: lesson.parseId || '',
    audioId: lesson.audioId || '',
    title: lesson.lessonName || lesson.lessonId,
    img: lesson.coverUrl || DEFAULT_PUBLISHED_COVER,
    subjectTag: lesson.tag || '',
    barGradient: `linear-gradient(180deg, ${from}, ${to})`,
    status: 'completed',
    sections: Number(lesson.sectionCount || 0),
    createdAt: lesson.createdAt || '刚刚',
    previewReady: true,
    isPublished: true,
  }
}

const loadPublishedLessons = async () => {
  try {
    const res = await listLessons('published')
    const lessons = Array.isArray(res?.lessons) ? res.lessons : []
    const existingIds = new Set(lessonList.value.map((lesson) => lesson.lessonId))
    const published = lessons
      .filter((lesson) => lesson?.lessonId && !existingIds.has(lesson.lessonId))
      .map(mapPublishedLesson)
    lessonList.value = [...published, ...lessonList.value]
  } catch {
    // 后端不可用时保留本地 mock 智课。
  }
}

const goPreview = (lesson) => {
  const lessonId = typeof lesson === 'string' ? lesson : lesson.lessonId
  const query = typeof lesson === 'string'
    ? {}
    : {
        courseId: lesson.courseId || lesson.lessonId,
        courseName: lesson.title,
        scriptId: lesson.scriptId || undefined,
        parseId: lesson.parseId || undefined,
        audioId: lesson.audioId || undefined,
      }
  router.push({ path: `/lesson/${encodeURIComponent(lessonId)}`, query })
}

const deleteLessonItem = async (lesson) => {
  if (!lesson?.lessonId) return
  try {
    await showConfirmDialog({
      title: '删除智课',
      message: `确认删除「${lesson.title || '该智课'}」？`,
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    if (lesson.isPublished) {
      await deleteLesson(lesson.lessonId)
    }
    lessonList.value = lessonList.value.filter((item) => item.lessonId !== lesson.lessonId)
    showToast({ message: '已删除', type: 'success' })
  } catch (error) {
    showToast(error?.userMessage || error?.message || '删除失败，请稍后重试')
  }
}

const goCreate = () => {
  // 通知父组件切换到"创课"Tab（用自定义事件）
  // 此处通过 emit 告知 Home.vue 切换 tab，暂用 router 占位
  router.push('/m/home')
}

const stats = computed(() => [
  { label: '已生成智课', value: String(lessonList.value.length), icon: 'description', color: '#1677ff', bg: '#eef4ff' },
  { label: '服务学生', value: '50', icon: 'friends-o', color: '#12b76a', bg: '#ecfdf3' },
  { label: '本月新增', value: '1', icon: 'add-o', color: '#7c3aed', bg: '#f5f0ff' },
])

onMounted(loadPublishedLessons)
</script>

<template>
  <div class="teacher-home">

    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="welcome-banner__text">
        <p class="welcome-sub">欢迎回来</p>
        <h2 class="welcome-name">智悉云擎教师端</h2>
        <p class="welcome-hint">点击"创课"可一键上传课件生成智课</p>
      </div>
      <div class="welcome-banner__deco">
        <div class="deco-ring deco-ring--1" />
        <div class="deco-ring deco-ring--2" />
        <van-icon name="notes-o" size="40" color="rgba(255,255,255,0.3)" />
      </div>
    </div>

    <!-- 数据统计 -->
    <div class="stats-row">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-card__icon" :style="{ background: s.bg }">
          <van-icon :name="s.icon" size="20" :color="s.color" />
        </div>
        <strong :style="{ color: s.color }">{{ s.value }}</strong>
        <span>{{ s.label }}</span>
      </div>
    </div>

    <!-- 智课列表 -->
    <div class="section">
      <div class="section__head">
        <span>我的智课</span>
        <em>{{ lessonList.length }} 条</em>
      </div>

      <div class="lesson-list">
        <div
          v-for="lesson in lessonList"
          :key="lesson.lessonId"
          class="lesson-card"
          @click="lesson.previewReady && goPreview(lesson)"
        >
          <!-- 左色条 -->
          <div class="lesson-card__bar" :style="{ background: lesson.barGradient }" />

          <!-- 封面图 -->
          <div class="lesson-card__cover-wrap">
            <img class="lesson-card__cover" :src="lesson.img" :alt="lesson.title" loading="lazy">
            <span v-if="lesson.subjectTag" class="lesson-card__subject-tag">{{ lesson.subjectTag }}</span>
            <span v-if="lesson.status === 'generating'" class="lesson-card__generating-badge">
              <van-loading size="8px" color="#fff" style="margin-right:3px" />生成中
            </span>
          </div>

          <!-- 内容 -->
          <div class="lesson-card__body">
            <h4>{{ lesson.title }}</h4>
            <div class="lesson-card__meta">
              <span><van-icon name="calendar-o" size="11" /> {{ lesson.createdAt }}</span>
              <span v-if="lesson.sections > 0"><van-icon name="list-switch" size="11" /> {{ lesson.sections }} 节</span>
            </div>
            <div class="lesson-card__actions">
              <button
                class="action-btn action-btn--primary"
                :disabled="!lesson.previewReady"
                @click.stop="goPreview(lesson)"
              >
                <van-icon name="play-circle-o" size="12" />
                预览
              </button>
              <button class="action-btn action-btn--danger" @click.stop="deleteLessonItem(lesson)">
                <van-icon name="delete-o" size="12" />
                删除
              </button>
            </div>
          </div>

          <!-- 箭头 -->
          <van-icon name="arrow" size="14" color="#c5cdd8" style="flex-shrink:0;margin-top:auto;margin-bottom:16px" />
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.teacher-home {
  padding: 16px 14px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── 欢迎横幅 ── */
.welcome-banner {
  border-radius: 22px;
  background: linear-gradient(135deg, #7c3aed 0%, #9f67ff 55%, #b794f4 100%);
  padding: 22px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  overflow: hidden;
  position: relative;
  box-shadow: 0 8px 28px rgba(124, 58, 237, 0.28);
}

.welcome-banner__text { position: relative; z-index: 1; }
.welcome-sub { margin: 0; font-size: 13px; color: rgba(255,255,255,0.7); }
.welcome-name { margin: 4px 0 8px; font-size: 24px; font-weight: 800; color: #fff; letter-spacing: -0.03em; }
.welcome-hint { margin: 0; font-size: 12px; color: rgba(255,255,255,0.65); }

.welcome-banner__deco { position: relative; display: flex; align-items: center; justify-content: center; z-index: 1; }

.deco-ring { position: absolute; border-radius: 50%; border: 2px solid rgba(255,255,255,0.14); }
.deco-ring--1 { width: 70px; height: 70px; }
.deco-ring--2 { width: 100px; height: 100px; }

/* ── 统计行 ── */
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.stat-card {
  background: #fff;
  border-radius: 18px;
  padding: 14px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.stat-card__icon {
  width: 40px; height: 40px;
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
}

.stat-card strong { font-size: 22px; font-weight: 800; line-height: 1; }
.stat-card span { font-size: 11px; color: #9aa3b2; text-align: center; }

/* ── Section ── */
.section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.section__head span { font-size: 15px; font-weight: 800; color: #1a2035; }
.section__head em { font-style: normal; font-size: 12px; color: #9aa3b2; }

/* ── 智课列表 ── */
.lesson-list { display: flex; flex-direction: column; gap: 10px; }

.lesson-card {
  display: flex;
  align-items: flex-start;
  background: #fff;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  cursor: pointer;
  transition: transform 0.15s;
  padding-right: 16px;
}

.lesson-card:active { transform: scale(0.98); }

.lesson-card__bar {
  width: 5px;
  align-self: stretch;
  flex-shrink: 0;
  margin-right: 14px;
}

.lesson-card__cover-wrap {
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

.lesson-card__cover {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.lesson-card__subject-tag {
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

.lesson-card__generating-badge {
  position: absolute;
  top: 6px;
  left: 0;
  right: 0;
  margin: 0 auto;
  width: fit-content;
  display: flex;
  align-items: center;
  font-size: 9.5px;
  font-weight: 700;
  color: #fff;
  background: rgba(245, 158, 11, 0.88);
  backdrop-filter: blur(6px);
  padding: 2px 7px;
  border-radius: 999px;
}

.lesson-card__body {
  flex: 1;
  min-width: 0;
  padding: 14px 0;
}

.lesson-card__body h4 {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 700;
  color: #1a2035;
  line-height: 1.45;
}

.lesson-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.lesson-card__meta span {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: #9aa3b2;
}

.lesson-card__actions { display: flex; gap: 7px; }

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 11px;
  border-radius: 8px;
  border: 1.5px solid #e4e8ef;
  background: #fff;
  color: #6b7a90;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.action-btn--primary {
  background: linear-gradient(135deg, #1677ff, #2a8aff);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 3px 10px rgba(22,119,255,0.26);
}

.action-btn--danger {
  border-color: #fecaca;
  color: #dc2626;
  background: #fff7f7;
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

</style>
