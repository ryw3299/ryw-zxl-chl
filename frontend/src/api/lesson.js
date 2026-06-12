import request from '@/utils/request'
import { buildSignedPath, DEFAULT_SCHOOL_ID } from '@/utils/signature'

const normalizeString = (value, fallback = '') => {
  if (Array.isArray(value)) {
    return normalizeString(value[0], fallback)
  }
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

const inferFileType = (file) => {
  const fileName = normalizeString(file?.name).toLowerCase()
  const suffix = fileName.includes('.') ? fileName.split('.').pop() : ''
  return suffix || 'pdf'
}

const resolveSignedAssetUrl = (signedPath) => {
  const apiBaseUrl = normalizeString(import.meta.env.VITE_API_BASE_URL)
  if (!signedPath || !apiBaseUrl || apiBaseUrl.startsWith('/')) {
    return signedPath
  }

  try {
    return new URL(signedPath, apiBaseUrl).toString()
  } catch {
    return signedPath
  }
}

export const parseLesson = async (payload = {}) => {
  if (typeof FormData !== 'undefined' && payload instanceof FormData) {
    const file = payload.get('file')
    const nextPayload = new FormData()
    nextPayload.append('file', file)
    nextPayload.append('schoolId', normalizeString(payload.get('schoolId'), DEFAULT_SCHOOL_ID))
    nextPayload.append('userId', normalizeString(payload.get('userId')))
    nextPayload.append('courseId', normalizeString(payload.get('courseId')))
    nextPayload.append('fileType', normalizeString(payload.get('fileType'), inferFileType(file)))
    nextPayload.append('isExtractKeyPoint', normalizeString(payload.get('isExtractKeyPoint'), 'true'))
    return request({
      url: '/lesson/parseUpload',
      method: 'post',
      data: nextPayload,
    })
  }

  return request({
    url: '/lesson/parse',
    method: 'post',
    data: {
      schoolId: normalizeString(payload.schoolId, DEFAULT_SCHOOL_ID),
      userId: normalizeString(payload.userId),
      courseId: normalizeString(payload.courseId),
      fileType: normalizeString(payload.fileType),
      fileUrl: normalizeString(payload.fileUrl),
      isExtractKeyPoint: payload.isExtractKeyPoint ?? true,
    },
  })
}

export const getParseStatus = (parseId) => request({
  url: '/lesson/parseStatus',
  method: 'post',
  data: { parseId },
})

export const generateCoursewareSlidePlan = async (payload = {}) => {
  if (typeof FormData !== 'undefined' && payload instanceof FormData) {
    const file = payload.get('file')
    const nextPayload = new FormData()
    nextPayload.append('file', file)
    nextPayload.append('schoolId', normalizeString(payload.get('schoolId'), DEFAULT_SCHOOL_ID))
    nextPayload.append('userId', normalizeString(payload.get('userId')))
    nextPayload.append('courseId', normalizeString(payload.get('courseId')))
    nextPayload.append('fileType', normalizeString(payload.get('fileType'), inferFileType(file)))
    nextPayload.append('instruction', normalizeString(payload.get('instruction')))
    nextPayload.append('audience', normalizeString(payload.get('audience')))
    return request({
      url: '/lesson/courseware/slidePlanUpload',
      method: 'post',
      data: nextPayload,
    })
  }
  throw new Error('generateCoursewareSlidePlan requires FormData')
}

export const getCoursewareStatus = (lessonId) => request({
  url: '/lesson/courseware/status',
  method: 'post',
  data: { lessonId: normalizeString(lessonId) },
})

export const updateCoursewareSlidePlan = (payload = {}) => request({
  url: '/lesson/courseware/slidePlan',
  method: 'post',
  data: {
    lessonId: normalizeString(payload.lessonId),
    slidePlan: payload.slidePlan && typeof payload.slidePlan === 'object' ? payload.slidePlan : {},
  },
})

export const renderCoursewarePpt = (payload = {}) => request({
  url: '/lesson/courseware/render',
  method: 'post',
  data: {
    lessonId: normalizeString(payload.lessonId),
    renderMode: normalizeString(payload.renderMode, 'flash'),
  },
})

export const generateNarrationAudio = (payload = {}) => request({
  url: '/lesson/courseware/generateNarrationAudio',
  method: 'post',
  data: {
    lessonId: normalizeString(payload.lessonId),
    levels: Array.isArray(payload.levels) && payload.levels.length ? payload.levels : ['A', 'B', 'C', 'D'],
    voiceType: normalizeString(payload.voiceType, 'female_standard'),
    audioFormat: normalizeString(payload.audioFormat, 'mp3'),
    sectionIds: Array.isArray(payload.sectionIds) ? payload.sectionIds : undefined,
  },
})

export const getNarrationAudioStatus = (lessonId) => request({
  url: '/lesson/courseware/narrationAudioStatus',
  method: 'post',
  data: { lessonId: normalizeString(lessonId) },
})

export const generateScript = (payload = {}) => request({
  url: '/lesson/generateScript',
  method: 'post',
  data: {
    parseId: normalizeString(payload.parseId),
    teachingStyle: normalizeString(payload.teachingStyle, 'standard'),
    speechSpeed: normalizeString(payload.speechSpeed, 'normal'),
    customOpening: normalizeString(payload.customOpening),
  },
})

export const getScriptStatus = (scriptId) => request({
  url: '/lesson/scriptStatus',
  method: 'post',
  data: { scriptId },
})

export const editScript = (payload = {}) => request({
  url: '/lesson/editScript',
  method: 'post',
  data: {
    scriptId: normalizeString(payload.scriptId),
    scriptStructure: Array.isArray(payload.scriptStructure) ? payload.scriptStructure : [],
  },
})

export const generateAudio = (payload = {}) => request({
  url: '/lesson/generateAudio',
  method: 'post',
  data: {
    scriptId: normalizeString(payload.scriptId),
    voiceType: normalizeString(payload.voiceType, 'female_standard'),
    audioFormat: normalizeString(payload.audioFormat, 'mp3'),
    sectionIds: Array.isArray(payload.sectionIds) ? payload.sectionIds : undefined,
  },
})

export const getAudioStatus = (audioId) => request({
  url: '/lesson/audioStatus',
  method: 'post',
  data: { audioId },
})

export const buildAudioUrl = (audioId, sectionId, params = {}) => resolveSignedAssetUrl(buildSignedPath(
  `/api/v1/lesson/audio/${encodeURIComponent(audioId)}/${encodeURIComponent(sectionId)}`,
  params,
))

export const renderLessonPpt = (lessonId) => request({
  url: '/lesson/renderPPT',
  method: 'post',
  data: { lessonId },
})

export const getLessonPreviewMeta = (lessonId) => request({
  url: `/lesson/preview/${encodeURIComponent(lessonId)}`,
  method: 'get',
  params: {},
})

export const getLessonNarration = (lessonId, level) => request({
  url: `/lesson/narration/${encodeURIComponent(lessonId)}/${encodeURIComponent(level)}`,
  method: 'get',
})

export const buildLessonDownloadUrl = (lessonId) => resolveSignedAssetUrl(buildSignedPath(
  `/api/v1/lesson/download/${encodeURIComponent(lessonId)}`,
))

export const getLessonPreviewImageUrl = (lessonId, slideNumber, params = {}) => resolveSignedAssetUrl(buildSignedPath(
  `/api/v1/lesson/preview/${encodeURIComponent(lessonId)}/${encodeURIComponent(slideNumber)}`,
  params,
))

export const buildLessonPreviewImageUrl = getLessonPreviewImageUrl

// ── 教师端：一键生成智课 ────────────────────────────────────────────────

export const generateLesson = (payload = {}) => request({
  url: '/lesson/generate',
  method: 'post',
  data: {
    schoolId: normalizeString(payload.schoolId, DEFAULT_SCHOOL_ID),
    userId: normalizeString(payload.userId),
    courseId: normalizeString(payload.courseId),
    fileType: normalizeString(payload.fileType, 'pptx'),
    fileUrl: normalizeString(payload.fileUrl),
    teachingStyle: normalizeString(payload.teachingStyle, 'standard'),
    customOpening: normalizeString(payload.customOpening),
  },
})

export const getGenerateStatus = (lessonId) => request({
  url: '/lesson/generateStatus',
  method: 'post',
  data: { lessonId },
})

export const publishLesson = (payload = {}) => request({
  url: '/lesson/publish',
  method: 'post',
  data: {
    lessonId: normalizeString(payload.lessonId),
    lessonName: normalizeString(payload.lessonName),
    courseDesc: normalizeString(payload.courseDesc),
    tag: normalizeString(payload.tag),
    coverUrl: normalizeString(payload.coverUrl),
  },
})

export const deleteLesson = (lessonId) => request({
  url: '/lesson/delete',
  method: 'post',
  data: { lessonId: normalizeString(lessonId) },
})

export const listLessons = (status = '', options = {}) => request({
  url: '/lesson/list',
  method: 'get',
  params: status ? { status } : {},
  ...options,
})

export const uploadAndParse = async (file, payload = {}) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('schoolId', normalizeString(payload.schoolId, DEFAULT_SCHOOL_ID))
  formData.append('userId', normalizeString(payload.userId))
  formData.append('courseId', normalizeString(payload.courseId))
  formData.append('fileType', normalizeString(payload.fileType, inferFileType(file)))
  formData.append('isExtractKeyPoint', 'true')
  return request({
    url: '/lesson/parseUpload',
    method: 'post',
    data: formData,
  })
}
