import request from '@/utils/request'

export function syncCourse(payload) {
  const { silent, ...data } = payload || {}
  return request({
    url: '/platform/syncCourse',
    method: 'post',
    data,
    silent,
  })
}

export function syncUser(payload) {
  const { silent, ...data } = payload || {}
  return request({
    url: '/platform/syncUser',
    method: 'post',
    data,
    silent,
  })
}
