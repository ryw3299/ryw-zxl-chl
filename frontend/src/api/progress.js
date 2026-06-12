import request from '@/utils/request'
import { DEFAULT_SCHOOL_ID } from '@/utils/signature'

const normalizeString = (value, fallback = '') => {
  if (Array.isArray(value)) {
    return normalizeString(value[0], fallback)
  }
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

export const trackProgress = (payload = {}) => request({
  url: '/progress/track',
  method: 'post',
  data: {
    schoolId: normalizeString(payload.schoolId, DEFAULT_SCHOOL_ID),
    userId: normalizeString(payload.userId),
    courseId: normalizeString(payload.courseId),
    lessonId: normalizeString(payload.lessonId),
    currentSectionId: normalizeString(payload.currentSectionId || payload.sectionId),
    progressPercent: Number(payload.progressPercent ?? 0),
    lastOperateTime: normalizeString(payload.lastOperateTime, new Date().toISOString().slice(0, 19).replace('T', ' ')),
    qaRecordId: normalizeString(payload.qaRecordId),
  },
  silent: Boolean(payload.silent),
})

export const adjustProgress = async (payload = {}) => {
  const result = await request({
    url: '/progress/adjust',
    method: 'post',
    data: {
      userId: normalizeString(payload.userId),
      lessonId: normalizeString(payload.lessonId),
      currentSectionId: normalizeString(payload.currentSectionId || payload.sectionId),
      understandingLevel: normalizeString(payload.understandingLevel, 'partial'),
      qaRecordId: normalizeString(payload.qaRecordId, 'qa-local'),
    },
  })
  return result.adjustPlan || result
}
