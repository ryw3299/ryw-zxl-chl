import axios from 'axios'
import { ElMessage } from 'element-plus'

const getToken = () => localStorage.getItem('token') || ''

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    const payload = response.data || {}
    if (typeof payload.code === 'number' && payload.code !== 200) {
      const error = new Error(payload.msg || '请求失败')
      error.response = response
      throw error
    }
    return payload.data ?? payload
  },
  (error) => {
    const msg = error?.response?.data?.msg || error.message || '请求失败'
    if (error?.config?.silent !== true) {
      ElMessage.error(msg)
    }
    if (error?.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default request
