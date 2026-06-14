import request from '@/utils/request'

export function getProfile() {
  return request.get('/profile/me')
}

export function initProfile(data) {
  return request.post('/profile/init', data)
}

export function getProfileHistory() {
  return request.get('/profile/history')
}
