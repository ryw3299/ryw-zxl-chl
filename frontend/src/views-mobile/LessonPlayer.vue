<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  buildAudioUrl,
  getAudioStatus,
  getLessonPreviewImageUrl,
  getLessonPreviewMeta,
  getScriptStatus,
  renderLessonPpt,
} from '@/api/lesson'
import { trackProgress } from '@/api/progress'
import { normalizeScriptSections } from '@/utils/lessonRuntime'
import { useLessonStore } from '@/store/lessonStore'

import LearnTab from '@/views-mobile/tabs/LearnTab.vue'
import AssistantTab from '@/views-mobile/tabs/AssistantTab.vue'
import PracticeTab from '@/views-mobile/tabs/PracticeTab.vue'

const route = useRoute()
const router = useRouter()
const lessonStore = useLessonStore()

const VIRTUAL_TEACHER_URL = '/build/web-mobile-001/index.html?level=2'
const TEACHER_IDLE_SPEED = 0.4
const TEACHER_TALK_SPEED = 0.3
const TEACHER_TALK_LOOP_MS = 3600

const activeTab = ref('learn')
const previewLoading = ref(false)
const previewError = ref('')
const previewSlideCount = ref(0)
const previewImageFailed = ref(false)
const previewImageVersion = ref(0)
const teacherIframeRef = ref(null)
const virtualTeacherVisible = ref(false)
const scriptLoading = ref(false)
const previewRenderRequested = ref(false)
let teacherReadyTimer = null
let teacherTalkLoopTimer = null
let previewPollTimer = null

const normalizeQuery = (value, fallback = '') => {
  if (Array.isArray(value)) return value[0] || fallback
  return typeof value === 'string' ? value : fallback
}

const syncContext = () => {
  lessonStore.syncPlatformContext({
    courseId: normalizeQuery(route.query.courseId, lessonStore.courseInfo.courseId),
    lessonId: normalizeQuery(route.params.lessonId, lessonStore.lessonInfo.lessonId),
    userId: normalizeQuery(route.query.userId, lessonStore.platformContext.userId),
    role: normalizeQuery(route.query.role, lessonStore.platformContext.role || 'student'),
    token: normalizeQuery(route.query.token, lessonStore.platformContext.token),
    schoolId: normalizeQuery(route.query.schoolId, lessonStore.platformContext.schoolId),
  })
  if (route.query.courseName) {
    lessonStore.setCourseInfo({
      courseId: normalizeQuery(route.query.courseId, lessonStore.courseInfo.courseId),
      courseName: normalizeQuery(route.query.courseName, lessonStore.courseInfo.courseName),
    })
  }
}

const currentLessonId = computed(() => normalizeQuery(
  route.params.lessonId,
  lessonStore.lessonInfo.lessonId || lessonStore.platformContext.lessonId,
))

const totalPages = computed(() => Math.max(
  1,
  Number(previewSlideCount.value || lessonStore.lessonInfo.totalPages || 1),
))

const safeCurrentPage = computed(() => {
  const current = Number(lessonStore.lessonInfo.currentPage || 1)
  return Math.min(Math.max(1, current), totalPages.value)
})

const progressPercent = computed(() => Math.max(
  0,
  Math.min(100, Number(lessonStore.learningProgress.overallProgress || 0)),
))

const displayCourseTitle = computed(() =>
  normalizeQuery(route.query.courseName) ||
  lessonStore.courseInfo.courseName ||
  normalizeQuery(route.query.courseId, '课程学习'),
)

const displaySectionTitle = computed(() =>
  lessonStore.learningProgress.currentSectionTitle || lessonStore.currentSection?.title || '当前章节',
)

const pageRatio = computed(() => totalPages.value <= 1
  ? 0
  : Math.round((safeCurrentPage.value / totalPages.value) * 100),
)

const previewImageUrl = computed(() => {
  if (!currentLessonId.value) return ''
  return getLessonPreviewImageUrl(currentLessonId.value, safeCurrentPage.value, {
    v: previewImageVersion.value,
  })
})

const activeComponent = computed(() => {
  if (activeTab.value === 'assistant') return AssistantTab
  if (activeTab.value === 'practice') return PracticeTab
  return LearnTab
})

const currentScriptId = computed(() => normalizeQuery(route.query.scriptId))

const clearPreviewPollTimer = () => {
  if (previewPollTimer) {
    clearTimeout(previewPollTimer)
    previewPollTimer = null
  }
}

const schedulePreviewRefresh = (delay = 2500) => {
  clearPreviewPollTimer()
  previewPollTimer = setTimeout(() => loadPreviewMeta({ silent: true }), delay)
}

const loadScriptStructure = async () => {
  if (!currentScriptId.value || scriptLoading.value) return
  scriptLoading.value = true
  try {
    const result = await getScriptStatus(currentScriptId.value)
    const sections = normalizeScriptSections(result?.scriptStructure || [])
    if (!sections.length) return
    lessonStore.setLessonInfo({
      lessonId: currentLessonId.value,
      scriptId: currentScriptId.value,
      audioId: result?.audioId || lessonStore.lessonInfo.audioId || '',
      sections,
      currentSectionId: sections[0].sectionId,
      currentPage: sections[0].page || 1,
    })
    if (result?.audioId && !normalizeQuery(route.query.audioId)) {
      initAudio(result.audioId)
    }
  } catch {
    // 脚本加载失败时保留 store 中的演示章节，PPT 预览仍可继续尝试加载。
  } finally {
    scriptLoading.value = false
  }
}

const requestPreviewRender = async () => {
  if (!currentLessonId.value || previewRenderRequested.value) return false
  previewRenderRequested.value = true
  try {
    await renderLessonPpt(currentLessonId.value)
    previewError.value = 'PPT 正在生成预览...'
    schedulePreviewRefresh()
    return true
  } catch (error) {
    previewError.value = error?.message || 'PPT 预览生成失败'
    return false
  }
}

const loadPreviewMeta = async ({ silent = false } = {}) => {
  if (!currentLessonId.value) return
  previewLoading.value = !silent
  if (!silent) previewError.value = ''
  previewImageFailed.value = false
  try {
    const previewData = await getLessonPreviewMeta(currentLessonId.value)
    const taskStatus = previewData?.taskStatus || 'idle'
    const slideCount = Math.max(0, Number(previewData?.slideCount || 0))
    previewSlideCount.value = slideCount
    if (slideCount > 0) {
      clearPreviewPollTimer()
      previewImageVersion.value += 1
      lessonStore.setLessonInfo({
        totalPages: slideCount,
        currentPage: Math.min(Math.max(1, Number(lessonStore.lessonInfo.currentPage || 1)), slideCount),
      })
    } else if (previewRenderRequested.value) {
      previewError.value = 'PPT 正在生成预览...'
      schedulePreviewRefresh()
    } else if (taskStatus === 'processing') {
      previewError.value = 'PPT 正在生成预览...'
      schedulePreviewRefresh()
    } else {
      const started = await requestPreviewRender()
      if (!started) previewError.value = previewData?.errorMessage || '暂未生成预览图'
    }
  } catch (error) {
    const message = error?.message || '加载失败'
    if (/not been generated|not ready|暂未生成|预览/i.test(message)) {
      const started = await requestPreviewRender()
      if (!started) previewError.value = message
    } else {
      previewError.value = message
    }
  } finally {
    previewLoading.value = false
  }
}

const trackUserProgress = async () => {
  if (!lessonStore.platformContext.userId || !currentLessonId.value) return
  try {
    await trackProgress({
      userId: lessonStore.platformContext.userId,
      courseId: lessonStore.platformContext.courseId || lessonStore.courseInfo.courseId,
      lessonId: currentLessonId.value,
      currentSectionId: lessonStore.lessonInfo.currentSectionId,
      progressPercent: pageRatio.value,
    })
  } catch { /* 忽略统计错误 */ }
}

const prevPage = () => {
  if (safeCurrentPage.value > 1) lessonStore.setCurrentPage(safeCurrentPage.value - 1)
}

const nextPage = () => {
  if (safeCurrentPage.value < totalPages.value) lessonStore.setCurrentPage(safeCurrentPage.value + 1)
}

const selectSection = (item) => {
  const sectionId = item?.sectionId || item?.id
  if (!sectionId) return
  lessonStore.setCurrentSection(sectionId)
  const targetPage = item?.page || item?.relatedPages?.[0]
  if (targetPage) lessonStore.setCurrentPage(targetPage)
}

// ── 虚拟老师 ──
const clearTeacherReadyTimer = () => {
  if (teacherReadyTimer) { clearInterval(teacherReadyTimer); teacherReadyTimer = null }
}
const clearTeacherTalkLoopTimer = () => {
  if (teacherTalkLoopTimer) { clearTimeout(teacherTalkLoopTimer); teacherTalkLoopTimer = null }
}
const getTeacherAPI = () => teacherIframeRef.value?.contentWindow?.teacherAPI
const playTeacherIdle = () => {
  clearTeacherTalkLoopTimer()
  try { getTeacherAPI()?.playIdle1?.(TEACHER_IDLE_SPEED) } catch { /* ignore */ }
}
const playTeacherTalk = () => {
  clearTeacherTalkLoopTimer()
  try { getTeacherAPI()?.playTalkImmediately?.(TEACHER_TALK_SPEED) } catch { /* ignore */ }
  const loop = () => {
    try {
      getTeacherAPI()?.playTalkImmediately?.(TEACHER_TALK_SPEED)
      teacherTalkLoopTimer = setTimeout(loop, TEACHER_TALK_LOOP_MS)
    } catch { clearTeacherTalkLoopTimer() }
  }
  teacherTalkLoopTimer = setTimeout(loop, TEACHER_TALK_LOOP_MS)
}
const makeTeacherIframeTransparent = () => {
  const iframe = teacherIframeRef.value
  if (!iframe?.contentDocument) return false
  try {
    const doc = iframe.contentDocument
    const targets = [doc.documentElement, doc.body, doc.getElementById('GameDiv'), doc.getElementById('Cocos3dGameContainer'), doc.getElementById('GameCanvas')]
    targets.forEach((el) => { if (el) { el.style.background = 'transparent'; el.style.backgroundColor = 'transparent' } })
    return true
  } catch { return false }
}
const initVirtualTeacher = () => {
  virtualTeacherVisible.value = false
  clearTeacherReadyTimer()
  teacherReadyTimer = setInterval(() => {
    makeTeacherIframeTransparent()
    if (!getTeacherAPI()) return
    playTeacherIdle()
    virtualTeacherVisible.value = true
    clearTeacherReadyTimer()
  }, 500)
}
const handleTeacherIframeLoad = () => {
  virtualTeacherVisible.value = false
  setTimeout(() => { makeTeacherIframeTransparent(); initVirtualTeacher() }, 120)
}

// ── 音频播放 ─────────────────────────────────────────────────────────
const isPlaying = ref(false)
const audioProgress = ref(0)  // 0-100，绑定到进度条

let audioEl = null
let sectionAudioMap = {}
let activeAudioId = ''

const loadSectionAudio = () => {
  if (!audioEl) return
  const sectionId = lessonStore.currentSection?.sectionId
  const url = sectionId && sectionAudioMap[sectionId]
  if (!url) return
  audioEl.src = url
  audioEl.load()
}

const initAudio = async (nextAudioId = '') => {
  const audioId = normalizeQuery(nextAudioId) || normalizeQuery(route.query.audioId) || lessonStore.lessonInfo.audioId || ''
  if (!audioId || activeAudioId === audioId) return
  if (audioEl) {
    audioEl.pause()
    audioEl.src = ''
    audioEl = null
  }
  activeAudioId = audioId
  sectionAudioMap = {}

  try {
    const status = await getAudioStatus(audioId)
    const sections = status?.sectionAudios || []
    if (!sections.length) return

    sections.forEach(({ sectionId }) => {
      sectionAudioMap[sectionId] = buildAudioUrl(audioId, sectionId)
    })

    audioEl = new Audio()
    audioEl.preload = 'metadata'

    audioEl.addEventListener('timeupdate', () => {
      if (!audioEl.duration) return
      audioProgress.value = Math.round((audioEl.currentTime / audioEl.duration) * 100)
    })

    audioEl.addEventListener('ended', () => {
      audioProgress.value = 100
      isPlaying.value = false
      playTeacherIdle()
      // 自动下一章节
      const sections = lessonStore.lessonInfo.sections || []
      const idx = sections.findIndex(s => s.sectionId === lessonStore.currentSection?.sectionId)
      if (idx >= 0 && idx < sections.length - 1) {
        lessonStore.setCurrentSection(sections[idx + 1].sectionId)
        loadSectionAudio()
        audioEl.play().catch(() => {})
        isPlaying.value = true
        playTeacherTalk()
      }
    })

    loadSectionAudio()
  } catch {
    activeAudioId = ''
  }
}

const togglePlay = () => {
  if (audioEl && audioEl.src) {
    if (isPlaying.value) {
      audioEl.pause()
      playTeacherIdle()
    } else {
      audioEl.play().catch(() => {})
      playTeacherTalk()
    }
    isPlaying.value = !isPlaying.value
  } else {
    isPlaying.value = !isPlaying.value
    if (isPlaying.value) playTeacherTalk()
    else playTeacherIdle()
  }
}

watch(() => lessonStore.currentSection?.sectionId, () => {
  if (!audioEl) return
  const wasPlaying = isPlaying.value
  audioProgress.value = 0
  loadSectionAudio()
  if (wasPlaying) audioEl.play().catch(() => {})
})

// ── 全屏 ──
const isFullscreen = ref(false)
const fsBarsVisible = ref(false)
let fsBarsTimer = null

const showFsBars = () => {
  fsBarsVisible.value = true
  clearTimeout(fsBarsTimer)
  fsBarsTimer = setTimeout(() => { fsBarsVisible.value = false }, 3000)
}

const enterFullscreen = () => {
  isFullscreen.value = true
  screen.orientation?.lock?.('landscape').catch(() => {})
  showFsBars()
}

const exitFullscreen = () => {
  isFullscreen.value = false
  screen.orientation?.unlock?.()
  clearTimeout(fsBarsTimer)
  fsBarsVisible.value = false
}

const onKeydown = (e) => { if (e.key === 'Escape') exitFullscreen() }

watch(() => route.fullPath, () => {
  syncContext()
  previewRenderRequested.value = false
  loadScriptStructure()
  loadPreviewMeta()
  initAudio()
})
watch(() => safeCurrentPage.value, () => { previewImageFailed.value = false; trackUserProgress() })
onMounted(() => {
  syncContext()
  loadScriptStructure()
  loadPreviewMeta()
  initVirtualTeacher()
  initAudio()
  document.addEventListener('keydown', onKeydown)
})
onUnmounted(() => {
  clearTeacherReadyTimer()
  clearTeacherTalkLoopTimer()
  clearPreviewPollTimer()
  clearTimeout(fsBarsTimer)
  document.removeEventListener('keydown', onKeydown)
  screen.orientation?.unlock?.()
  if (audioEl) { audioEl.pause(); audioEl.src = ''; audioEl = null }
})
</script>

<template>
  <div class="player-page">

    <!-- ── PPT 舞台区 ── -->
    <div class="stage-wrap">

      <!-- 悬浮顶栏（叠加在 PPT 上） -->
      <div class="stage-header">
        <button class="header-btn" @click="router.push('/m/home')">
          <van-icon name="arrow-left" size="18" color="#fff" />
        </button>
        <div class="header-center">
          <span class="header-title">{{ displayCourseTitle }}</span>
          <span class="header-sub">{{ displaySectionTitle }}</span>
        </div>
      </div>

      <!-- 幻灯片 -->
      <div class="slide-viewport">
        <div v-if="previewLoading" class="slide-state">
          <van-loading color="rgba(255,255,255,0.8)" vertical size="28px">加载中...</van-loading>
        </div>
        <div v-else-if="previewError || previewImageFailed" class="slide-state">
          <van-icon name="warning-o" size="32" color="rgba(255,255,255,0.4)" />
          <p class="slide-state__text">{{ previewError || '图片加载失败' }}</p>
        </div>
        <img v-else :src="previewImageUrl" class="slide-img" @error="previewImageFailed = true" />
        <div class="slide-page-badge">{{ safeCurrentPage }} / {{ totalPages }}</div>

        <!-- 虚拟老师（竖屏正常模式） -->
        <div v-show="!isFullscreen" class="teacher-stage" :class="{ ready: virtualTeacherVisible }">
          <div v-if="!virtualTeacherVisible" class="teacher-stage-mask">加载中</div>
          <iframe
            ref="teacherIframeRef"
            class="teacher-frame"
            :src="VIRTUAL_TEACHER_URL"
            title="虚拟老师"
            scrolling="no"
            allow="autoplay"
            @load="handleTeacherIframeLoad"
          />
        </div>

      </div>

      <!-- 翻页控制栏 -->
      <div class="page-controls">
        <button class="play-pause-btn" :class="{ playing: isPlaying }" @click.stop="togglePlay">
          <svg v-if="!isPlaying" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="4" width="4" height="16" />
            <rect x="14" y="4" width="4" height="16" />
          </svg>
        </button>
        <button class="ctrl-btn" :disabled="safeCurrentPage <= 1" @click="prevPage">
          <van-icon name="arrow-left" size="13" />
          上一页
        </button>
        <van-progress
          :percentage="audioEl ? audioProgress : pageRatio"
          stroke-width="3"
          color="#1677ff"
          :show-pivot="false"
          class="ctrl-progress"
        />
        <span class="ctrl-pct">{{ audioEl ? audioProgress : pageRatio }}%</span>
        <button class="ctrl-btn ctrl-btn--primary" :disabled="safeCurrentPage >= totalPages" @click="nextPage">
          下一页
          <van-icon name="arrow" size="13" />
        </button>
        <button class="ctrl-btn ctrl-btn--icon" @click="enterFullscreen">
          <van-icon name="expand-o" size="26" />
        </button>
      </div>
    </div>

    <!-- ── 内容区 ── -->
    <div class="content-wrap">

      <!-- Segment 切换器 -->
      <div class="segment-ctrl">
        <button
          class="seg-btn"
          :class="{ 'is-active': activeTab === 'learn' }"
          @click="activeTab = 'learn'"
        >
          <van-icon name="notes-o" size="14" />
          学习内容
        </button>
        <button
          class="seg-btn"
          :class="{ 'is-active': activeTab === 'assistant' }"
          @click="activeTab = 'assistant'"
        >
          <van-icon name="chat-o" size="14" />
          AI 问答
        </button>
        <button
          class="seg-btn"
          :class="{ 'is-active': activeTab === 'practice' }"
          @click="activeTab = 'practice'"
        >
          <van-icon name="edit" size="14" />
          练习
        </button>
      </div>

      <!-- Tab 内容 -->
      <transition name="fade-up" mode="out-in">
        <component
          :is="activeComponent"
          :key="activeTab"
          :progress-percent="progressPercent"
          :section-title="displaySectionTitle"
          :understanding-label="lessonStore.learningProgress.understandingLevel || '稳步推进'"
          :stage-list="lessonStore.lessonInfo.sections || []"
          :sections="lessonStore.lessonInfo.sections || []"
          @select-section="selectSection"
        />
      </transition>
    </div>

  </div>

  <!-- ── 全屏覆盖层 ── -->
  <teleport to="body">
    <transition name="fs-fade">
      <div v-if="isFullscreen" class="fs-overlay" @click.self="showFsBars">

        <!-- 关闭按钮 -->
        <transition name="fs-bar-fade">
          <button v-show="fsBarsVisible" class="fs-close" @click="exitFullscreen">
            <van-icon name="cross" size="18" color="#fff" />
          </button>
        </transition>

        <!-- 课件图片 -->
        <img :src="previewImageUrl" class="fs-img" @click="showFsBars" @error="previewImageFailed = true" />

        <!-- 虚拟老师（横屏全屏模式） -->
        <div v-if="virtualTeacherVisible" class="fs-teacher">
          <iframe
            class="fs-teacher-frame"
            :src="VIRTUAL_TEACHER_URL"
            title="虚拟老师"
            scrolling="no"
            allow="autoplay"
          />
        </div>

        <!-- 播放条 -->
        <transition name="fs-bar-fade">
          <div v-show="fsBarsVisible" class="fs-controls" @click.stop>
            <button class="fs-play-btn" :class="{ playing: isPlaying }" @click="togglePlay">
              <svg v-if="!isPlaying" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16" />
                <rect x="14" y="4" width="4" height="16" />
              </svg>
            </button>
            <button class="fs-btn" :disabled="safeCurrentPage <= 1" @click="prevPage">
              <van-icon name="arrow-left" size="16" />
            </button>
            <van-progress
              :percentage="audioEl ? audioProgress : pageRatio"
              stroke-width="3"
              color="#1677ff"
              track-color="rgba(255,255,255,0.2)"
              :show-pivot="false"
              class="fs-progress"
            />
            <span class="fs-pct">{{ audioEl ? audioProgress : pageRatio }}%</span>
            <button class="fs-btn" :disabled="safeCurrentPage >= totalPages" @click="nextPage">
              <van-icon name="arrow" size="16" />
            </button>
            <span class="fs-page">{{ safeCurrentPage }} / {{ totalPages }}</span>
          </div>
        </transition>

      </div>
    </transition>
  </teleport>
</template>

<style scoped>
.player-page {
  min-height: 100vh;
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
}

/* ── 舞台区 ── */
.stage-wrap {
  background: #1a1a1a;
  position: relative;
  flex-shrink: 0;
}

/* 悬浮顶栏 */
.stage-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.55), transparent);
}

.header-btn {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: none;
  background: rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  backdrop-filter: blur(6px);
  transition: background 0.15s;
}

.header-btn:active {
  background: rgba(255, 255, 255, 0.22);
}

.header-center {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.header-title {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-sub {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.65);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 幻灯片 */
.slide-viewport {
  width: 100%;
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: #111;
}

.slide-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.slide-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.slide-state__text {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
}

.slide-page-badge {
  position: absolute;
  left: 12px;
  bottom: 10px;
  background: rgba(0, 0, 0, 0.45);
  color: rgba(255, 255, 255, 0.85);
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  backdrop-filter: blur(4px);
}

/* 虚拟老师 */
.teacher-stage {
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 9.33vw;
  max-width: 40px;
  aspect-ratio: 9 / 16;
  opacity: 0;
  transform: translateY(8px);
  transition: opacity 0.24s ease, transform 0.24s ease;
  pointer-events: none;
  z-index: 5;
}

.teacher-stage.ready {
  opacity: 1;
  transform: translateY(0);
}

.teacher-stage-mask {
  position: absolute;
  inset: auto 4px 8px 4px;
  padding: 3px 6px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.65);
  color: #fff;
  font-size: 9px;
  font-weight: 600;
  text-align: center;
  backdrop-filter: blur(6px);
}

.teacher-frame {
  width: 100%;
  height: 100%;
  display: block;
  border: none;
  background: transparent;
  pointer-events: none;
}

/* 播放暂停 */
.play-pause-btn {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: linear-gradient(135deg, #1677ff, #2a8aff);
  color: #fff;
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.35);
  transition: transform 0.15s, box-shadow 0.15s;
}

.play-pause-btn.playing {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.35);
}

.play-pause-btn:active {
  transform: scale(0.93);
}

/* 翻页控制 */
.page-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px 12px;
  background: #fff;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.ctrl-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border-radius: 10px;
  border: 1.5px solid #e4e8ef;
  background: #fff;
  color: #6b7a90;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.ctrl-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.ctrl-btn:not(:disabled):active {
  background: #f5f7fa;
}

.ctrl-btn--primary {
  background: linear-gradient(135deg, #1677ff, #2a8aff);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.28);
}

.ctrl-btn--primary:not(:disabled):active {
  background: #1264d4;
}

.ctrl-progress {
  flex: 1;
}

.ctrl-pct {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: #1677ff;
  min-width: 30px;
  text-align: center;
}

/* ── 内容区 ── */
.content-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 14px 14px 28px;
  gap: 14px;
}

/* Segment 切换器 */
.segment-ctrl {
  display: flex;
  gap: 0;
  background: #e8ecf2;
  border-radius: 14px;
  padding: 4px;
}

.seg-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 38px;
  border-radius: 11px;
  border: none;
  background: transparent;
  color: #6b7a90;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.seg-btn.is-active {
  background: #fff;
  color: #1677ff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.09);
}


.ctrl-btn--icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: none;
  background: #fff;
  color: #6b7a90;
  cursor: pointer;
}

/* ── 全屏覆盖层 ── */
.fs-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 竖屏时旋转 90° 模拟横屏 */
@media (orientation: portrait) {
  .fs-overlay {
    transform: rotate(90deg);
    transform-origin: center center;
    width: 100vh;
    height: 100vw;
    top: calc((100vh - 100vw) / 2);
    left: calc((100vw - 100vh) / 2);
    position: fixed;
  }
}

.fs-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.fs-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: none;
  background: rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  backdrop-filter: blur(6px);
  z-index: 1;
}

.fs-controls {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 20px;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(8px);
  padding: 10px 24px;
  border-radius: 999px;
}

.fs-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s;
}

.fs-teacher {
  position: absolute;
  right: 12px;
  bottom: 64px;
  /* 横屏时 PPT 被高度撑满，宽 = 100vh×16/9，教师占其 9.33% ≈ 14.9vh */
  width: 14.9vh;
  aspect-ratio: 9 / 16;
  z-index: 1;
  pointer-events: none;
}

.fs-teacher-frame {
  width: 100%;
  height: 100%;
  border: none;
  background: transparent;
  display: block;
  pointer-events: none;
}

.fs-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.fs-btn:not(:disabled):active {
  background: rgba(255, 255, 255, 0.28);
}

.fs-page {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  min-width: 50px;
  text-align: center;
}

.fs-play-btn {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: linear-gradient(135deg, #1677ff, #2a8aff);
  color: #fff;
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.4);
  transition: transform 0.15s;
}

.fs-play-btn.playing {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
}

.fs-play-btn:active {
  transform: scale(0.9);
}

.fs-progress {
  flex: 1;
}

.fs-pct {
  font-size: 12px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.85);
  min-width: 28px;
  text-align: center;
}

.fs-bar-fade-enter-active,
.fs-bar-fade-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.fs-bar-fade-enter-from,
.fs-bar-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* ── 动画 ── */
.fade-up-enter-active,
.fade-up-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.fs-fade-enter-active,
.fs-fade-leave-active {
  transition: opacity 0.2s ease;
}
.fs-fade-enter-from,
.fs-fade-leave-to {
  opacity: 0;
}
</style>
