import request from '@/utils/request'

export function getPaths() {
  return request.get('/paths')
}

export function generatePath(data) {
  return request.post('/paths/generate', data)
}

export function getPathDetail(id) {
  return request.get(`/paths/${id}`)
}

export function updatePathStatus(id, data) {
  return request.put(`/paths/${id}/status`, data)
}
