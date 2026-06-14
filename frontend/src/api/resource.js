import request from '@/utils/request'

export function getResources(params) {
  return request.get('/resources', { params })
}

export function getResourceDetail(id) {
  return request.get(`/resources/${id}`)
}

export function recordResourceView(id) {
  return request.post(`/resources/${id}/view`)
}
