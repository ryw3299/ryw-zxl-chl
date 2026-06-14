import request from '@/utils/request'

export function getAnnouncements() {
  return request.get('/announcements')
}
