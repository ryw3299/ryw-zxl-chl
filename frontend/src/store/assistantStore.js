import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sendChatMessage, getConversations, getConversationMessages } from '@/api/assistant'

export const useAssistantStore = defineStore('assistant', () => {
  const conversations = ref([])
  const currentConvId = ref(null)
  const messages = ref([])
  const contextItems = ref([])
  const isOpen = ref(false)
  const isThinking = ref(false)

  function toggle() { isOpen.value = !isOpen.value }
  function open() { isOpen.value = true }
  function close() { isOpen.value = false }

  async function sendMessage(content) {
    isThinking.value = true
    // Add user message locally immediately
    const tempId = Date.now()
    messages.value.push({ id: tempId, role: 'user', content })

    try {
      // Build context text from contextItems
      const contextText = contextItems.value
        .map(c => c.type === 'text' ? `[选中内容]\n${c.content}` : `[${c.type}]`)
        .join('\n\n')

      const res = await sendChatMessage({
        conversation_id: currentConvId.value,
        message: content,
        context_text: contextText || undefined,
      })

      currentConvId.value = res.conversation_id
      messages.value.push({ id: Date.now() + 1, role: 'assistant', content: res.message?.content || res.message })
      // Clear context after sending
      contextItems.value = []
      return res
    } catch {
      messages.value.push({
        id: Date.now() + 1,
        role: 'assistant',
        content: '抱歉，我暂时无法回答这个问题。请稍后重试或换一种问法。',
      })
    } finally {
      isThinking.value = false
    }
  }

  function addContext(item) {
    // item: { type: 'text'|'image'|'screenshot', content: string, pageId?: string, resourceId?: string }
    contextItems.value.push({ ...item, id: Date.now() })
    open() // Open panel automatically when adding context
  }

  function clearContext() {
    contextItems.value = []
  }

  function removeContext(id) {
    contextItems.value = contextItems.value.filter(c => c.id !== id)
  }

  async function fetchConversations() {
    try { conversations.value = await getConversations() } catch {}
  }

  async function fetchMessages(convId) {
    currentConvId.value = convId
    try { messages.value = await getConversationMessages(convId) } catch {}
  }

  return {
    conversations, currentConvId, messages, contextItems, isOpen, isThinking,
    toggle, open, close, sendMessage, addContext, clearContext, removeContext,
    fetchConversations, fetchMessages,
  }
})
