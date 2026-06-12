import request from '@/utils/request'
import { DEFAULT_SCHOOL_ID } from '@/utils/signature'

const normalizeString = (value, fallback = '') => {
  if (Array.isArray(value)) {
    return normalizeString(value[0], fallback)
  }
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

const normalizeNumber = (value) => {
  const raw = Array.isArray(value) ? value[0] : value
  const nextValue = Number(raw)
  return Number.isFinite(nextValue) ? nextValue : undefined
}

const parseJsonLike = (value, fallback) => {
  if (typeof value === 'string') {
    try {
      return JSON.parse(value)
    } catch {
      return fallback
    }
  }
  return value ?? fallback
}

const readStoredUserId = () => {
  if (typeof window === 'undefined') {
    return ''
  }
  try {
    const raw = localStorage.getItem('userInfo')
    const parsed = raw ? JSON.parse(raw) : {}
    return normalizeString(parsed?.userId)
  } catch {
    return ''
  }
}

const pickResult = (payload) => {
  if (!payload || typeof payload !== 'object') {
    return {}
  }
  if (payload.data && typeof payload.data === 'object') {
    return payload.data
  }
  return payload
}

const normalizeRelatedKnowledge = (value) => {
  const parsed = parseJsonLike(value, value)

  if (!parsed) {
    return []
  }

  if (Array.isArray(parsed)) {
    return parsed
      .map((item) => {
        if (typeof item === 'string') {
          return item.trim()
        }
        return normalizeString(
          item?.knowledgeName || item?.knowledge_name || item?.name,
        )
      })
      .filter(Boolean)
  }

  const single = normalizeString(
    parsed.knowledgeName || parsed.knowledge_name || parsed.name,
  )
  return single ? [single] : []
}

const normalizeSuggestions = (value) => {
  const parsed = parseJsonLike(value, value)
  if (!Array.isArray(parsed)) {
    return []
  }
  return parsed.map((item) => normalizeString(item)).filter(Boolean)
}

export const getGamePayload = async (payload = {}) => {
  const response = await request({
    url: '/qa/gamePayload',
    method: 'post',
    data: {
      schoolId: normalizeString(payload.schoolId, DEFAULT_SCHOOL_ID),
      userId: normalizeString(payload.userId, readStoredUserId()),
      courseId: normalizeString(payload.courseId),
      lessonId: normalizeString(payload.lessonId),
      sessionId: normalizeString(payload.sessionId),
      question: normalizeString(payload.question),
      currentSectionId: normalizeString(payload.currentSectionId),
      currentPage: normalizeNumber(payload.currentPage),
    },
  })

  const result = pickResult(response)
  return {
    gameType: normalizeString(result.gameType, 'multiple_choice'),
    prompt: normalizeString(result.prompt),
    choices: Array.isArray(result.choices) ? result.choices : [],
    correctIndex: typeof result.correctIndex === 'number' ? result.correctIndex : 0,
    correctChoice: normalizeString(result.correctChoice),
    explanation: normalizeString(result.explanation),
  }
}

export const transcribeVoice = async (blob, language = 'zh-CN') => {
  if (!blob) {
    throw new Error('No audio blob provided')
  }
  const form = new FormData()
  const ext = (blob.type || '').includes('mp4') ? 'm4a'
    : (blob.type || '').includes('wav') ? 'wav'
    : 'webm'
  form.append('file', blob, `voice-${Date.now()}.${ext}`)
  form.append('language', language)

  const response = await request({
    url: '/qa/voiceToTextUpload',
    method: 'post',
    data: form,
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })

  const result = pickResult(response)
  return {
    text: normalizeString(result.text),
    confidence: typeof result.confidence === 'number' ? result.confidence : 0,
  }
}

export const interactQA = async (payload = {}) => {
  const response = await request({
    url: '/qa/interact',
    method: 'post',
    data: {
      schoolId: normalizeString(payload.schoolId, DEFAULT_SCHOOL_ID),
      userId: normalizeString(payload.userId, readStoredUserId()),
      courseId: normalizeString(payload.courseId),
      lessonId: normalizeString(payload.lessonId),
      sessionId: normalizeString(payload.sessionId),
      questionType: normalizeString(payload.questionType, 'text'),
      questionContent: normalizeString(payload.question || payload.questionContent),
      currentSectionId: normalizeString(payload.currentSectionId),
      currentPage: normalizeNumber(payload.currentPage),
      historyQa: Array.isArray(payload.historyQa) ? payload.historyQa : [],
    },
  })

  const result = pickResult(response)

  return {
    answer: normalizeString(result.answerContent || result.answer_content),
    relatedKnowledge: normalizeRelatedKnowledge(
      result.relatedKnowledge || result.related_knowledge,
    ),
    understandingLevel: normalizeString(
      result.understandingLevel || result.understanding_level,
    ),
    suggestions: normalizeSuggestions(result.suggestions),
    answerId: normalizeString(result.answerId || result.answer_id),
    questionType: normalizeString(result.questionType || result.question_type, 'unknown'),
    recommendedNarrationLevel: normalizeString(
      result.recommendedNarrationLevel || result.recommended_narration_level,
    ),
    nextAction: normalizeString(result.nextAction || result.next_action),
    reason: normalizeString(result.reason),
    matchedSectionId: normalizeString(result.matchedSectionId || result.matched_section_id),
    matchedPage: normalizeNumber(result.matchedPage ?? result.matched_page),
    targetSectionId: normalizeString(result.targetSectionId || result.target_section_id),
    targetPage: normalizeNumber(result.targetPage ?? result.target_page),
  }
}
