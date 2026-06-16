import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getProfile, initProfile, getProfileHistory, getProfileInitState } from '@/api/profile'

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

  async function init(chatHistory, conversationId = '') {
    loading.value = true
    try {
      const result = await initProfile({
        chat_history: chatHistory,
        conversation_id: conversationId,
      })
      if (result?.profile_ready && result?.profile_json) {
        profile.value = result
      }
      return result
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory() {
    history.value = await getProfileHistory()
  }

  async function fetchInitState() {
    return getProfileInitState()
  }

  return { profile, history, loading, fetchProfile, init, fetchHistory, fetchInitState }
})
