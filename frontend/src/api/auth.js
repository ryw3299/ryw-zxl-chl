import request from '@/utils/request'

const normalizeString = (value, fallback = '') => {
  if (Array.isArray(value)) {
    return normalizeString(value[0], fallback)
  }
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

export const login = (payload = {}) => request({
  url: '/auth/login',
  method: 'post',
  data: {
    userId: normalizeString(payload.userId),
    password: normalizeString(payload.password),
    role: normalizeString(payload.role),
  },
})

export const register = (payload = {}) => request({
  url: '/auth/register',
  method: 'post',
  data: {
    userId: normalizeString(payload.userId),
    password: normalizeString(payload.password),
    role: 'student',
    userName: normalizeString(payload.userName),
    schoolId: normalizeString(payload.schoolId),
  },
})

export const getCurrentUser = () => request({
  url: '/auth/me',
  method: 'get',
  params: {},
})
