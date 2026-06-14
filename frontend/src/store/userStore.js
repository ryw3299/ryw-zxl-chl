import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, register as registerApi, getMe } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLogin = computed(() => !!token.value)
  const isStudent = computed(() => user.value?.role === 'student')
  const username = computed(() => user.value?.username || '')

  async function login(username, password) {
    const res = await loginApi({ username, password })
    token.value = res.access_token
    user.value = res.user_info
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify(res.user_info))
    return res
  }

  async function register(username, password, email) {
    const res = await registerApi({ username, password, email })
    token.value = res.access_token
    user.value = res.user_info
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify(res.user_info))
    return res
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  async function fetchUser() {
    try {
      const res = await getMe()
      user.value = {
        id: res.id,
        username: res.username,
        role: res.role,
        email: res.email || '',
      }
      localStorage.setItem('user', JSON.stringify(user.value))
    } catch {
      logout()
    }
  }

  return { token, user, isLogin, isStudent, username, login, register, logout, fetchUser }
})
