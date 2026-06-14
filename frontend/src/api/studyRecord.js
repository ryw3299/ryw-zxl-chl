import request from '@/utils/request'

export function getStudyRecords() {
  return request.get('/study-records')
}

export function getStudyStats() {
  return request.get('/study-records/stats')
}
