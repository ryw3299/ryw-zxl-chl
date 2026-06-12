import axios from 'axios'
import { ElMessage } from 'element-plus'
import { signRequestConfig } from '@/utils/signature'
import { API_TIMEOUT_MS } from '@/utils/runtimeConfig'

const readTokenFromQuery = () => {
  if (typeof window === 'undefined') {
    return ''
  }
  const token = new URLSearchParams(window.location.search).get('token') || ''
  if (token) {
    localStorage.setItem('platform_token', token)
    localStorage.setItem('token', token)
  }
  return token
}

const getAuthToken = () => {
  if (typeof window === 'undefined') {
    return ''
  }
  return readTokenFromQuery()
    || localStorage.getItem('platform_token')
    || localStorage.getItem('token')
    || ''
}

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: API_TIMEOUT_MS,
})

request.interceptors.request.use(
  (config) => {
    const token = getAuthToken()
    if (token) {
      config.headers = config.headers || {}
      if (!config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    signRequestConfig(config)
    return config
  },
  (error) => Promise.reject(error),
)

request.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') {
      return response.data
    }
    const payload = response.data || {}
    if (typeof payload.code === 'number' && payload.code !== 200) {
      const error = new Error(payload.msg || '请求失败')
      error.response = response
      throw error
    }
    return payload.data ?? payload
  },
  (error) => {
    const isTimeout = error?.code === 'ECONNABORTED' || /timeout/i.test(String(error?.message || ''))
    const message = isTimeout
      ? `请求超时，请稍后重试或检查后端问答/检索耗时（当前超时 ${API_TIMEOUT_MS}ms）`
      : (error?.response?.data?.msg || error?.response?.data?.message || error.message || '请求失败，请稍后重试')
    if (typeof window !== 'undefined' && !error?.config?.silent) {
      ElMessage.error(message)
    }
    error.userMessage = message
    return Promise.reject(error)
  },
)

export default request
