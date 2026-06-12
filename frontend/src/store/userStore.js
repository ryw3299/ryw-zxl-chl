import { defineStore } from 'pinia'

const TOKEN_KEY = 'token'
const USER_INFO_KEY = 'userInfo'

const getStoredToken = () => {
  if (typeof window === 'undefined') {
    return ''
  }
  return localStorage.getItem(TOKEN_KEY) || ''
}

const getStoredUserInfo = () => {
  if (typeof window === 'undefined') {
    return { userId: '', userName: '', role: '', schoolId: '' }
  }

  const raw = localStorage.getItem(USER_INFO_KEY)
  if (!raw) {
    return { userId: '', userName: '', role: '', schoolId: '' }
  }

  try {
    const parsed = JSON.parse(raw)
    return {
      userId: parsed?.userId || '',
      userName: parsed?.userName || '',
      role: parsed?.role || '',
      schoolId: parsed?.schoolId || '',
    }
  } catch (error) {
    return { userId: '', userName: '', role: '', schoolId: '' }
  }
}

const initialToken = getStoredToken()
const initialUserInfo = getStoredUserInfo()

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: initialUserInfo,
    token: initialToken,
    isLogin: Boolean(initialToken),
  }),

  getters: {
    isTeacher: (state) => state.userInfo.role === 'teacher',
    isStudent: (state) => state.userInfo.role === 'student',
  },

  actions: {
    login(userInfo = {}, token = '') {
      this.userInfo = {
        userId: userInfo.userId || '',
        userName: userInfo.userName || userInfo.userId || '',
        role: userInfo.role || '',
        schoolId: userInfo.schoolId || '',
      }
      this.token = token || ''
      this.isLogin = Boolean(this.token)

      if (typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, this.token)
        localStorage.setItem(USER_INFO_KEY, JSON.stringify(this.userInfo))
      }
    },

    logout() {
      this.userInfo = { userId: '', userName: '', role: '', schoolId: '' }
      this.token = ''
      this.isLogin = false

      if (typeof window !== 'undefined') {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_INFO_KEY)
        localStorage.removeItem('platform_token')
      }
    },
  },
})
