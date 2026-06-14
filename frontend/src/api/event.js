import request from '@/utils/request'

export function createEvent(data) {
  return request.post('/events', data)
}

export function batchEvents(data) {
  return request.post('/events/batch', data)
}

export function getMyEvents() {
  return request.get('/events/me')
}

export function getMastery() {
  return request.get('/events/mastery/me')
}
