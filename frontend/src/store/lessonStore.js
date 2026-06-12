import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const normalizeString = (value) => {
  if (Array.isArray(value)) {
    return value[0] || ''
  }
  return typeof value === 'string' ? value : ''
}

const createSessionId = () => `session-${Date.now()}`

export const useLessonStore = defineStore('lesson', () => {
  const platformContext = ref({
    schoolId: '',
    courseId: '',
    userId: '',
    lessonId: '',
    role: 'student',
    token: '',
  })

  const courseInfo = ref({
    courseId: '',
    courseName: '',
    courseDesc: '',
    teacherName: '',
  })
  const lessonInfo = ref({
    lessonId: '',
    scriptId: '',
    audioId: '',
    totalPages: 0,
    sections: [],
    currentSectionId: '',
    currentPage: 1,
  })
  const explainStatus = ref('idle')
  const learningProgress = ref({
    currentSectionTitle: '',
    overallProgress: 0,
    understandingLevel: '中等',
    recommendedActions: ['继续当前章节', '补充讲解', '加快节奏'],
  })
  const sessionInfo = ref({
    sessionId: createSessionId(),
  })
  const chatHistory = ref([
    {
      id: `msg-${Date.now()}`,
      role: 'ai',
      text: '你好，我是智课助教。你可以随时提问，我会结合当前章节为你解答。',
      createdAt: new Date().toISOString(),
    },
  ])

  const currentSection = computed(() => {
    const sections = lessonInfo.value.sections || []
    if (!sections.length) {
      return null
    }
    return (
      sections.find((section) => section.sectionId === lessonInfo.value.currentSectionId) ||
      sections[0]
    )
  })

  const highlightedPages = computed(() => currentSection.value?.relatedPages || [])
  const currentExplainText = computed(
    () => currentSection.value?.explainScript || '当前章节脚本尚未生成，请先完成教师端脚本生成。',
  )

  const refreshProgressFromSection = () => {
    const sections = lessonInfo.value.sections || []
    if (!sections.length) {
      return
    }

    const index = sections.findIndex((item) => item.sectionId === lessonInfo.value.currentSectionId)
    const safeIndex = index < 0 ? 0 : index
    learningProgress.value.currentSectionTitle = sections[safeIndex].title
    learningProgress.value.overallProgress = Math.round(((safeIndex + 1) / sections.length) * 100)
  }

  const syncPlatformContext = (payload = {}) => {
    const nextContext = {
      schoolId: normalizeString(payload.schoolId),
      courseId: normalizeString(payload.courseId),
      userId: normalizeString(payload.userId),
      lessonId: normalizeString(payload.lessonId),
      role: normalizeString(payload.role) || 'student',
      token: normalizeString(payload.token),
    }

    platformContext.value = {
      ...platformContext.value,
      ...nextContext,
    }

    if (nextContext.token && typeof window !== 'undefined') {
      localStorage.setItem('platform_token', nextContext.token)
    }

    if (nextContext.courseId) {
      courseInfo.value.courseId = nextContext.courseId
    }
    if (nextContext.lessonId) {
      lessonInfo.value.lessonId = nextContext.lessonId
    }
  }

  const setCourseInfo = (payload = {}) => {
    courseInfo.value = {
      ...courseInfo.value,
      ...payload,
    }
  }

  const setLessonInfo = (payload = {}) => {
    const nextLesson = {
      ...lessonInfo.value,
      ...payload,
    }
    if (Array.isArray(payload.sections)) {
      nextLesson.sections = payload.sections
    }

    if (
      !nextLesson.currentSectionId ||
      !nextLesson.sections?.some((item) => item.sectionId === nextLesson.currentSectionId)
    ) {
      nextLesson.currentSectionId = nextLesson.sections?.[0]?.sectionId || ''
    }

    lessonInfo.value = nextLesson

    if (typeof payload.currentPage === 'number') {
      setCurrentPage(payload.currentPage)
    } else if (currentSection.value?.relatedPages?.length) {
      lessonInfo.value.currentPage = currentSection.value.relatedPages[0]
    }

    refreshProgressFromSection()
  }

  const setCurrentSection = (sectionId) => {
    const target = (lessonInfo.value.sections || []).find((item) => item.sectionId === sectionId)
    if (!target) {
      return
    }
    lessonInfo.value.currentSectionId = target.sectionId
    if (target.relatedPages?.length) {
      lessonInfo.value.currentPage = target.relatedPages[0]
    }
    refreshProgressFromSection()
  }

  const setCurrentPage = (page) => {
    const targetPage = Number(page)
    if (!Number.isFinite(targetPage)) {
      return
    }
    lessonInfo.value.currentPage = Math.min(
      Math.max(1, targetPage),
      Number(lessonInfo.value.totalPages || 1),
    )
  }

  const setExplainStatus = (status) => {
    explainStatus.value = status
  }

  const setLearningProgress = (payload = {}) => {
    learningProgress.value = {
      ...learningProgress.value,
      ...payload,
    }
  }

  const appendChatMessage = (message) => {
    chatHistory.value.push(message)
  }

  const clearChatHistory = () => {
    chatHistory.value = []
  }

  const resetSession = () => {
    sessionInfo.value.sessionId = createSessionId()
  }

  return {
    platformContext,
    courseInfo,
    lessonInfo,
    explainStatus,
    learningProgress,
    sessionInfo,
    chatHistory,
    currentSection,
    highlightedPages,
    currentExplainText,
    syncPlatformContext,
    setCourseInfo,
    setLessonInfo,
    setCurrentSection,
    setCurrentPage,
    setExplainStatus,
    setLearningProgress,
    appendChatMessage,
    clearChatHistory,
    resetSession,
  }
})
