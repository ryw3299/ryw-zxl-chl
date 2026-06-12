<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  buildAudioUrl,
  getAudioStatus,
  getCoursewareStatus,
  getLessonPreviewImageUrl,
  getLessonPreviewMeta,
  getLessonNarration,
  getNarrationAudioStatus,
  getScriptStatus,
  renderLessonPpt,
} from '@/api/lesson'
import { trackProgress } from '@/api/progress'
import ChatBox from '@/components/ChatBox.vue'
import { normalizeScriptSections } from '@/utils/lessonRuntime'
import { useLessonStore } from '@/store/lessonStore'

const route = useRoute()
const router = useRouter()
const lessonStore = useLessonStore()

const VIRTUAL_TEACHER_URL = '/build/web-mobile-001/index.html?level=2'
const TEACHER_IDLE_SPEED = 0.4
const TEACHER_TALK_SPEED = 0.3
const TEACHER_TALK_LOOP_MS = 900
const DEFAULT_NARRATION_LEVEL = 'D'
const NARRATION_LEVELS = ['A', 'B', 'C', 'D']
const SIMPLE_NARRATION_FALLBACK_ORDER = ['D', 'C', 'B', 'A']
const NARRATION_LEVEL_LABELS = { A: '拓展', B: '标准', C: '精简', D: '基础' }
const NARRATION_LEVEL_COLORS = { A: '#7c3aed', B: '#2563eb', C: '#0f766e', D: '#64748b' }

const { platformContext, courseInfo, lessonInfo, explainStatus, learningProgress, sessionInfo, currentSection, highlightedPages } = storeToRefs(lessonStore)

const catalogCollapsed = ref(false)
const showResumePrompt = ref(false)
const voiceProgress = ref(0)
const noteText = ref('')
const noteSavedAt = ref('')
const quickReviewPoints = ref([])
const currentNarrationLevel = ref(DEFAULT_NARRATION_LEVEL)
const narrationLevelFlash = ref(false)
const activeRightTab = ref('chat')
const controlsVisible = ref(true)
const catalogOpen = ref(false)
const previewLoading = ref(false)
const previewError = ref('')
const previewSlideCount = ref(0)
const previewImageFailed = ref(false)
const previewImageVersion = ref(0)
const previewTaskStatus = ref('idle')
const lastQaRecordId = ref('')
const teacherIframeRef = ref(null)
const virtualTeacherVisible = ref(false)
const scriptLoading = ref(false)
const previewRenderRequested = ref(false)
// ── 真实音频播放 ──────────────────────────────────────────────────────
let audioEl = null              // HTMLAudioElement
let sectionAudioMap = {}       // { sectionId: url }
let pageAudioMap = {}          // { pageNumber: url }
const audioReady = ref(false)  // 音频资源已加载
let activeAudioId = ''
let activeAudioSrc = ''
const narrationAudioTasks = ref({})

let voiceTimer = null
let hideControlsTimer = null
let previewPollTimer = null
let progressTrackTimer = null
let teacherReadyTimer = null
let teacherTalkLoopTimer = null

const normalizeQuery = (v, d = '') => (Array.isArray(v) ? v[0] || d : (typeof v === 'string' ? v : d))
const syncContext = () => {
  lessonStore.syncPlatformContext({
    courseId: normalizeQuery(route.query.courseId, courseInfo.value.courseId),
    userId: normalizeQuery(route.query.userId, platformContext.value.userId),
    lessonId: normalizeQuery(route.query.lessonId, lessonInfo.value.lessonId),
    role: normalizeQuery(route.query.role, platformContext.value.role),
    token: normalizeQuery(route.query.token, platformContext.value.token),
  })
  if (route.query.courseName) {
    lessonStore.setCourseInfo({
      courseId: normalizeQuery(route.query.courseId, courseInfo.value.courseId),
      courseName: normalizeQuery(route.query.courseName, courseInfo.value.courseName),
    })
  }
}

const statusMap = {
  idle: { text: '待开始', color: '#94a3b8', bg: 'rgba(148,163,184,0.15)', dot: '#94a3b8' },
  explaining: { text: '讲解中', color: '#0f766e', bg: 'rgba(20,184,166,0.14)', dot: '#14b8a6' },
  paused: { text: '已暂停', color: '#b45309', bg: 'rgba(245,158,11,0.14)', dot: '#f59e0b' },
  qa: { text: '问答中', color: '#2563eb', bg: 'rgba(37,99,235,0.12)', dot: '#3b82f6' },
}
const statusDisplay = computed(() => statusMap[explainStatus.value] || statusMap.idle)
const sectionOptions = computed(() => lessonInfo.value.sections || [])
const isExplaining = computed(() => explainStatus.value === 'explaining')
const canResume = computed(() => explainStatus.value === 'paused')
const effectiveTotalPages = computed(() => {
  const previewTotal = Number(previewSlideCount.value || 0)
  if (previewTotal > 0) {
    return previewTotal
  }
  return Math.max(1, Number(lessonInfo.value.totalPages || 1))
})
const safeCurrentPage = computed(() => {
  const page = Number(lessonInfo.value.currentPage || 1)
  const max = effectiveTotalPages.value
  return Math.min(Math.max(1, page), max)
})
const canPrevPage = computed(() => safeCurrentPage.value > 1)
const canNextPage = computed(() => safeCurrentPage.value < effectiveTotalPages.value)
const currentLessonId = computed(() => (
  platformContext.value.lessonId
  || lessonInfo.value.lessonId
  || normalizeQuery(route.query.lessonId)
))
const currentScriptId = computed(() => normalizeQuery(route.query.scriptId))
const previewReady = computed(() => (
  Boolean(currentLessonId.value)
  && previewSlideCount.value > 0
))
const carouselSlides = computed(() => {
  if (!previewReady.value) {
    return []
  }
  return Array.from({ length: previewSlideCount.value }, (_, index) => {
    const slideNumber = index + 1
    return {
      slideNumber,
      active: slideNumber === safeCurrentPage.value,
    }
  })
})
const currentPreviewImageUrl = computed(() => {
  if (!previewReady.value) {
    return ''
  }
  return getLessonPreviewImageUrl(currentLessonId.value, safeCurrentPage.value, {
    v: previewImageVersion.value,
  })
})
const previewPlaceholderText = computed(() => {
  if (previewLoading.value || previewTaskStatus.value === 'processing') {
    return '正在加载 PPT 预览...'
  }
  return previewError.value || 'PPT 预览加载失败'
})
const catalogItems = computed(() => sectionOptions.value.map((item, index) => ({
  id: item.sectionId,
  title: item.title || `章节 ${index + 1}`,
  desc: (item.keywords || []).slice(0, 3).join(' | ') || '暂无简介',
})))
const normalizeSlidePlanSections = (slidePlan = {}) => {
  const slides = Array.isArray(slidePlan?.slides) ? slidePlan.slides : []
  return slides.map((slide, index) => {
    const page = Number(slide.pageNumber || slide.page_number || slide.slideNumber || slide.slide_number || index + 1)
    const safePage = Number.isFinite(page) && page > 0 ? page : index + 1
    const title = slide.title || slide.heading || slide.name || `第 ${index + 1} 页`
    const rawPoints = slide.keyPoints || slide.key_points || slide.points || slide.bullets || slide.objectives || []
    const keywords = (Array.isArray(rawPoints) ? rawPoints : [])
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') return item.text || item.title || item.content || item.point || ''
        return ''
      })
      .filter(Boolean)
      .slice(0, 3)

    return {
      sectionId: slide.id || slide.slideId || slide.slide_id || `slide-${safePage}`,
      id: slide.id || slide.slideId || slide.slide_id || `slide-${safePage}`,
      title,
      sectionName: title,
      explainScript: slide.teachingGoal || slide.teaching_goal || slide.goal || slide.summary || '',
      content: slide.subtitle || slide.description || slide.summary || slide.teachingGoal || slide.teaching_goal || '',
      keywords,
      keyPoints: keywords,
      relatedPages: [safePage],
      page: safePage,
    }
  }).filter((item) => item.sectionId)
}

const playbackPages = computed(() => {
  if (previewSlideCount.value > 0) return Array.from({ length: effectiveTotalPages.value }, (_, i) => i + 1)
  const secPages = currentSection.value?.relatedPages || []
  if (secPages.length) return [...new Set(secPages.map(Number).filter(Number.isFinite))]
  if (highlightedPages.value?.length) return [...new Set(highlightedPages.value.map(Number).filter(Number.isFinite))]
  return Array.from({ length: effectiveTotalPages.value }, (_, i) => i + 1)
})
const progressReportBucket = computed(() => Math.floor(Math.max(0, Math.min(100, voiceProgress.value)) / 10))

const noteStorageKey = computed(() => `lesson-note:${courseInfo.value.courseId || platformContext.value.courseId}:${lessonInfo.value.lessonId}`)
const loadNote = () => {
  if (typeof window === 'undefined') return
  const raw = localStorage.getItem(noteStorageKey.value)
  if (!raw) return
  try {
    const payload = JSON.parse(raw)
    noteText.value = payload.text || ''
    noteSavedAt.value = payload.savedAt || ''
    quickReviewPoints.value = Array.isArray(payload.quickPoints) ? payload.quickPoints : []
  } catch { localStorage.removeItem(noteStorageKey.value) }
}
const persistNote = () => {
  if (typeof window === 'undefined') return
  localStorage.setItem(noteStorageKey.value, JSON.stringify({ text: noteText.value, savedAt: noteSavedAt.value, quickPoints: quickReviewPoints.value }))
}
const saveNote = () => { noteSavedAt.value = new Date().toISOString(); persistNote(); ElMessage.success('笔记已保存') }
const clearNote = () => { noteText.value = ''; noteSavedAt.value = ''; quickReviewPoints.value = []; persistNote() }
const appendQuickPoint = (point) => {
  if (!point) return
  noteText.value = noteText.value ? `${noteText.value}\n- ${point}` : `- ${point}`
}

const clearTeacherReadyTimer = () => {
  if (teacherReadyTimer) {
    clearInterval(teacherReadyTimer)
    teacherReadyTimer = null
  }
}

const clearTeacherTalkLoopTimer = () => {
  if (teacherTalkLoopTimer) {
    clearTimeout(teacherTalkLoopTimer)
    teacherTalkLoopTimer = null
  }
}

const getTeacherAPI = () => teacherIframeRef.value?.contentWindow?.teacherAPI

const playTeacherIdle = () => {
  clearTeacherTalkLoopTimer()
  try {
    getTeacherAPI()?.stopTalk?.()
    getTeacherAPI()?.playIdle1?.(TEACHER_IDLE_SPEED)
  } catch {
    // Ignore animation failures from the embedded virtual teacher.
  }
}

const playTeacherTalk = () => {
  clearTeacherTalkLoopTimer()

  const teacherAPI = getTeacherAPI()
  try {
    if (teacherAPI?.startTalk) {
      teacherAPI.startTalk(TEACHER_TALK_SPEED)
      return
    }
    if (teacherAPI?.playTalkLoop) {
      teacherAPI.playTalkLoop(TEACHER_TALK_SPEED)
      return
    }
    if (teacherAPI?.playTalk1) {
      teacherAPI.playTalk1(TEACHER_TALK_SPEED)
      return
    }
    teacherAPI?.playTalkImmediately?.(TEACHER_TALK_SPEED)
  } catch {
    // Ignore animation failures from the embedded virtual teacher.
  }

  const loopTalk = () => {
    if (explainStatus.value !== 'explaining') {
      clearTeacherTalkLoopTimer()
      return
    }

    try {
      teacherAPI?.playTalkImmediately?.(TEACHER_TALK_SPEED)
      teacherTalkLoopTimer = setTimeout(loopTalk, TEACHER_TALK_LOOP_MS)
    } catch {
      clearTeacherTalkLoopTimer()
    }
  }

  teacherTalkLoopTimer = setTimeout(loopTalk, TEACHER_TALK_LOOP_MS)
}

const makeTeacherIframeTransparent = () => {
  const iframe = teacherIframeRef.value
  if (!iframe?.contentDocument) {
    return false
  }

  try {
    const doc = iframe.contentDocument
    const html = doc.documentElement
    const body = doc.body
    const gameDiv = doc.getElementById('GameDiv')
    const container = doc.getElementById('Cocos3dGameContainer')
    const canvas = doc.getElementById('GameCanvas')

    if (html) html.style.background = 'transparent'
    if (body) {
      body.style.background = 'transparent'
      body.style.backgroundColor = 'transparent'
    }
    if (gameDiv) {
      gameDiv.style.background = 'transparent'
      gameDiv.style.backgroundColor = 'transparent'
    }
    if (container) {
      container.style.background = 'transparent'
      container.style.backgroundColor = 'transparent'
    }
    if (canvas) {
      canvas.style.background = 'transparent'
      canvas.style.backgroundColor = 'transparent'
    }
    return true
  } catch {
    return false
  }
}

const initVirtualTeacher = () => {
  virtualTeacherVisible.value = false
  clearTeacherReadyTimer()
  teacherReadyTimer = setInterval(() => {
    const teacherAPI = getTeacherAPI()
    makeTeacherIframeTransparent()

    if (!teacherAPI) {
      return
    }

    playTeacherIdle()
    virtualTeacherVisible.value = true
    clearTeacherReadyTimer()
  }, 500)
}

const handleTeacherIframeLoad = () => {
  virtualTeacherVisible.value = false
  setTimeout(() => {
    makeTeacherIframeTransparent()
    initVirtualTeacher()
  }, 120)
}

const clearPreviewPollTimer = () => {
  if (previewPollTimer) {
    clearTimeout(previewPollTimer)
    previewPollTimer = null
  }
}

const schedulePreviewRefresh = (delay = 2500) => {
  clearPreviewPollTimer()
  previewPollTimer = setTimeout(() => {
    loadPreviewMeta({ silent: true })
  }, delay)
}

const loadScriptStructure = async () => {
  if (scriptLoading.value) return
  scriptLoading.value = true
  try {
    let result = null
    let sections = []

    if (currentScriptId.value) {
      result = await getScriptStatus(currentScriptId.value)
      sections = normalizeScriptSections(result?.scriptStructure || [])
    }

    if (!sections.length && currentLessonId.value) {
      const courseware = await getCoursewareStatus(currentLessonId.value)
      sections = normalizeSlidePlanSections(courseware?.slidePlan || {})
    }

    if (!sections.length) {
      await initNarrationAudio(currentNarrationLevel.value)
      return
    }
    lessonStore.setLessonInfo({
      lessonId: currentLessonId.value,
      scriptId: currentScriptId.value || lessonInfo.value.scriptId || '',
      audioId: result?.audioId || lessonInfo.value.audioId || '',
      sections,
      currentSectionId: sections[0].sectionId,
      currentPage: sections[0].page || 1,
    })
    if (result?.audioId && !normalizeQuery(route.query.audioId)) {
      initAudio(result.audioId)
    }
  } catch {
    // 保留本地演示章节，不阻塞 PPT 学习页。
  } finally {
    scriptLoading.value = false
  }
}

const requestPreviewRender = async () => {
  if (!currentLessonId.value || previewRenderRequested.value) return false
  previewRenderRequested.value = true
  try {
    await renderLessonPpt(currentLessonId.value)
    previewTaskStatus.value = 'processing'
    previewError.value = 'PPT 正在生成预览...'
    schedulePreviewRefresh()
    return true
  } catch (error) {
    previewError.value = error?.response?.data?.msg || error?.message || 'PPT 预览生成失败'
    return false
  }
}

const loadPreviewMeta = async ({ silent = false } = {}) => {
  if (!currentLessonId.value) {
    previewSlideCount.value = 0
    previewImageFailed.value = false
    previewTaskStatus.value = 'idle'
    previewError.value = ''
    clearPreviewPollTimer()
    return
  }

  previewLoading.value = !silent
  if (!silent) {
    previewError.value = ''
  }
  previewImageFailed.value = false

  try {
    const previewData = await getLessonPreviewMeta(currentLessonId.value)
    previewTaskStatus.value = previewData?.taskStatus || 'idle'
    syncNarrationAudioTasks(previewData?.narrationAudioTasks || {})
    if (!audioReady.value) {
      initNarrationAudio(currentNarrationLevel.value)
    }
    previewSlideCount.value = Math.max(0, Number(previewData?.slideCount || 0))
    if (previewSlideCount.value > 0) {
      previewImageVersion.value += 1
      lessonStore.setLessonInfo({
        totalPages: previewSlideCount.value,
        currentPage: Math.min(
          Math.max(1, Number(lessonInfo.value.currentPage || 1)),
          previewSlideCount.value,
        ),
      })
    } else if (previewRenderRequested.value) {
      previewTaskStatus.value = 'processing'
      previewError.value = 'PPT 正在生成预览...'
      schedulePreviewRefresh()
    } else if (previewData?.errorMessage) {
      const started = await requestPreviewRender()
      if (!started) previewError.value = previewData.errorMessage
    } else if (previewTaskStatus.value !== 'processing') {
      await requestPreviewRender()
    }

    if (previewTaskStatus.value === 'processing') {
      schedulePreviewRefresh()
    } else {
      clearPreviewPollTimer()
    }
  } catch (error) {
    previewSlideCount.value = 0
    previewImageFailed.value = false
    previewTaskStatus.value = 'failed'
    const message = error?.response?.data?.msg || error?.message || 'PPT 预览加载失败'
    if (/not been generated|not ready|暂未生成|预览/i.test(message)) {
      const started = await requestPreviewRender()
      if (!started) previewError.value = message
    } else {
      previewError.value = message
      clearPreviewPollTimer()
    }
  } finally {
    previewLoading.value = false
  }
}

const handlePreviewImageError = () => {
  previewImageFailed.value = true
  previewError.value = previewError.value || 'PPT 预览图片加载失败'
}

const reportLearningProgress = async ({ qaRecordId = '' } = {}) => {
  if (!platformContext.value.userId || !currentLessonId.value || !lessonInfo.value.currentSectionId) {
    return
  }

  try {
    const result = await trackProgress({
      userId: platformContext.value.userId,
      courseId: platformContext.value.courseId || courseInfo.value.courseId,
      lessonId: currentLessonId.value,
      currentSectionId: lessonInfo.value.currentSectionId,
      progressPercent: Math.round(Math.max(0, Math.min(100, voiceProgress.value))),
      qaRecordId: qaRecordId || lastQaRecordId.value,
    })

    if (typeof result?.totalProgress === 'number') {
      lessonStore.setLearningProgress({ overallProgress: result.totalProgress })
    }
  } catch {
    // ignore progress tracking failures in the playback UI
  }
}

const scheduleLearningProgressReport = (options = {}) => {
  clearTimeout(progressTrackTimer)
  progressTrackTimer = setTimeout(() => {
    reportLearningProgress(options)
  }, 250)
}

const clearVoiceTimer = () => { if (voiceTimer) { clearInterval(voiceTimer); voiceTimer = null } }
const syncPageByProgress = () => {
  const pages = playbackPages.value
  if (!pages.length) return
  const index = Math.min(pages.length - 1, Math.floor((voiceProgress.value / 100) * pages.length))
  const page = Number(pages[index])
  if (Number.isFinite(page) && page !== Number(lessonInfo.value.currentPage)) lessonStore.setCurrentPage(page)
}

// ── 加载当前章节音频 ───────────────────────────────────────────────────
const loadSectionAudio = () => {
  if (!audioEl) return
  const pageUrl = pageAudioMap[safeCurrentPage.value]
  const sectionId = currentSection.value?.sectionId
  const url = pageUrl || (sectionId && sectionAudioMap[sectionId])
  if (!url) return
  if (activeAudioSrc === url) return
  activeAudioSrc = url
  voiceProgress.value = 0
  audioEl.src = url
  audioEl.load()
}

// ── 初始化音频元素 ────────────────────────────────────────────────────
const normalizeNarrationLevel = (level, fallback = DEFAULT_NARRATION_LEVEL) => {
  const normalized = normalizeQuery(level, fallback).toUpperCase()
  return NARRATION_LEVELS.includes(normalized) ? normalized : fallback
}

const syncNarrationAudioTasks = (tasks = {}) => {
  narrationAudioTasks.value = tasks && typeof tasks === 'object' ? tasks : {}
}

const extractAudioPageNumber = (item = {}, index = 0) => {
  const candidates = [item.pageNumber, item.page, item.slideNumber, item.slideIndex, item.slideId, item.sectionId]
  for (const candidate of candidates) {
    if (candidate === undefined || candidate === null) continue
    const numeric = Number(candidate)
    if (Number.isInteger(numeric) && numeric > 0) return numeric
    const match = String(candidate).match(/(\d+)(?!.*\d)/)
    if (match) {
      const parsed = Number(match[1])
      if (Number.isInteger(parsed) && parsed > 0) return parsed
    }
  }
  return index + 1
}

const resolveAudioSectionId = (item = {}) => (
  item.sectionId || item.section_id || item.id || item.slideId || ''
)

const buildPageAudioMapFromSections = (audioId, sections = []) => {
  const nextPageMap = {}
  const nextSectionMap = {}
  sections.forEach((item, index) => {
    const sectionId = resolveAudioSectionId(item)
    if (!sectionId) return
    const url = buildAudioUrl(audioId, sectionId)
    nextPageMap[extractAudioPageNumber(item, index)] = url
    nextSectionMap[sectionId] = url
  })
  pageAudioMap = nextPageMap
  sectionAudioMap = nextSectionMap
}

const selectNarrationAudioTask = (preferredLevel = currentNarrationLevel.value) => {
  const preferred = normalizeNarrationLevel(preferredLevel)
  const preferredTask = narrationAudioTasks.value[preferred]
  if (preferredTask?.taskStatus === 'completed' && preferredTask?.sectionAudios?.length) {
    return preferredTask
  }
  const fallbackLevel = SIMPLE_NARRATION_FALLBACK_ORDER.find((level) => {
    const task = narrationAudioTasks.value[level]
    return task?.taskStatus === 'completed' && task?.sectionAudios?.length
  })
  return fallbackLevel ? narrationAudioTasks.value[fallbackLevel] : null
}

const loadNarrationAudioStatus = async () => {
  if (!currentLessonId.value) return {}
  const result = await getNarrationAudioStatus(currentLessonId.value)
  syncNarrationAudioTasks(result?.audioTasks || {})
  return narrationAudioTasks.value
}

const ensureAudioElement = () => {
  if (audioEl) return
  audioEl = new Audio()
  audioEl.preload = 'metadata'

  audioEl.addEventListener('timeupdate', () => {
    if (!audioEl?.duration) return
    voiceProgress.value = Math.min(100, (audioEl.currentTime / audioEl.duration) * 100)
  })

  audioEl.addEventListener('ended', () => {
    voiceProgress.value = 100
    if (canNextPage.value) {
      lessonStore.setCurrentPage(safeCurrentPage.value + 1)
      return
    }
    lessonStore.setExplainStatus('paused')
  })

  audioEl.addEventListener('error', () => {
    if (explainStatus.value === 'explaining') {
      runFallbackProgress()
    }
  })
}

const resetAudioElement = () => {
  clearVoiceTimer()
  if (audioEl) {
    audioEl.pause()
    audioEl.removeAttribute('src')
    audioEl.load()
  }
  activeAudioSrc = ''
  voiceProgress.value = 0
}

const playLoadedAudio = () => {
  if (!audioEl) return false
  clearVoiceTimer()
  audioEl.play().catch(() => runFallbackProgress())
  return true
}

const initNarrationAudio = async (level = currentNarrationLevel.value) => {
  currentNarrationLevel.value = normalizeNarrationLevel(level)
  let task = selectNarrationAudioTask(currentNarrationLevel.value)
  if (!task) {
    try {
      await loadNarrationAudioStatus()
      task = selectNarrationAudioTask(currentNarrationLevel.value)
    } catch {
      task = null
    }
  }
  if (!task?.audioId || !task?.sectionAudios?.length) {
    audioReady.value = false
    return false
  }

  ensureAudioElement()
  if (activeAudioId !== task.audioId) {
    activeAudioId = task.audioId
    resetAudioElement()
  }
  buildPageAudioMapFromSections(task.audioId, task.sectionAudios)
  audioReady.value = true
  loadSectionAudio()
  return Boolean(activeAudioSrc)
}

const playCurrentAudioOrFallback = async () => {
  clearVoiceTimer()
  if (!audioReady.value || !audioEl || !activeAudioSrc) {
    const ready = await initNarrationAudio(currentNarrationLevel.value)
    if (!ready || explainStatus.value !== 'explaining') {
      runFallbackProgress()
      return
    }
  }
  playLoadedAudio()
}

const initAudio = async (nextAudioId = '') => {
  const audioId = normalizeQuery(nextAudioId) || normalizeQuery(route.query.audioId) || lessonInfo.value.audioId || ''
  if (!audioId) {
    await initNarrationAudio(currentNarrationLevel.value)
    return
  }
  if (activeAudioId === audioId && audioReady.value) {
    loadSectionAudio()
    if (explainStatus.value === 'explaining') playLoadedAudio()
    return
  }
  activeAudioId = audioId
  audioReady.value = false
  pageAudioMap = {}
  sectionAudioMap = {}
  resetAudioElement()

  try {
    const status = await getAudioStatus(audioId)
    const sections = status?.sectionAudios || []
    if (!sections.length) {
      await initNarrationAudio(currentNarrationLevel.value)
      return
    }

    ensureAudioElement()
    buildPageAudioMapFromSections(audioId, sections)

    audioReady.value = true
    loadSectionAudio()
    if (explainStatus.value === 'explaining') playLoadedAudio()
  } catch {
    activeAudioId = ''
    await initNarrationAudio(currentNarrationLevel.value)
  }
}

// ── 假进度兜底（无音频时） ────────────────────────────────────────────
const runFallbackProgress = () => {
  clearVoiceTimer()
  voiceTimer = setInterval(() => {
    if (explainStatus.value !== 'explaining') return
    voiceProgress.value = Math.min(100, voiceProgress.value + 1.6)
    syncPageByProgress()
    if (voiceProgress.value >= 100) lessonStore.setExplainStatus('paused')
  }, 500)
}

const startExplain = () => {
  if (voiceProgress.value >= 100) voiceProgress.value = 0
  lessonStore.setExplainStatus('explaining')
}
const pauseExplain = () => lessonStore.setExplainStatus('paused')
const resumeExplain = () => {
  if (voiceProgress.value >= 100) voiceProgress.value = 0
  lessonStore.setExplainStatus('explaining')
}

const goPrevPage = () => { if (canPrevPage.value) lessonStore.setCurrentPage(safeCurrentPage.value - 1) }
const goNextPage = () => { if (canNextPage.value) lessonStore.setCurrentPage(safeCurrentPage.value + 1) }
const goToPage = (page) => {
  const nextPage = Number(page)
  if (Number.isInteger(nextPage) && nextPage >= 1 && nextPage <= effectiveTotalPages.value) {
    lessonStore.setCurrentPage(nextPage)
  }
}
const handleSectionChange = (sectionId) => {
  lessonStore.setCurrentSection(sectionId)
  voiceProgress.value = 0
  if (previewSlideCount.value > 0) {
    const targetIndex = sectionOptions.value.findIndex((item) => item.sectionId === sectionId)
    if (targetIndex >= 0) {
      lessonStore.setCurrentPage(Math.min(previewSlideCount.value, targetIndex + 1))
    }
  } else {
    syncPageByProgress()
  }
  if (explainStatus.value !== 'paused') lessonStore.setExplainStatus('explaining')
  catalogOpen.value = false
}
const handleQaFinished = async (payload) => {
  lessonStore.setExplainStatus('qa')
  if (payload?.understandingLevel) lessonStore.setLearningProgress({ understandingLevel: payload.understandingLevel })
  if (payload?.answerId) lastQaRecordId.value = payload.answerId
  if (payload?.targetSectionId) lessonStore.setCurrentSection(payload.targetSectionId)
  if (Number.isInteger(payload?.targetPage)) lessonStore.setCurrentPage(payload.targetPage)
  if (Array.isArray(payload?.suggestions) && payload.suggestions.length) {
    quickReviewPoints.value = [...new Set([...quickReviewPoints.value, ...payload.suggestions])].slice(0, 6)
  }
  if (payload?.recommendedNarrationLevel) {
    const newLevel = normalizeNarrationLevel(payload.recommendedNarrationLevel)
    if (newLevel !== currentNarrationLevel.value) {
      currentNarrationLevel.value = newLevel
      narrationLevelFlash.value = true
      setTimeout(() => { narrationLevelFlash.value = false }, 1600)
    }
    try {
      await initNarrationAudio(currentNarrationLevel.value)
      await getLessonNarration(currentLessonId.value, currentNarrationLevel.value)
      quickReviewPoints.value = [
        `后续讲解已切换到 ${currentNarrationLevel.value} 档 (${NARRATION_LEVEL_LABELS[currentNarrationLevel.value] || currentNarrationLevel.value})`,
        ...quickReviewPoints.value,
      ].slice(0, 6)
    } catch {
      quickReviewPoints.value = [
        `推荐使用 ${currentNarrationLevel.value} 档讲稿`,
        ...quickReviewPoints.value,
      ].slice(0, 6)
    }
  }
  persistNote()
  scheduleLearningProgressReport({ qaRecordId: payload?.answerId || '' })
  showResumePrompt.value = true
}
const continueLecture = () => { showResumePrompt.value = false; lessonStore.setExplainStatus('explaining') }
const keepQaMode = () => { showResumePrompt.value = false; lessonStore.setExplainStatus('qa') }
const backToHome = () => router.push('/home')
const formattedSavedAt = computed(() => {
  if (!noteSavedAt.value) return ''
  try { return new Date(noteSavedAt.value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
  catch { return '' }
})

const resetHideTimer = () => {
  controlsVisible.value = true
  clearTimeout(hideControlsTimer)
  if (isExplaining.value) {
    hideControlsTimer = setTimeout(() => { controlsVisible.value = false }, 3500)
  }
}

watch(() => explainStatus.value, (s) => {
  if (s === 'explaining') {
    playCurrentAudioOrFallback()
    resetHideTimer()
    playTeacherTalk()
  } else {
    clearVoiceTimer()
    if (audioReady.value && audioEl) audioEl.pause()
    controlsVisible.value = true
    clearTimeout(hideControlsTimer)
    scheduleLearningProgressReport()
    playTeacherIdle()
  }
})

watch(() => currentSection.value?.sectionId, () => {
  if (!audioReady.value || !audioEl) return
  const wasPlaying = !audioEl.paused
  voiceProgress.value = 0
  loadSectionAudio()
  if (wasPlaying || explainStatus.value === 'explaining') {
    playLoadedAudio()
  }
})
watch(() => `${currentLessonId.value}:${safeCurrentPage.value}`, () => {
  previewImageFailed.value = false
  previewImageVersion.value += 1
  if (audioReady.value && audioEl) {
    const wasPlaying = !audioEl.paused || explainStatus.value === 'explaining'
    loadSectionAudio()
    if (wasPlaying) playLoadedAudio()
  }
})
watch(() => `${currentLessonId.value}:${lessonInfo.value.currentSectionId}:${progressReportBucket.value}`, () => {
  scheduleLearningProgressReport()
})
watch(() => route.query, () => {
  syncContext()
  loadNote()
  previewRenderRequested.value = false
  loadScriptStructure()
  loadPreviewMeta()
  initAudio()
}, { deep: true })
watch(() => noteText.value, persistNote)
onMounted(() => {
  syncContext()
  loadNote()
  loadScriptStructure()
  loadPreviewMeta()
  scheduleLearningProgressReport()
  initVirtualTeacher()
  initAudio()
})
onBeforeUnmount(() => {
  clearVoiceTimer()
  clearTeacherReadyTimer()
  clearTeacherTalkLoopTimer()
  clearTimeout(hideControlsTimer)
  clearPreviewPollTimer()
  clearTimeout(progressTrackTimer)
  if (audioEl) { audioEl.pause(); audioEl.src = ''; audioEl = null }
})
</script>

<template>
  <div class="cockpit" @mousemove="resetHideTimer">

    <div class="stage-col">

      <!-- Top bar -->
      <div class="stage-topbar">
        <button class="topbar-back" @click="backToHome">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M19 12H5M12 5l-7 7 7 7" />
          </svg>
        </button>

        <div class="topbar-meta">
          <span class="topbar-course">知微智课</span>
        </div>

        <div class="topbar-right">
          <div class="page-stepper topbar-stepper">
            <button :disabled="!canPrevPage" @click="goPrevPage">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <span>{{ safeCurrentPage }}</span>
            <button :disabled="!canNextPage" @click="goNextPage">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </button>
          </div>
          <div class="progress-ring-wrap" title="整体进度">
            <svg class="progress-ring" width="36" height="36" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="14" fill="none" stroke="rgba(148,163,184,0.35)" stroke-width="3" />
              <circle cx="18" cy="18" r="14" fill="none" stroke="#14b8a6" stroke-width="3" stroke-linecap="round"
                :stroke-dasharray="`${(learningProgress.overallProgress || 0) * 0.879} 87.9`" stroke-dashoffset="21.975"
                style="transition:stroke-dasharray 0.8s cubic-bezier(0.22,1,0.36,1)" />
            </svg>
            <span class="progress-ring-label">{{ Math.round(learningProgress.overallProgress || 0) }}%</span>
          </div>

          <div class="status-chip" :style="{ background: statusDisplay.bg, color: statusDisplay.color }">
            <span class="status-dot" :style="{ background: statusDisplay.dot }" />
            {{ statusDisplay.text }}
          </div>

          <div class="narration-badge" :class="{ flash: narrationLevelFlash }"
            :style="{ '--lv-color': NARRATION_LEVEL_COLORS[currentNarrationLevel] || '#64748b' }"
            :title="`当前讲稿难度：${currentNarrationLevel} 档`">
            <span class="narration-badge-icon">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
              </svg>
            </span>
            <span class="narration-badge-label">讲稿</span>
            <span class="narration-badge-level">{{ NARRATION_LEVEL_LABELS[currentNarrationLevel] || currentNarrationLevel }}</span>
          </div>

          <button class="topbar-btn" :class="{ active: catalogOpen }" @click="catalogOpen = !catalogOpen"
            :title="catalogOpen ? '收起目录' : '展开目录'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="8" y1="6" x2="21" y2="6" />
              <line x1="8" y1="12" x2="21" y2="12" />
              <line x1="8" y1="18" x2="21" y2="18" />
              <line x1="3" y1="6" x2="3.01" y2="6" />
              <line x1="3" y1="12" x2="3.01" y2="12" />
              <line x1="3" y1="18" x2="3.01" y2="18" />
            </svg>
            <span class="topbar-btn-label">{{ catalogOpen ? '收起' : '目录' }}</span>
          </button>
        </div>
      </div>

      <!-- Slide area -->
      <div class="slide-area">

        <!-- Catalog overlay -->
        <transition name="catalog-slide">
          <div v-if="catalogOpen" class="catalog-drawer">
            <div class="drawer-header">
              <span class="drawer-title">课程目录</span>
              <button class="drawer-close" @click="catalogOpen = false">×</button>
            </div>
            <div class="drawer-list">
              <template v-if="catalogItems.length">
                <button v-for="(item, i) in catalogItems" :key="item.id" class="drawer-item"
                  :class="{ active: lessonInfo.currentSectionId === item.id }" @click="handleSectionChange(item.id)">
                  <span class="drawer-num">{{ String(i + 1).padStart(2, '0') }}</span>
                  <span class="drawer-text">
                    <span class="drawer-name">{{ item.title }}</span>
                    <span class="drawer-desc">{{ item.desc }}</span>
                  </span>
                  <svg v-if="lessonInfo.currentSectionId === item.id" class="drawer-check" width="14" height="14"
                    viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </button>
              </template>
              <div v-else class="drawer-empty">
                {{ scriptLoading ? '正在加载课程结构...' : '暂无章节数据' }}
              </div>
            </div>
          </div>
        </transition>
        <div v-if="catalogOpen" class="catalog-backdrop" @click="catalogOpen = false" />

        <!-- 页码标签（浮在 stage 左上角，不受 ppt-frame overflow 影响） -->
        <div class="slide-page-label">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="3" />
            <path d="M3 9h18M9 21V9" />
          </svg>
          {{ safeCurrentPage }} / {{ effectiveTotalPages }}
        </div>

        <!-- PPT frame -->
        <div class="ppt-frame">
          <div class="slide-inner">
            <div class="slide-content-wrap">
              <img v-if="currentPreviewImageUrl && !previewImageFailed" class="slide-preview-image"
                :src="currentPreviewImageUrl" :alt="`PPT 第 ${safeCurrentPage} 页`" @error="handlePreviewImageError">
              <div v-else class="slide-empty-state">
                {{ previewPlaceholderText }}
              </div>
              <div class="teacher-stage" :class="{ ready: virtualTeacherVisible }">
                <div v-if="!virtualTeacherVisible" class="teacher-stage-mask">虚拟老师加载中...</div>
                <iframe ref="teacherIframeRef" class="teacher-frame" :src="VIRTUAL_TEACHER_URL" title="虚拟老师"
                  scrolling="no" allow="autoplay" @load="handleTeacherIframeLoad" />
              </div>
            </div>

          </div>
        </div>

        <!-- Page flip arrows -->
        <button class="flip-btn flip-prev" :disabled="!canPrevPage" @click="goPrevPage">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <button class="flip-btn flip-next" :disabled="!canNextPage" @click="goNextPage">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M9 18l6-6-6-6" />
          </svg>
        </button>

        <div class="ctrl-progress slide-progress-panel">
          <div class="progress-playback">
            <button class="play-ctrl play" :disabled="isExplaining" @click="startExplain">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            </button>
            <button class="play-ctrl" :disabled="!isExplaining" @click="pauseExplain">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16" />
                <rect x="14" y="4" width="4" height="16" />
              </svg>
            </button>
            <button class="play-ctrl resume" :disabled="!canResume" @click="resumeExplain">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polygon points="5 3 19 12 5 21 5 3" />
                <line x1="19" y1="3" x2="19" y2="21" />
              </svg>
            </button>
          </div>
          <div class="progress-main">
            <div class="ctrl-track">
              <div class="ctrl-fill" :class="{ animating: isExplaining }" :style="{ width: voiceProgress + '%' }" />
              <div class="ctrl-thumb" :style="{ left: voiceProgress + '%' }" />
            </div>
            <div class="ctrl-time">
              <span>当前页讲解 {{ Math.round(voiceProgress) }}%</span>
              <span>第 {{ safeCurrentPage }} / {{ effectiveTotalPages }} 页</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Controls bar -->
      <transition name="controls-fade">
        <div v-show="controlsVisible" class="controls-bar">
          <div class="ctrl-group">
            <button class="play-ctrl play" :disabled="isExplaining" @click="startExplain">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            </button>
            <button class="play-ctrl" :disabled="!isExplaining" @click="pauseExplain">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16" />
                <rect x="14" y="4" width="4" height="16" />
              </svg>
            </button>
            <button class="play-ctrl resume" :disabled="!canResume" @click="resumeExplain">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polygon points="5 3 19 12 5 21 5 3" />
                <line x1="19" y1="3" x2="19" y2="21" />
              </svg>
            </button>
            <div class="voice-vol">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
              </svg>
            </div>
          </div>

          <div class="ctrl-progress">
            <div class="ctrl-track">
              <div class="ctrl-fill" :class="{ animating: isExplaining }" :style="{ width: voiceProgress + '%' }" />
              <div class="ctrl-thumb" :style="{ left: voiceProgress + '%' }" />
            </div>
            <div class="ctrl-time">
              <span>当前页讲解 {{ Math.round(voiceProgress) }}%</span>
              <span>第 {{ safeCurrentPage }} / {{ effectiveTotalPages }} 页</span>
            </div>
          </div>

          <div class="ctrl-right">
            <div class="page-stepper">
              <button :disabled="!canPrevPage" @click="goPrevPage">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                  <path d="M15 18l-6-6 6-6" />
                </svg>
              </button>
              <span>{{ safeCurrentPage }}</span>
              <button :disabled="!canNextPage" @click="goNextPage">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </div>


    <div class="sidebar">
      <div class="sidebar-tabs">
        <button class="stab" :class="{ active: activeRightTab === 'chat' }" @click="activeRightTab = 'chat'">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          AI 助手
        </button>
        <button class="stab" :class="{ active: activeRightTab === 'notes' }" @click="activeRightTab = 'notes'">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          笔记
          <span v-if="noteText" class="stab-dot" />
        </button>
        <div class="stab-line" :style="{ transform: `translateX(${activeRightTab === 'notes' ? '100%' : '0'})` }" />
      </div>

      <!-- Chat -->
      <div v-show="activeRightTab === 'chat'" class="sidebar-pane chat-pane">
        <div class="chat-identity">
          <div class="chat-orb">AI</div>
          <div>
            <p class="chat-name">AI 助手</p>
            <p class="chat-sub"><span class="online-dot" />可随时提问当前课程内容</p>
          </div>
        </div>
        <div class="chat-body">
          <ChatBox :course-id="platformContext.courseId || courseInfo.courseId" :user-id="platformContext.userId"
            :lesson-id="platformContext.lessonId || lessonInfo.lessonId"
            :current-section-id="lessonInfo.currentSectionId" :current-page="safeCurrentPage"
            :session-id="sessionInfo.sessionId" @after-answer="handleQaFinished" />
        </div>
      </div>

      <!-- Notes -->
      <div v-show="activeRightTab === 'notes'" class="sidebar-pane notes-pane">
        <div class="notes-toolbar">
          <div class="notes-meta">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span v-if="formattedSavedAt" class="saved-at">已保存 {{ formattedSavedAt }}</span>
            <span v-else class="unsaved">未保存</span>
          </div>
          <button class="clear-btn" @click="clearNote">清空</button>
        </div>

        <div v-if="quickReviewPoints.length" class="qp-section">
          <p class="qp-title">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2.5">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
            AI 建议
          </p>
          <div class="qp-grid">
            <button v-for="pt in quickReviewPoints" :key="pt" class="qp-pill" @click="appendQuickPoint(pt)">
              + {{ pt }}
            </button>
          </div>
        </div>

        <textarea v-model="noteText" class="notes-ta" placeholder="在这里记录重点内容&#10;&#10;支持 Markdown 格式" />

        <button class="save-btn" @click="saveNote">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
            <polyline points="17 21 17 13 7 13 7 21" />
            <polyline points="7 3 7 8 15 8" />
          </svg>
          保存笔记
        </button>
      </div>
    </div>

    <transition name="toast-pop">
      <div v-if="showResumePrompt" class="resume-toast">
        <span class="t-emoji">问</span>
        <div class="t-body">
          <p class="t-title">问答已完成</p>
          <p class="t-sub">
            <template v-if="narrationLevelFlash">已切换到 <strong>{{ NARRATION_LEVEL_LABELS[currentNarrationLevel] || currentNarrationLevel }}</strong> 讲稿 · 点击继续讲解生效</template>
            <template v-else>是否继续当前课程讲解？</template>
          </p>
        </div>
        <button class="t-primary" @click="continueLecture">继续讲解</button>
        <button class="t-ghost" @click="keepQaMode">继续问答</button>
        <button class="t-x" @click="showResumePrompt = false">×</button>
      </div>
    </transition>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=Noto+Serif+SC:wght@700&display=swap');

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.cockpit {
  --player-bg: #f8fafc;
  --player-surface: #ffffff;
  --player-border: #d9f3ef;
  --player-border-strong: #99f6e4;
  --player-text: #0f172a;
  --player-muted: #64748b;
  --player-subtle: #94a3b8;
  --player-primary: #14b8a6;
  --player-primary-strong: #0f766e;
  --player-primary-soft: #ccfbf1;
  --player-primary-faint: #f0fdfa;
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100dvh;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 336px;
  background:
    radial-gradient(circle at 18% 14%, rgba(20, 184, 166, 0.16), transparent 28%),
    radial-gradient(circle at 72% 8%, rgba(59, 130, 246, 0.09), transparent 24%),
    linear-gradient(135deg, #f0fdfa 0%, var(--player-bg) 42%, #eef6ff 100%);
  font-family: 'Sora', sans-serif;
  overflow: hidden;
}

.stage-col {
  position: relative;
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(180deg, rgba(240, 253, 250, 0.58), rgba(248, 250, 252, 0.96) 36%),
    var(--player-bg);
  min-width: 0;
}

/* Top bar */
.stage-topbar {
  height: 56px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  background:
    linear-gradient(90deg, rgba(240, 253, 250, 0.94), rgba(255, 255, 255, 0.9));
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--player-border);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
  z-index: 20;
}

.topbar-back {
  all: unset;
  cursor: pointer;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: var(--player-primary-faint);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--player-primary-strong);
  transition: all 0.15s;
  flex-shrink: 0;
}

.topbar-back:hover {
  background: var(--player-primary-soft);
  color: #115e59;
}

.topbar-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.topbar-course {
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: var(--player-primary-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.topbar-playback {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 3px;
  border: 1px solid rgba(204, 251, 241, 0.72);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.74);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.topbar-playback .play-ctrl {
  width: 28px;
  height: 28px;
}

.topbar-playback .play-ctrl.play {
  width: 32px;
  height: 32px;
}

.topbar-stepper {
  height: 34px;
}

/* Progress ring */
.progress-ring-wrap {
  position: relative;
  width: 36px;
  height: 36px;
  display: none;
  align-items: center;
  justify-content: center;
}

.progress-ring {
  position: absolute;
  inset: 0;
  transform: rotate(-90deg);
}

.progress-ring-label {
  font-size: 9px;
  font-weight: 700;
  color: var(--player-primary-strong);
  position: relative;
  z-index: 1;
}

/* Status chip */
.status-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
  border: 1px solid rgba(20, 184, 166, 0.16);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  animation: blink 2s ease-in-out infinite;
}

/* Narration level badge */
.narration-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: color-mix(in srgb, var(--lv-color, #64748b) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--lv-color, #64748b) 22%, transparent);
  color: var(--lv-color, #64748b);
  transition: all 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  cursor: default;
  user-select: none;
}

.narration-badge-icon {
  display: flex;
  align-items: center;
  opacity: 0.7;
}

.narration-badge-label {
  opacity: 0.7;
  letter-spacing: 0.04em;
}

.narration-badge-level {
  background: var(--lv-color, #64748b);
  color: #fff;
  height: 18px;
  padding: 0 6px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
}

.narration-badge.flash {
  animation: levelFlash 0.5s cubic-bezier(0.22, 1, 0.36, 1) 3;
}

@keyframes levelFlash {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--lv-color, #64748b) 30%, transparent);
  }
  50% {
    transform: scale(1.08);
    box-shadow: 0 0 0 8px color-mix(in srgb, var(--lv-color, #64748b) 0%, transparent);
  }
}

@keyframes blink {

  0%,
  100% {
    opacity: 1
  }

  50% {
    opacity: 0.3
  }
}

.topbar-btn {
  all: unset;
  cursor: pointer;
  height: 34px;
  padding: 0 10px;
  gap: 6px;
  border-radius: 10px;
  background: rgba(240, 253, 250, 0.78);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--player-muted);
  transition: all 0.15s;
  white-space: nowrap;
}

.topbar-btn:hover {
  background: var(--player-primary-soft);
  color: var(--player-primary-strong);
}

.topbar-btn.active {
  background: var(--player-primary-soft);
  color: var(--player-primary-strong);
}

.topbar-btn-label {
  font-size: 11.5px;
  font-weight: 600;
  line-height: 1;
}

/* Slide area */
.slide-area {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  gap: 10px;
  padding: 14px 18px 44px;
}

/* Catalog drawer */
.catalog-drawer {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 295px;
  z-index: 30;
  background: #ffffff;
  border-right: 1px solid #dbe6f2;
  display: flex;
  flex-direction: column;
  box-shadow: 18px 0 34px rgba(15, 23, 42, 0.12);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 13px;
  border-bottom: 1px solid #e6edf7;
  flex-shrink: 0;
}

.drawer-title {
  font-size: 13.5px;
  font-weight: 700;
  color: #1e293b;
}

.drawer-close {
  all: unset;
  cursor: pointer;
  width: 26px;
  height: 26px;
  border-radius: 7px;
  background: #eef4fb;
  color: #64748b;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.drawer-close:hover {
  background: #dbe8f8;
  color: #1e3a5f;
}

.drawer-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.drawer-list::-webkit-scrollbar {
  width: 3px;
}

.drawer-list::-webkit-scrollbar-thumb {
  background: #d0ddec;
  border-radius: 3px;
}

.drawer-item {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 12px;
  border-radius: 11px;
  width: 100%;
  transition: all 0.15s;
  margin-bottom: 3px;
}

.drawer-item:hover {
  background: #f2f7ff;
}

.drawer-item.active {
  background: #e8f1ff;
}

.drawer-num {
  font-size: 11px;
  font-weight: 700;
  color: #9caec4;
  min-width: 22px;
}

.drawer-item.active .drawer-num {
  color: #2563eb;
}

.drawer-check {
  margin-right: 4px;
  flex-shrink: 0;
}

.drawer-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
  min-width: 0;
}

.drawer-name {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.drawer-item.active .drawer-name {
  color: #1f3f68;
}

.drawer-desc {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.drawer-empty {
  padding: 32px 16px;
  text-align: center;
  font-size: 13px;
  color: #94a3b8;
}

.catalog-backdrop {
  position: absolute;
  inset: 0;
  z-index: 25;
  background: rgba(15, 23, 42, 0.12);
}

/* PPT frame */
.ppt-frame {
  width: 100%;
  height: clamp(540px, calc(100dvh - 145px), 920px);
  flex: 0 1 auto;
  min-height: 0;
  max-width: 1320px;
  border-radius: 14px;
  overflow: hidden;
  background: var(--player-surface);
  border: 1px solid var(--player-border);
  box-shadow:
    0 0 0 1px rgba(20, 184, 166, 0.07),
    0 18px 44px rgba(15, 23, 42, 0.09);
  background-image:
    radial-gradient(ellipse at 50% 0%, rgba(20, 184, 166, 0.1) 0%, transparent 52%),
    radial-gradient(ellipse at 88% 100%, rgba(59, 130, 246, 0.05) 0%, transparent 48%);
  position: relative;
}

.slide-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px 28px;
  position: relative;
}

.slide-page-label {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--player-primary-strong);
  background: rgba(240, 253, 250, 0.9);
  border: 1px solid rgba(153, 246, 228, 0.78);
  backdrop-filter: blur(10px);
  padding: 4px 10px;
  border-radius: 999px;
  pointer-events: none;
}

.slide-content-wrap {
  width: 100%;
  height: 100%;
  max-width: 1120px;
  position: relative;
  text-align: center;
  animation: contentIn 0.35s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.slide-preview-image {
  display: block;
  width: 100%;
  max-width: 100%;
  height: 100%;
  max-height: 100%;
  margin: 0 auto;
  object-fit: contain;
  border-radius: 10px;
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.14);
}

.teacher-stage {
  position: absolute;
  right: clamp(8px, 1vw, 16px);
  bottom: clamp(8px, 1vw, 16px);
  width: min(8.67vw, 94px);
  aspect-ratio: 9 / 16;
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.24s ease, transform 0.24s ease;
  pointer-events: none;
}

.teacher-stage.ready {
  opacity: 1;
  transform: translateY(0);
}

.teacher-stage-mask {
  position: absolute;
  inset: auto 12px 24px 12px;
  padding: 8px 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.72);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  backdrop-filter: blur(8px);
}

.teacher-frame {
  width: 100%;
  height: 100%;
  display: block;
  border: none;
  background: transparent;
  pointer-events: none;
}

.slide-empty-state {
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  font-size: 16px;
  line-height: 1.8;
  color: #64748b;
}

@keyframes contentIn {
  from {
    opacity: 0;
    transform: translateY(10px)
  }

  to {
    opacity: 1;
    transform: translateY(0)
  }
}

.slide-text {
  font-size: 17px;
  line-height: 2;
  color: #334155;
  font-weight: 400;
}

/* Flip arrows */
.flip-btn {
  all: unset;
  cursor: pointer;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 38px;
  height: 62px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid var(--player-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--player-primary-strong);
  transition: all 0.2s;
  z-index: 5;
}

.flip-btn:hover:not(:disabled) {
  background: #ffffff;
  color: #115e59;
  border-color: var(--player-border-strong);
  box-shadow: 0 10px 24px rgba(20, 184, 166, 0.16);
}

.flip-btn:disabled {
  opacity: 0.18;
  cursor: not-allowed;
}

.flip-prev {
  left: 12px;
}

.flip-next {
  right: 12px;
}

/* Controls bar */
.controls-bar {
  height: 0;
  flex-shrink: 0;
  display: none !important;
  grid-template-columns: auto 1fr auto;
  grid-template-rows: 1fr;
  align-items: center;
  column-gap: 22px;
  padding: 0 22px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(248, 250, 252, 0.96));
  backdrop-filter: blur(18px);
  border-top: 1px solid var(--player-border);
  box-shadow: 0 -10px 24px rgba(15, 23, 42, 0.05);
}

.controls-bar>.ctrl-progress {
  display: none;
}

.ctrl-group {
  grid-column: 1;
  grid-row: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
  border: 1px solid rgba(204, 251, 241, 0.72);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
}

.play-ctrl {
  all: unset;
  cursor: pointer;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--player-muted);
  transition: all 0.15s;
}

.play-ctrl:hover:not(:disabled) {
  color: var(--player-primary-strong);
  background: var(--player-primary-faint);
}

.play-ctrl:disabled {
  opacity: 0.22;
  cursor: not-allowed;
}

.play-ctrl.play {
  background: linear-gradient(135deg, var(--player-primary), #0f766e);
  color: #fff;
  width: 40px;
  height: 40px;
  box-shadow: 0 8px 20px rgba(20, 184, 166, 0.28);
}

.play-ctrl.play:not(:disabled):hover {
  box-shadow: 0 10px 26px rgba(20, 184, 166, 0.36);
  transform: scale(1.05);
}

.play-ctrl.play:disabled {
  opacity: 0.38;
  transform: none;
  box-shadow: none;
}

.voice-vol {
  color: var(--player-subtle);
  display: flex;
  align-items: center;
  margin-left: 4px;
}

.ctrl-progress {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 180px;
  padding: 0 2px;
}

.slide-progress-panel {
  position: static;
  width: 100%;
  max-width: 1320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 14px;
  z-index: 34;
  padding: 8px 14px;
  border: 1px solid rgba(153, 246, 228, 0.82);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(14px);
  box-shadow:
    0 14px 34px rgba(15, 23, 42, 0.12),
    0 0 0 1px rgba(20, 184, 166, 0.05);
  transition:
    opacity 0.22s ease,
    transform 0.22s ease,
    box-shadow 0.22s ease;
}

.slide-progress-panel.is-hidden {
  opacity: 0;
  transform: translateY(10px);
  pointer-events: none;
  box-shadow: none;
}

.progress-playback {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
  padding: 4px;
  border-radius: 999px;
  border: 1px solid rgba(204, 251, 241, 0.76);
  background: rgba(240, 253, 250, 0.86);
}

.progress-playback .play-ctrl {
  width: 30px;
  height: 30px;
}

.progress-playback .play-ctrl.play {
  width: 36px;
  height: 36px;
}

.progress-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.slide-progress-panel .ctrl-track {
  height: 7px;
}

.ctrl-track {
  height: 8px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.76), rgba(240, 253, 250, 0.86)),
    #dff7f3;
  border-radius: 999px;
  position: relative;
  cursor: pointer;
  overflow: hidden;
  border: 1px solid rgba(153, 246, 228, 0.8);
  box-shadow:
    inset 0 1px 2px rgba(15, 23, 42, 0.05),
    0 8px 18px rgba(20, 184, 166, 0.09);
  transition: transform 0.15s, box-shadow 0.15s;
}

.ctrl-track:hover {
  transform: translateY(-1px);
  box-shadow:
    inset 0 1px 2px rgba(15, 23, 42, 0.05),
    0 10px 22px rgba(20, 184, 166, 0.14);
}

.ctrl-fill {
  height: 100%;
  min-width: 8px;
  background:
    linear-gradient(90deg, #14b8a6 0%, #2dd4bf 58%, #60a5fa 100%);
  border-radius: 999px;
  transition: width 0.38s linear;
  position: relative;
  box-shadow: 0 0 18px rgba(20, 184, 166, 0.28);
}

.ctrl-fill.animating::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 42px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.62), transparent);
  animation: shim 1.2s linear infinite;
}

@keyframes shim {
  from {
    opacity: 0
  }

  50% {
    opacity: 1
  }

  to {
    opacity: 0
  }
}

.ctrl-thumb {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  border: 3px solid var(--player-primary);
  box-shadow:
    0 0 0 4px rgba(20, 184, 166, 0.14),
    0 8px 18px rgba(15, 23, 42, 0.16);
  opacity: 1;
  transition: transform 0.15s, box-shadow 0.15s;
}

.ctrl-track:hover .ctrl-thumb {
  transform: translate(-50%, -50%) scale(1.06);
}

.ctrl-time {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--player-muted);
  font-weight: 700;
  letter-spacing: 0.01em;
}

.ctrl-right {
  grid-column: 3;
  grid-row: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}

.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.ctrl-section {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  font-weight: 600;
  color: #6d86a5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 130px;
}

.page-stepper {
  display: flex;
  align-items: center;
  background: rgba(240, 253, 250, 0.9);
  border: 1px solid rgba(153, 246, 228, 0.72);
  border-radius: 999px;
  overflow: hidden;
}

.page-stepper button {
  all: unset;
  cursor: pointer;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--player-primary-strong);
  transition: all 0.15s;
}

.page-stepper button:hover:not(:disabled) {
  color: #115e59;
  background: var(--player-primary-soft);
}

.page-stepper button:disabled {
  opacity: 0.18;
  cursor: not-allowed;
}

.page-stepper span {
  padding: 0 10px;
  font-size: 12px;
  font-weight: 700;
  color: var(--player-primary-strong);
  min-width: 28px;
  text-align: center;
}

.sidebar {
  display: flex;
  flex-direction: column;
  background: #f9fcff;
  border-left: 1px solid #dbe7f3;
  overflow: hidden;
}

.sidebar-tabs {
  display: grid;
  grid-template-columns: 1fr;
  height: 52px;
  flex-shrink: 0;
  background: #eff5fc;
  border-bottom: 1px solid #dbe7f3;
  position: relative;
}

.stab {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 600;
  color: #8aa0b9;
  position: relative;
  z-index: 1;
  transition: color 0.2s;
}

.stab.active {
  color: #1f3f67;
}

.stab-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34d399;
  position: absolute;
  top: 13px;
  right: calc(50% - 30px);
}

.stab-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 50%;
  height: 2px;
  border-radius: 2px 2px 0 0;
  background: linear-gradient(90deg, #2563eb, #06b6d4);
  transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

.sidebar-pane {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* Chat */
.chat-identity {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px 10px;
  flex-shrink: 0;
  border-bottom: 1px solid #e6edf7;
}

.chat-orb {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #1e3a5f, #1e40af);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #93c5fd;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 0 16px rgba(37, 99, 235, 0.3);
}

.chat-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e3a5f;
}

.chat-sub {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #90a4bc;
  margin-top: 2px;
}

.online-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 6px #34d399;
  animation: blink 2s infinite;
}

.chat-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin: 10px 12px 12px;
  border: 1px solid #d9e7f5;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
}

.chat-body :deep(.chat-card) {
  border: none !important;
  box-shadow: none !important;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent !important;
}

.chat-body :deep(.chat-card > .el-card__header) {
  display: none;
}

.chat-body :deep(.chat-card > .el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0;
  background: transparent;
}

.chat-body :deep(.chat-list) {
  flex: 1;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
  padding: 0 10px 0 10px;
  scrollbar-width: thin;
  scrollbar-color: #9ab8da #ecf3fb;
}

.chat-body :deep(.chat-list::-webkit-scrollbar) {
  width: 8px;
}

.chat-body :deep(.chat-list::-webkit-scrollbar-track) {
  background: #ecf3fb;
  border-radius: 999px;
}

.chat-body :deep(.chat-list::-webkit-scrollbar-thumb) {
  background: linear-gradient(180deg, #9cc4ed 0%, #7ea8d8 100%);
  border-radius: 999px;
  border: 1px solid #e3edf8;
}

.chat-body :deep(.chat-list::-webkit-scrollbar-thumb:hover) {
  background: linear-gradient(180deg, #82b3e6 0%, #668fc6 100%);
}

.sidebar-tabs .stab:nth-of-type(2),
.sidebar-tabs .stab-line {
  display: none;
}

.chat-pane {
  background:
    radial-gradient(circle at 18% 0%, rgba(20, 184, 166, 0.09), transparent 32%),
    linear-gradient(180deg, #f8fafc 0%, #f1f8f8 100%);
}

.chat-identity {
  margin: 12px 12px 0;
  padding: 12px;
  border: 1px solid rgba(217, 243, 239, 0.96);
  border-radius: 14px;
  background:
    linear-gradient(135deg, rgba(240, 253, 250, 0.96), rgba(255, 255, 255, 0.94)),
    #ffffff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.chat-orb {
  display: none;
}

.chat-name {
  font-size: 0;
}

.chat-name::after {
  content: 'DeepSeek-v4 在线助教';
  color: #0f172a;
  font-size: 13px;
  font-weight: 800;
}

.chat-sub {
  font-size: 0;
}

.chat-sub::after {
  content: '正在结合当前页课件内容';
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
}

.chat-body {
  margin: 10px 12px 12px;
  border-color: rgba(217, 243, 239, 0.96);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.07);
}

.chat-body :deep(.chat-list) {
  padding: 14px 12px 12px;
  background:
    radial-gradient(circle at 20% 0%, rgba(20, 184, 166, 0.08), transparent 34%),
    #f8fafc;
}

/* Notes */
.notes-pane {
  display: none !important;
  padding: 14px;
  gap: 11px;
  overflow-y: auto;
}

.notes-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.notes-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: #8da2ba;
}

.saved-at {
  color: #34d399;
}

.unsaved {
  color: #a8bacd;
}

.clear-btn {
  all: unset;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 7px;
  font-size: 11.5px;
  font-weight: 600;
  color: #7b92ae;
  background: #edf4fc;
  transition: all 0.15s;
}

.clear-btn:hover {
  background: rgba(220, 38, 38, 0.15);
  color: #f87171;
}

.qp-section {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.qp-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #90a4bc;
}

.qp-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.qp-pill {
  all: unset;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 500;
  color: #93c5fd;
  background: rgba(96, 165, 250, 0.1);
  border: 1px solid rgba(96, 165, 250, 0.2);
  transition: all 0.15s;
  white-space: nowrap;
}

.qp-pill:hover {
  background: rgba(96, 165, 250, 0.2);
}

.notes-ta {
  flex: 1;
  min-height: 200px;
  resize: none;
  background: #ffffff;
  border: 1px solid #d8e5f2;
  border-radius: 12px;
  padding: 12px 14px;
  font: 13px/1.85 'Sora', sans-serif;
  color: #334155;
  outline: none;
  transition: border-color 0.2s, background 0.2s;
}

.notes-ta:focus {
  border-color: #9ec3ea;
  background: #fdfefe;
}

.notes-ta::placeholder {
  color: #a5b8cc;
}

.save-btn {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  height: 40px;
  border-radius: 11px;
  font-size: 13.5px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #059669, #0891b2);
  box-shadow: 0 4px 14px rgba(5, 150, 105, 0.28);
  transition: all 0.18s;
  flex-shrink: 0;
}

.save-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 7px 22px rgba(5, 150, 105, 0.4);
}

.catalog-slide-enter-active {
  animation: drawIn 0.28s cubic-bezier(0.22, 1, 0.36, 1);
}

.catalog-slide-leave-active {
  animation: drawOut 0.2s ease;
}

@keyframes drawIn {
  from {
    transform: translateX(-100%)
  }

  to {
    transform: translateX(0)
  }
}

@keyframes drawOut {
  from {
    transform: translateX(0)
  }

  to {
    transform: translateX(-100%)
  }
}

.controls-fade-enter-active {
  transition: opacity 0.3s, transform 0.3s;
}

.controls-fade-leave-active {
  transition: opacity 0.5s, transform 0.5s;
}

.controls-fade-enter-from,
.controls-fade-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

/* Toast */
.resume-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #cfdff0;
  border-radius: 16px;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.2);
  max-width: 460px;
  width: calc(100vw - 48px);
}

.t-emoji {
  font-size: 20px;
  flex-shrink: 0;
}

.t-body {
  flex: 1;
  min-width: 0;
}

.t-title {
  font-size: 13.5px;
  font-weight: 700;
  color: #1f3f67;
}

.t-sub {
  font-size: 12px;
  color: #6f86a3;
  margin-top: 2px;
}

.t-primary {
  all: unset;
  cursor: pointer;
  padding: 7px 16px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #2563eb, #0891b2);
  box-shadow: 0 3px 10px rgba(37, 99, 235, 0.35);
  white-space: nowrap;
  transition: all 0.15s;
}

.t-primary:hover {
  box-shadow: 0 5px 18px rgba(37, 99, 235, 0.5);
}

.t-ghost {
  all: unset;
  cursor: pointer;
  padding: 7px 16px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  color: #5f7694;
  background: #edf3fb;
  white-space: nowrap;
  transition: all 0.15s;
}

.t-ghost:hover {
  background: #dbe8f8;
  color: #1f436d;
}

.t-x {
  all: unset;
  cursor: pointer;
  color: #93a8c0;
  font-size: 13px;
  padding: 4px;
  flex-shrink: 0;
  transition: color 0.15s;
}

.t-x:hover {
  color: #526d8d;
}

.toast-pop-enter-active {
  animation: tPop 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.toast-pop-leave-active {
  animation: tPop 0.2s ease reverse;
}

@keyframes tPop {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(16px)
  }

  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0)
  }
}

@media (max-width: 960px) {
  .teacher-stage {
    width: min(11.33vw, 74px);
    right: 8px;
  }
}

@media (max-width: 760px) {
  .teacher-stage {
    width: min(14vw, 60px);
  }
}
</style>
