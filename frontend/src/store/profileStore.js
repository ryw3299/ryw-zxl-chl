import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getProfile, initProfile, getProfileHistory } from '@/api/profile'

export const useProfileStore = defineStore('profile', () => {
  const profile = ref(null)
  const history = ref([])
  const loading = ref(false)

  async function fetchProfile() {
    loading.value = true
    try {
      profile.value = await getProfile()
    } catch {
      profile.value = null
    } finally {
      loading.value = false
    }
  }

  async function init(chatHistory) {
    loading.value = true
    try {
      profile.value = await initProfile({ chat_history: chatHistory })
      return profile.value
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory() {
    history.value = await getProfileHistory()
  }

  return { profile, history, loading, fetchProfile, init, fetchHistory }
})
