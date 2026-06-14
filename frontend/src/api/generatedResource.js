import request from '@/utils/request'

export function generateResource(data) {
  return request.post('/generated-resources/generate', data)
}

export function getGeneratedResources() {
  return request.get('/generated-resources')
}

export function getGeneratedResourceDetail(id) {
  return request.get(`/generated-resources/${id}`)
}
