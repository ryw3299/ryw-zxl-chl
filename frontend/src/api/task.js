import request from '@/utils/request'

export function getTasks() {
  return request.get('/tasks')
}

export function createTask(data) {
  return request.post('/tasks', data)
}

export function toggleTask(id) {
  return request.put(`/tasks/${id}/toggle`)
}
